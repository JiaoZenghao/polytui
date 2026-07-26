import polytui.cli
from typer.testing import CliRunner

from polytui.cli import app

runner = CliRunner()


def test_no_args_runs_interactive_and_propagates_exit_code(
    monkeypatch,
) -> None:
    calls = 0

    def run_interactive() -> int:
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(polytui.cli, "run_interactive", run_interactive)

    result = runner.invoke(app)

    assert result.exit_code == 1
    assert calls == 1


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
