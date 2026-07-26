from typer.testing import CliRunner

from polytui.cli import app

runner = CliRunner()


def test_version_flag_uses_shared_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == "polytui 0.1.0-dev.0 (python)\n"
