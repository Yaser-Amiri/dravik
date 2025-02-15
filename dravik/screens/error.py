from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Horizontal, Vertical
from rich.text import Text

from dravik.utils import get_app_state


class ErrorScreen(ModalScreen[None]):
    CSS_PATH = "../styles/error.tcss"

    def ns(self, name: str) -> str:
        return f"error--{name}"

    def compose(self) -> ComposeResult:
        with Vertical(id=self.ns("container")):
            yield Label("There is an error!\n")
            for err in get_app_state(self.app).errors:
                yield Label(Text(str(err), style="italic #FAFAD2"))

            with Horizontal(id=self.ns("actions")):
                yield Button("Quit", variant="primary", id=self.ns("quit"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == self.ns("quit"):
            self.app.exit()
