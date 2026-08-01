from io import StringIO

import pytest

from polytui.app import PolyTUIApp
from polytui.terminal import run_interactive


class TextStream(StringIO):
    def __init__(self, is_tty: bool) -> None:
        super().__init__()
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


@pytest.mark.parametrize("stdin_is_tty, stdout_is_tty", [(False, True), (True, False)])
def test_non_tty_stream_does_not_construct_app(
    stdin_is_tty: bool,
    stdout_is_tty: bool,
) -> None:
    stdout = TextStream(is_tty=stdout_is_tty)
    stderr = TextStream(is_tty=True)
    constructed = False

    def app_factory() -> object:
        nonlocal constructed
        constructed = True
        raise AssertionError("the TUI must not be constructed")

    exit_code = run_interactive(
        stdin=TextStream(is_tty=stdin_is_tty),
        stdout=stdout,
        stderr=stderr,
        app_factory=app_factory,
    )

    assert exit_code == 2
    assert not constructed
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "polytui: interactive mode requires a TTY\n"


def test_app_failure_returns_internal_diagnostic_only() -> None:
    stdout = TextStream(is_tty=True)
    stderr = TextStream(is_tty=True)

    def app_factory() -> object:
        raise RuntimeError("construction failed")

    exit_code = run_interactive(
        stdin=TextStream(is_tty=True),
        stdout=stdout,
        stderr=stderr,
        app_factory=app_factory,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "polytui: interactive mode failed\n"


def test_app_run_failure_returns_internal_diagnostic_only() -> None:
    stdout = TextStream(is_tty=True)
    stderr = TextStream(is_tty=True)

    class FailingApp:
        def run(self, **kwargs: bool) -> int:
            raise RuntimeError("run failed")

    exit_code = run_interactive(
        stdin=TextStream(is_tty=True),
        stdout=stdout,
        stderr=stderr,
        app_factory=FailingApp,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "polytui: interactive mode failed\n"


def test_textual_lifecycle_failure_returns_internal_diagnostic_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    stdout = TextStream(is_tty=True)
    stderr = TextStream(is_tty=True)

    class FailingTextualApp(PolyTUIApp):
        def on_mount(self) -> None:
            raise RuntimeError("mount failed")

        def run(self, **kwargs: bool) -> int | None:
            return super().run(headless=True, **kwargs)

    exit_code = run_interactive(
        stdin=TextStream(is_tty=True),
        stdout=stdout,
        stderr=stderr,
        app_factory=FailingTextualApp,
    )

    captured = capsys.readouterr()
    assert (
        exit_code,
        stdout.getvalue(),
        stderr.getvalue(),
        captured.err,
    ) == (
        1,
        "",
        "polytui: interactive mode failed\n",
        "",
    )


def test_successful_app_uses_inline_terminal_options() -> None:
    stdout = TextStream(is_tty=True)
    stderr = TextStream(is_tty=True)
    options: dict[str, bool] = {}

    class SuccessfulApp:
        return_code = 0

        def run(self, **kwargs: bool) -> int:
            options.update(kwargs)
            return 0

    exit_code = run_interactive(
        stdin=TextStream(is_tty=True),
        stdout=stdout,
        stderr=stderr,
        app_factory=SuccessfulApp,
    )

    assert exit_code == 0
    assert options == {
        "inline": True,
        "inline_no_clear": True,
        "mouse": False,
    }
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""
