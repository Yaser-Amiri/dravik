from typing import Any, TypedDict

from rich.text import Text
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Input, Label

from dravik.models import (
    AccountPath,
    AppState,
)
from dravik.utils import get_app_state


class RichTable(DataTable[str | Text]):
    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("l", "cursor_right", "Right", show=False),
        Binding("h", "cursor_left", "Left", show=False),
    ]

    class IngestableDataRow(TypedDict):
        cells: list[str | Text]
        key: str | None
        height: int

    def set_data(self, data: list[IngestableDataRow]) -> None:
        self.clear()
        for r in data:
            self.add_row(*r["cells"], key=r["key"], height=r["height"])


class HoldingsLabel(Label):
    """
    A labels to show holdings of an account, like `123 EUR & 987 USD & 456 BTC`
    """

    def __init__(
        self, account: AccountPath, color: str | None, *args: Any, **kwargs: Any
    ) -> None:
        self.account = account
        super().__init__(*args, **kwargs)
        if color:
            self.styles.background = color

    def on_mount(self) -> None:
        def _x(s: AppState) -> None:
            balance = s.ledger_data.balances.get(self.account, {})
            account_label = s.account_labels.get(self.account, self.account)
            values = " & ".join(
                [
                    f"{amount} {s.currency_labels.get(currency, currency)}"
                    for currency, amount in balance.items()
                ]
            )
            if values:
                self.update(f"{account_label} => {values}")
            else:
                self.update(f"{account_label} => 0")

        self.watch(self.app, "state", _x)


class AccountPathInput(Input):
    BINDINGS = [
        Binding("ctrl+y", "autocomplete", "Auto Complete"),
    ]

    def _suggest_account(self, state: AppState, word: str) -> AccountPath | None:
        word_sub_count = word.count(":")
        all_accounts: set[AccountPath] = set()
        if word in all_accounts:
            return word
        for account in state.ledger_data.balances:
            sa = account.split(":")
            if len(sa) != word_sub_count + 1:
                continue
            all_accounts |= {":".join(sa[: i + 1]) for i in range(len(sa))}

        g = {a for a in all_accounts if a.startswith(word)}
        if len(g) == 1:
            return list(g)[0]

        return None

    def action_autocomplete(self) -> None:
        state = get_app_state(self.app)
        if suggested := self._suggest_account(state, self.value):
            self.clear()
            self.insert(suggested, 0)


class RichVerticalScroll(VerticalScroll):
    BINDINGS = [
        ("j", "scroll_down", "Scroll down"),
        ("k", "scroll_up", "Scroll up"),
    ]
