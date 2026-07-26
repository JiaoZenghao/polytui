from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static


class PolyTUIApp(App[int]):
    INLINE_PADDING = 0
    CSS = """
    Screen {
        height: 2;
    }
    #startup {
        height: 2;
    }
    """
    BINDINGS = [
        Binding("ctrl+c", "exit_success", show=False, priority=True),
        Binding("ctrl+d", "exit_success", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            "PolyTUI · Python\nPress Ctrl+C or Ctrl+D to exit",
            id="startup",
        )

    def action_exit_success(self) -> None:
        self.exit(result=0, return_code=0)
