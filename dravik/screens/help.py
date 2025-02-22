from pathlib import Path
import sys
import importlib.metadata

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Label, Static, Link
from textual.containers import Vertical

from dravik.utils import get_app_services, get_app_state


class HelpScreen(Screen[None]):
    CSS_PATH = "../styles/help.tcss"

    def ns(self, name: str) -> str:
        return f"help--{name}"

    def compose(self) -> ComposeResult:
        home = str(Path.home())
        hledger_stats = get_app_state(self.app).ledger_data.stats
        dist = importlib.metadata.distribution("dravik")
        app_name = dist.metadata["name"]
        app_version = dist.metadata["version"]
        app_summary = dist.metadata["summary"]
        app_authors = dist.metadata.get("Author-Email", "")
        app_urls = dist.metadata.get_all("Project-URL", [])
        services = get_app_services(self.app)
        services.app.config_path

        yield Static(
            (
                f"Paths:\n\n"
                f"Home: {home}\n"
                f"Python: {sys.executable}\n"
                f"Config file: {services.app.config_path}\n"
            ),
            id=self.ns("paths"),
        )
        yield Static(
            f"Hledger Stats:\n\n{hledger_stats}\n", id=self.ns("hledger-stats")
        )
        with Vertical(id=self.ns("about")):
            yield Label("About:\n")
            yield Label(f"Name: {app_name} ({app_summary})")
            yield Label(f"Version: {app_version}")
            yield Label("License: GNU General Public License v3.0 only")
            yield Label("Authros:")
            for author in app_authors.split(","):
                yield Label(author.strip(), classes=self.ns("padded-on-left"))
            yield Label("URLs:")
            for url in app_urls:
                text, href = [a.strip() for a in url.split(",")]
                yield Link(
                    f"{text} ({href})", url=href, classes=self.ns("padded-on-left")
                )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one(f"#{self.ns('hledger-stats')}").focus()
