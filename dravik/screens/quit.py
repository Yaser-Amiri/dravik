from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Horizontal, Vertical


class QuitScreen(ModalScreen[None]):
    CSS_PATH = "../styles/quit.tcss"

    def ns(self, name: str) -> str:
        return f"quit--{name}"

    def compose(self) -> ComposeResult:
        with Vertical(id=self.ns("container")):
            yield Label("Are you sure you want to quit?", id="quit--label")
            with Horizontal(id=self.ns("actions")):
                yield Button("Quit", variant="error", id=self.ns("quit"))
                yield Button("Cancel", variant="primary", id=self.ns("cancel"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == self.ns("quit"):
            self.app.exit()
        else:
            self.app.pop_screen()
