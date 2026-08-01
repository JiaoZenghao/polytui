#!/usr/bin/env python3
"""Exercise every public interactive target through a controlling PTY."""

from __future__ import annotations

import errno
import fcntl
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import termios
import time


CASES = {
    "go": ("PolyTUI · Go", ["make", "run-go"]),
    "rust": ("PolyTUI · Rust", ["make", "run-rust"]),
    "typescript": ("PolyTUI · TypeScript", ["make", "run-typescript"]),
    "python": ("PolyTUI · Python", ["make", "run-python"]),
}
EXIT_KEYS = {"ctrl+c": b"\x03", "ctrl+d": b"\x04"}
EXIT_HINT = "Press Ctrl+C or Ctrl+D to exit"

TIMEOUT_SECONDS = 5.0
TERMINATE_TIMEOUT_SECONDS = 1.0
TERMINAL_COLUMNS = 80
TERMINAL_ROWS = 24
REPO_ROOT = Path(__file__).resolve().parent.parent
CSI_SEQUENCE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CURSOR_POSITION_QUERY = b"\x1b[6n"
CURSOR_POSITION_RESPONSE = b"\x1b[1;1R"
OSC_SEQUENCE = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)", re.DOTALL)


def decoded_output(captured: bytearray) -> str:
    return bytes(captured).decode("utf-8", errors="replace")


def normalized_output(captured: bytearray) -> str:
    output = decoded_output(captured)
    output = OSC_SEQUENCE.sub("", output)
    lines: list[list[str]] = [[]]
    screen_top = 0
    row = 0
    column = 0
    saved_cursor: tuple[int, int] | None = None
    index = 0

    def ensure_line(line_index: int) -> None:
        while len(lines) <= line_index:
            lines.append([])

    def parsed_parameters(parameters: str) -> list[int | None] | None:
        if any(character not in "0123456789;" for character in parameters):
            return None
        return [int(value) if value else None for value in parameters.split(";")]

    def parameter_or_default(
        parameters: list[int | None],
        default: int,
    ) -> int:
        value = parameters[0] if parameters else None
        return default if value in (None, 0) else value

    def erase_line(mode: int) -> None:
        ensure_line(row)
        line = lines[row]
        if mode == 0:
            del line[column:]
        elif mode == 1:
            erased_cells = min(column + 1, len(line))
            line[:erased_cells] = [" "] * erased_cells
        elif mode == 2:
            line.clear()

    def erase_display(mode: int) -> None:
        nonlocal row, screen_top, saved_cursor
        ensure_line(row)
        screen_bottom = screen_top + TERMINAL_ROWS - 1
        if mode == 0:
            erase_line(0)
            for line_index in range(row + 1, min(len(lines), screen_bottom + 1)):
                lines[line_index].clear()
        elif mode == 1:
            for line_index in range(screen_top, row):
                ensure_line(line_index)
                lines[line_index].clear()
            erase_line(1)
        elif mode == 2:
            for line_index in range(
                screen_top,
                min(len(lines), screen_bottom + 1),
            ):
                lines[line_index].clear()
        elif mode == 3 and screen_top:
            del lines[:screen_top]
            row -= screen_top
            if saved_cursor is not None:
                saved_row, saved_column = saved_cursor
                saved_cursor = (max(0, saved_row - screen_top), saved_column)
            screen_top = 0

    while index < len(output):
        sequence = CSI_SEQUENCE.match(output, index)
        if sequence:
            sequence_text = sequence.group()
            command = sequence_text[-1]
            parameters = parsed_parameters(sequence_text[2:-1])
            if parameters is not None:
                amount = parameter_or_default(parameters, 1)
                if command == "A":
                    row = max(screen_top, row - amount)
                elif command == "B":
                    row = min(screen_top + TERMINAL_ROWS - 1, row + amount)
                elif command == "C":
                    column += amount
                elif command == "D":
                    column = max(0, column - amount)
                elif command == "E":
                    row = min(screen_top + TERMINAL_ROWS - 1, row + amount)
                    column = 0
                elif command == "F":
                    row = max(screen_top, row - amount)
                    column = 0
                elif command in {"G", "`"}:
                    column = amount - 1
                elif command in {"H", "f"}:
                    requested_row = parameter_or_default(parameters, 1)
                    requested_column = parameter_or_default(parameters[1:], 1)
                    row = screen_top + min(TERMINAL_ROWS, requested_row) - 1
                    column = requested_column - 1
                elif command == "d":
                    row = screen_top + min(TERMINAL_ROWS, amount) - 1
                elif command == "K":
                    erase_line(parameters[0] or 0)
                elif command == "J":
                    erase_display(parameters[0] or 0)
                elif command == "s":
                    saved_cursor = (row, column)
                elif command == "u" and saved_cursor is not None:
                    row, column = saved_cursor
            index = sequence.end()
            continue

        if output.startswith("\x1b7", index):
            saved_cursor = (row, column)
            index += 2
            continue
        if output.startswith("\x1b8", index):
            if saved_cursor is not None:
                row, column = saved_cursor
            index += 2
            continue

        character = output[index]
        if character == "\r":
            column = 0
        elif character == "\n":
            row += 1
            if row >= screen_top + TERMINAL_ROWS:
                screen_top += 1
        elif ord(character) >= 32:
            ensure_line(row)
            line = lines[row]
            while len(line) <= column:
                line.append(" ")
            line[column] = character
            column += 1
        index += 1

    normalized_lines = ["".join(line).rstrip() for line in lines]
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    return "\n".join(normalized_lines)


