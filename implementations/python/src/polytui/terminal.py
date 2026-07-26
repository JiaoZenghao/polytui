import sys
from collections.abc import Callable
from typing import TextIO

from polytui.app import PolyTUIApp

NON_TTY_DIAGNOSTIC = "polytui: interactive mode requires a TTY"
INTERNAL_DIAGNOSTIC = "polytui: interactive mode failed"


def run_interactive(
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    app_factory: Callable[[], PolyTUIApp] = PolyTUIApp,
) -> int:
    if not stdin.isatty() or not stdout.isatty():
        stderr.write(f"{NON_TTY_DIAGNOSTIC}\n")
        return 2

    try:
        result = app_factory().run(
            inline=True,
            inline_no_clear=True,
            mouse=False,
        )
        return int(result or 0)
    except Exception:
        stderr.write(f"{INTERNAL_DIAGNOSTIC}\n")
        return 1
