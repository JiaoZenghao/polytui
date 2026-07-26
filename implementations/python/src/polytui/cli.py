from typing import Annotated

import typer

from polytui.build_info import VERSION_TEXT
from polytui.terminal import run_interactive

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Learn CLI/TUI development across four languages.",
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(VERSION_TEXT)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    del version
    result = run_interactive()
    if result:
        raise typer.Exit(code=result)