def test_normalized_output_removes_erased_startup_lines() -> None:
    startup_lines = (
        "PolyTUI · Python",
        "Press Ctrl+C or Ctrl+D to exit",
    )
    captured = bytearray(
        (
            f"{startup_lines[0]}\r\n{startup_lines[1]}"
            "\x1b[2K\x1b[1A\r\x1b[2K"
        ).encode()
    )

    output = normalized_output(captured)

    for line in startup_lines:
        if line in output:
            raise AssertionError(
                f"normalizer retained erased startup line {line!r}: {output!r}"
            )


def test_normalized_output_emulates_required_vt_operations() -> None:
    cases = {
        "relative cursor movement": (
            "12345\x1b[2DXY\r\nabc\x1b[1A\x1b[2C!\x1b[1B\x1b[2D?",
            "123XY!\nabc ?",
        ),
        "line-relative cursor movement": (
            "top\r\nmid\r\nbot\x1b[2FZ\x1b[2E!",
            "Zop\nmid\n!ot",
        ),
        "absolute cursor movement": (
            "abcd\x1b[2GZ\x1b[2;3HQ\x1b[1;4f!",
            "aZc!\n  Q",
        ),
        "CSI cursor save and restore": (
            "abc\x1b[sX\x1b[2DZ\x1b[uY",
            "abZY",
        ),
        "DEC cursor save and restore": (
            "abc\x1b7X\x1b[2DZ\x1b8Y",
            "abZY",
        ),
        "erase line from cursor": ("abcde\x1b[3D\x1b[K", "ab"),
        "erase line to cursor": ("abcde\x1b[2D\x1b[1K", "    e"),
        "erase entire line": ("abcde\x1b[2K", ""),
        "erase display from cursor": (
            "one\r\ntwo\r\nthree\x1b[2;2H\x1b[J",
            "one\nt",
        ),
        "erase display to cursor": (
            "one\r\ntwo\r\nthree\x1b[2;2H\x1b[1J",
            "\n  o\nthree",
        ),
        "erase entire display": (
            "one\r\ntwo\r\nthree\x1b[2J",
            "",
        ),
    }

    for label, (captured, expected) in cases.items():
        output = normalized_output(bytearray(captured.encode()))
        if output != expected:
            raise AssertionError(
                f"{label}: normalized output {output!r}, expected {expected!r}"
            )

    scrollback = "history" + "\r\n" * 24 + "screen"
    display_erased = normalized_output(bytearray(f"{scrollback}\x1b[2J".encode()))
    if "history" not in display_erased or "screen" in display_erased:
        raise AssertionError(
            "erase-display mode 2 must retain scrollback and erase the visible screen: "
            f"{display_erased!r}"
        )

    scrollback_erased = normalized_output(bytearray(f"{scrollback}\x1b[3J".encode()))
    if "history" in scrollback_erased or "screen" not in scrollback_erased:
        raise AssertionError(
            "erase-display mode 3 must erase scrollback and retain the visible screen: "
            f"{scrollback_erased!r}"
        )


