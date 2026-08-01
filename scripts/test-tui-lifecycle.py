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
    row = 0
    column = 0
    index = 0

    def move_cursor(parameters: str) -> tuple[int, int]:
        values = parameters.split(";")
        cursor_row = int(values[0] or "1") - 1 if values else 0
        cursor_column = int(values[1] or "1") - 1 if len(values) > 1 else 0
        return cursor_row, cursor_column

    while index < len(output):
        sequence = CSI_SEQUENCE.match(output, index)
        if sequence:
            if sequence.group()[-1] in {"H", "f"}:
                row, column = move_cursor(sequence.group()[2:-1])
            index = sequence.end()
            continue

        character = output[index]
        if character == "\r":
            column = 0
        elif character == "\n":
            row += 1
        elif ord(character) >= 32:
            while len(lines) <= row:
                lines.append([])
            line = lines[row]
            while len(line) <= column:
                line.append(" ")
            line[column] = character
            column += 1
        index += 1

    return "\n".join("".join(line).rstrip() for line in lines)


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

    output = normalized_output(captured)
    return all(line in output for line in expected_lines)


def drain_output(
    master_fd: int,
    captured: bytearray,
    cursor_position_responder: CursorPositionResponder,
    deadline: float | None = None,
) -> None:
    while True:
        if deadline is not None and time.monotonic() >= deadline:
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
) -> int:
    deadline = time.monotonic() + TIMEOUT_SECONDS

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


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass

    process.kill()

    try:
        process.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        pass


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
    original_termios = termios.tcgetattr(slave_fd)
    fcntl.ioctl(
        slave_fd,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", 24, 80, 0, 0),
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
            stop_process(process)
            drain_output(master_fd, captured, cursor_position_responder)
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
            stop_process(process)
            drain_output(master_fd, captured, cursor_position_responder)
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
            )
        except subprocess.TimeoutExpired:
            stop_process(process)
            drain_output(master_fd, captured, cursor_position_responder)
            raise AssertionError(
                failure_message(
                    label,
                    "process did not exit within 5 seconds",
                    captured,
                )
            ) from None

        drain_output(master_fd, captured, cursor_position_responder)
        reopened_slave_fd = os.open(slave_name, os.O_RDWR | os.O_NOCTTY)
        try:
            restored_termios = termios.tcgetattr(reopened_slave_fd)
        finally:
            os.close(reopened_slave_fd)
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
        if process is not None:
            stop_process(process)
        os.close(master_fd)
        if not slave_closed:
            os.close(slave_fd)


def main() -> None:
    for language, (banner, command) in CASES.items():
        for exit_name, exit_byte in EXIT_KEYS.items():
            run_case(language, banner, command, exit_name, exit_byte)
            print(f"ok - {language} {exit_name}", flush=True)

    print("all TUI lifecycle PTY scenarios pass")


if __name__ == "__main__":
    main()
