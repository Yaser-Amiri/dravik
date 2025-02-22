from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Horizontal, Vertical

from dravik.utils import get_app_services, get_app_state


class RefreshScreen(ModalScreen[None]):
    CSS_PATH = "../styles/refresh.tcss"

    def ns(self, name: str) -> str:
        return f"refresh--{name}"

    def compose(self) -> ComposeResult:
        with Vertical(id=self.ns("container")):
            yield Label(
                "Are you sure you want to refresh the data?", classes=self.ns("label")
            )
            with Horizontal(id=self.ns("actions")):
                yield Button("Refresh", variant="primary", id=self.ns("refresh-btn"))
                yield Button("Cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == self.ns("refresh-btn"):
            state = get_app_state(self.app)
            state.ledger_data = get_app_services(self.app).read_hledger_data()
        self.app.pop_screen()