def normalized_terminal_attributes(attributes: list[object]) -> tuple[int, ...]:
    control_characters = attributes[6]
    return (
        *(int(value) for value in attributes[:6]),
        *(
            value[0] if isinstance(value, bytes) else int(value)
            for value in control_characters
        ),
    )


class CursorPositionResponder:
    """Reply once to every complete cursor-position query in PTY output."""

    def __init__(self) -> None:
        self.scanned_length = 0

    def reply_to_queries(self, master_fd: int, captured: bytearray) -> None:
        scan_start = max(
            0,
            self.scanned_length - len(CURSOR_POSITION_QUERY) + 1,
        )
        query_start = captured.find(CURSOR_POSITION_QUERY, scan_start)
        while query_start != -1:
            os.write(master_fd, CURSOR_POSITION_RESPONSE)
            query_start = captured.find(
                CURSOR_POSITION_QUERY,
                query_start + len(CURSOR_POSITION_QUERY),
            )
        self.scanned_length = len(captured)


def read_available(
    master_fd: int,
    captured: bytearray,
    cursor_position_responder: CursorPositionResponder,
) -> bool:
    try:
        chunk = os.read(master_fd, 65536)
    except OSError as error:
        if error.errno == errno.EIO:
            return False
        raise

    if not chunk:
        return False
    captured.extend(chunk)
    cursor_position_responder.reply_to_queries(master_fd, captured)
    return True


def read_until_lines(
    master_fd: int,
    captured: bytearray,
    expected_lines: tuple[str, str],
    cursor_position_responder: CursorPositionResponder,
    deadline: float,
) -> bool:
    while time.monotonic() < deadline:
        output = normalized_output(captured)
        if all(line in output for line in expected_lines):
            return True

        remaining = deadline - time.monotonic()
        readable, _, _ = select.select(
            [master_fd],
            [],
            [],
            min(0.1, max(0.0, remaining)),
        )
        if readable and not read_available(
            master_fd,
            captured,
            cursor_position_responder,
        ):
            break

    while True:
        readable, _, _ = select.select([master_fd], [], [], 0)
        if not readable or not read_available(
            master_fd,
            captured,
            cursor_position_responder,
        ):
            break

    output = normalized_output(captured)
    return all(line in output for line in expected_lines)


def test_read_until_lines_drains_ready_output_after_deadline() -> None:
    master_fd, slave_fd = pty.openpty()
    captured = bytearray()
    try:
        os.write(slave_fd, b"already ready banner\r\nalready ready hint\r\n")
        found = read_until_lines(
            master_fd,
            captured,
            ("already ready banner", "already ready hint"),
            CursorPositionResponder(),
            time.monotonic() - 1.0,
        )
    finally:
        os.close(master_fd)
        os.close(slave_fd)

    if not found:
        raise AssertionError(
            "read_until_lines did not drain output ready at the deadline"
        )


def drain_output(
    master_fd: int,
    captured: bytearray,
    cursor_position_responder: CursorPositionResponder,
    deadline: float,
) -> None:
    while True:
        if time.monotonic() >= deadline:
            return
        readable, _, _ = select.select([master_fd], [], [], 0)
        if not readable or not read_available(
            master_fd,
            captured,
            cursor_position_responder,
        ):
            return


