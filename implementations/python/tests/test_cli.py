import polytui.cli
from typer.testing import CliRunner

from polytui.cli import app

runner = CliRunner()


def test_no_args_uses_cli_runner_streams_for_non_tty_diagnostic() -> None:
    result = runner.invoke(app)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == "polytui: interactive mode requires a TTY\n"


def test_version_flag_uses_shared_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == "polytui 0.1.0-dev.0 (python)\n"


def test_version_does_not_run_interactive(monkeypatch) -> None:
    def run_interactive() -> int:
        raise AssertionError("interactive mode must not run for --version")

    monkeypatch.setattr(polytui.cli, "run_interactive", run_interactive)

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0


def test_help_does_not_run_interactive(monkeypatch) -> None:
    def run_interactive() -> int:
        raise AssertionError("interactive mode must not run for --help")

    monkeypatch.setattr(polytui.cli, "run_interactive", run_interactive)

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
