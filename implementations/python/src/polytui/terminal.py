import sys
from collections.abc import Callable
from contextlib import redirect_stderr
from io import StringIO
from typing import TextIO

from polytui.app import PolyTUIApp

NON_TTY_DIAGNOSTIC = "polytui: interactive mode requires a TTY"
INTERNAL_DIAGNOSTIC = "polytui: interactive mode failed"


def run_interactive(
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    app_factory: Callable[[], PolyTUIApp] = PolyTUIApp,
) -> int:
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    if not stdin.isatty() or not stdout.isatty():
        stderr.write(f"{NON_TTY_DIAGNOSTIC}\n")
        return 2

    try:
        with redirect_stderr(StringIO()):
            app = app_factory()
            app.run(
                inline=True,
                inline_no_clear=True,
                mouse=False,
            )
        if app.return_code not in (None, 0):
            stderr.write(f"{INTERNAL_DIAGNOSTIC}\n")
            return 1
        return 0
    except Exception:
        stderr.write(f"{INTERNAL_DIAGNOSTIC}\n")
        return 1