def wait_for_process(
    process: subprocess.Popen[bytes],
    master_fd: int,
    captured: bytearray,
    cursor_position_responder: CursorPositionResponder,
    deadline: float,
) -> int:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, TIMEOUT_SECONDS)
        try:
            return process.wait(timeout=min(0.05, remaining))
        except subprocess.TimeoutExpired:
            drain_output(
                master_fd,
                captured,
                cursor_position_responder,
                deadline,
            )


def signal_process_group(
    process: subprocess.Popen[bytes],
    signal_number: signal.Signals,
) -> None:
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        pass


def process_group_exists(process: subprocess.Popen[bytes]) -> bool:
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_for_process_group_exit(
    process: subprocess.Popen[bytes],
    master_fd: int,
    captured: bytearray,
    cursor_position_responder: CursorPositionResponder,
    deadline: float,
) -> None:
    while process_group_exists(process):
        if time.monotonic() >= deadline:
            raise RuntimeError("process group did not exit after SIGKILL")

        drain_output(master_fd, captured, cursor_position_responder, deadline)
        if not process_group_exists(process):
            return

        remaining = deadline - time.monotonic()
        readable, _, _ = select.select(
            [master_fd],
            [],
            [],
            min(0.05, max(0.0, remaining)),
        )
        if readable and not read_available(
            master_fd,
            captured,
            cursor_position_responder,
        ):
            select.select([], [], [], min(0.05, max(0.0, remaining)))


