import pytest
from textual.widgets import Static

from polytui.app import PolyTUIApp


@pytest.mark.asyncio
async def test_startup_view_and_ctrl_c() -> None:
    app = PolyTUIApp()

    async with app.run_test() as pilot:
        startup = app.query_one("#startup", Static)
        assert str(startup.content) == (
            "PolyTUI · Python\nPress Ctrl+C or Ctrl+D to exit"
        )
        await pilot.press("ctrl+c")

    assert app.return_value == 0


@pytest.mark.asyncio
async def test_ctrl_d_exits_successfully() -> None:
    app = PolyTUIApp()

    async with app.run_test() as pilot:
        await pilot.press("ctrl+d")

    assert app.return_value == 0