def stop_process(
    process: subprocess.Popen[bytes],
    master_fd: int,
    captured: bytearray,
    cursor_position_responder: CursorPositionResponder,
) -> None:
    signal_process_group(process, signal.SIGTERM)
    if process.poll() is None:
        try:
            wait_for_process(
                process,
                master_fd,
                captured,
                cursor_position_responder,
                time.monotonic() + TERMINATE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            pass

    if not process_group_exists(process):
        return

    signal_process_group(process, signal.SIGKILL)
    cleanup_deadline = time.monotonic() + TERMINATE_TIMEOUT_SECONDS
    if process.poll() is None:
        try:
            wait_for_process(
                process,
                master_fd,
                captured,
                cursor_position_responder,
                cleanup_deadline,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                "process group did not exit after SIGKILL; top-level process was not reaped"
            ) from error

    wait_for_process_group_exit(
        process,
        master_fd,
        captured,
        cursor_position_responder,
        cleanup_deadline,
    )


def input_is_raw(slave_name: str) -> bool:
    input_fd = os.open(slave_name, os.O_RDWR | os.O_NOCTTY)
    try:
        input_termios = termios.tcgetattr(input_fd)
    finally:
        os.close(input_fd)
    return (input_termios[3] & (termios.ICANON | termios.ISIG)) == 0


def wait_for_raw_input(
    master_fd: int,
    slave_name: str,
    captured: bytearray,
    cursor_position_responder: CursorPositionResponder,
    deadline: float,
) -> bool:
    while time.monotonic() < deadline:
        if input_is_raw(slave_name):
            return True

        remaining = deadline - time.monotonic()
        readable, _, _ = select.select(
            [master_fd],
            [],
            [],
            min(0.05, max(0.0, remaining)),
        )
        if readable and not read_available(
            master_fd,
            captured,
            cursor_position_responder,
        ):
            break

    return input_is_raw(slave_name)


def failure_message(label: str, message: str, captured: bytearray) -> str:
    return (
        f"{label}: {message}\n"
        f"captured output:\n{decoded_output(captured)!r}"
    )


def run_case(
    language: str,
    banner: str,
    command: list[str],
    exit_name: str,
    exit_byte: bytes,
) -> None:
    label = f"{language} {exit_name}"
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)
    slave_closed = False
    original_termios = normalized_terminal_attributes(termios.tcgetattr(slave_fd))
    fcntl.ioctl(
        slave_fd,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", TERMINAL_ROWS, TERMINAL_COLUMNS, 0, 0),
    )
    captured = bytearray()
    cursor_position_responder = CursorPositionResponder()
    process: subprocess.Popen[bytes] | None = None

    def setup_controlling_terminal() -> None:
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

    environment = os.environ.copy()
    environment.update(
        {
            "CI": "true",
            "TERM": "xterm-256color",
            "COLUMNS": "80",
            "LINES": "24",
        }
    )

    try:
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=environment,
            preexec_fn=setup_controlling_terminal,
        )
        os.close(slave_fd)
        slave_closed = True

        expected_lines = (banner, EXIT_HINT)
        startup_deadline = time.monotonic() + TIMEOUT_SECONDS
        if not read_until_lines(
            master_fd,
            captured,
            expected_lines,
            cursor_position_responder,
            startup_deadline,
        ):
            cleanup_deadline = time.monotonic() + TERMINATE_TIMEOUT_SECONDS
            stop_process(
                process,
                master_fd,
                captured,
                cursor_position_responder,
            )
            drain_output(
                master_fd,
                captured,
                cursor_position_responder,
                cleanup_deadline,
            )
            raise AssertionError(
                failure_message(
                    label,
                    "expected startup lines were not rendered within 5 seconds",
                    captured,
                )
            )

        if not wait_for_raw_input(
            master_fd,
            slave_name,
            captured,
            cursor_position_responder,
            startup_deadline,
        ):
            cleanup_deadline = time.monotonic() + TERMINATE_TIMEOUT_SECONDS
            stop_process(
                process,
                master_fd,
                captured,
                cursor_position_responder,
            )
            drain_output(
                master_fd,
                captured,
                cursor_position_responder,
                cleanup_deadline,
            )
            raise AssertionError(
                failure_message(
                    label,
                    "terminal input did not enter raw mode within 5 seconds",
                    captured,
                )
            )

        os.write(master_fd, exit_byte)

        try:
            status = wait_for_process(
                process,
                master_fd,
                captured,
                cursor_position_responder,
                time.monotonic() + TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            cleanup_deadline = time.monotonic() + TERMINATE_TIMEOUT_SECONDS
            stop_process(
                process,
                master_fd,
                captured,
                cursor_position_responder,
            )
            drain_output(
                master_fd,
                captured,
                cursor_position_responder,
                cleanup_deadline,
            )
            raise AssertionError(
                failure_message(
                    label,
                    "process did not exit within 5 seconds",
                    captured,
                )
            ) from None

        drain_output(
            master_fd,
            captured,
            cursor_position_responder,
            time.monotonic() + TERMINATE_TIMEOUT_SECONDS,
        )
        restored_termios = normalized_terminal_attributes(
            termios.tcgetattr(master_fd)
        )
        output = normalized_output(captured)
        failures = []

        if status != 0:
            failures.append(f"expected status 0, got {status}")
        if restored_termios != original_termios:
            failures.append("complete termios state was not restored")
        for line in expected_lines:
            if line not in output:
                failures.append(f"normalized retained output is missing {line!r}")

        if failures:
            raise AssertionError(
                failure_message(label, "; ".join(failures), captured)
            )
    finally:
        try:
            if process is not None and process.poll() is None:
                stop_process(
                    process,
                    master_fd,
                    captured,
                    cursor_position_responder,
                )
                drain_output(
                    master_fd,
                    captured,
                    cursor_position_responder,
                    time.monotonic() + TERMINATE_TIMEOUT_SECONDS,
                )
        finally:
            os.close(master_fd)
            if not slave_closed:
                os.close(slave_fd)


def main() -> None:
    test_normalized_output_removes_erased_startup_lines()
    test_normalized_output_emulates_required_vt_operations()
    test_read_until_lines_drains_ready_output_after_deadline()
    print("ok - terminal output normalizer", flush=True)

    for language, (banner, command) in CASES.items():
        for exit_name, exit_byte in EXIT_KEYS.items():
            run_case(language, banner, command, exit_name, exit_byte)
            print(f"ok - {language} {exit_name}", flush=True)

    print("all TUI lifecycle PTY scenarios pass")


if __name__ == "__main__":
    main()
