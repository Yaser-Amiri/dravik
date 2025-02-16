from datetime import date
from functools import partial
from typing import Any, Callable
from abc import abstractmethod


from rich.text import Text
from textual.events import Resize
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import (
    Grid,
    Vertical,
    VerticalScroll,
    ScrollableContainer,
)
from textual.widgets import Footer, Static, Input, Label, Button, MaskedInput

from dravik.models import AccountPath, LedgerTransaction
from dravik.utils import get_app_state, mutate_app_state
from dravik.widgets import HoldingsLabel, TransactionsTable, AccountsTree
from dravik.validators import Date
from dravik.screens.refresh import RefreshScreen


class AccountDetailsScreen(ModalScreen[None]):
    CSS_PATH = "../styles/account_details.tcss"

    def __init__(self, account: AccountPath, *args: Any, **kwargs: Any) -> None:
        self.account = account
        super().__init__(*args, **kwargs)

    def ns(self, name: str) -> str:
        return f"account-details--{name}"

    def compose(self) -> ComposeResult:
        app_state = get_app_state(self.app)
        label = app_state.account_labels.get(self.account, "-")
        balance = " & ".join(
            [
                f"{amount} {currency}"
                for currency, amount in app_state.ledger_data.balances.get(
                    self.account, {}
                ).items()
            ]
        )
        with Vertical(id=self.ns("container")):
            yield Label(Text(f"Account Path: {self.account}"), classes=self.ns("label"))
            yield Label(Text(f"Label: {label}"), classes=self.ns("label"))
            yield Label(Text(f"Balance: {balance}"), classes=self.ns("label"))
            with Vertical(id=self.ns("actions")):
                yield Button("OK", variant="primary", id=self.ns("ok-btn"))

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.app.pop_screen()


class TransactionDetailsScreen(ModalScreen[None]):
    CSS_PATH = "../styles/transaction_details.tcss"

    def __init__(
        self, transaction_id: str | None = None, *args: Any, **kwargs: Any
    ) -> None:
        self.transaction_id = transaction_id
        super().__init__(*args, **kwargs)

    def ns(self, name: str) -> str:
        return f"transaction-details--{name}"

    def _compose_no_transaction_id(self) -> ComposeResult:
        with Vertical(id=self.ns("container")):
            yield Label(
                "This transaction doesn't have an ID.", classes=self.ns("label")
            )
            with Vertical(id=self.ns("actions")):
                yield Button("OK", variant="primary", id=self.ns("ok-btn"))

    def _compose_invalid_transaction_id(self, count: int) -> ComposeResult:
        with Vertical(id=self.ns("container")):
            count_str = "no" if count == 0 else str(count)
            yield Label(
                f"There are {count_str} transactions with this ID ({self.transaction_id}).",
                classes=self.ns("label"),
            )
            with Vertical(id=self.ns("actions")):
                yield Button("OK", variant="primary", id=self.ns("ok-btn"))

    def _compose_transaction_details(self, tx: LedgerTransaction) -> ComposeResult:
        def _posting_text_fmt(left: str, right: str, width: int = 80) -> str:
            space = max(0, width - len(left) - len(right))
            return f"{left}{' ' * space}{right}"

        with Vertical(id=self.ns("container")):
            with Vertical(id=self.ns("postings")):
                yield Label(f"{str(tx.date)}")
                yield Label(f"Description: {tx.description}")
                yield Label("\nPostings:")
                for posting in tx.postings:
                    left = f"    {posting.account}:"
                    right = f"{posting.amount} {posting.currency}"
                    yield Label(
                        Text(_posting_text_fmt(left, right, 50), style="#03AC13")
                    )

                yield Label("\nTags:")
                for tag_key, tag_value in tx.tags.items():
                    yield Label(Text(f"{tag_key}: {tag_value}", style="#FF4500"))

            with Vertical(id=self.ns("actions")):
                yield Button("OK", variant="primary", id=self.ns("ok-btn"))

    def compose(self) -> ComposeResult:
        ledger_data = get_app_state(self.app).ledger_data

        if self.transaction_id is None:
            yield from self._compose_no_transaction_id()
            return

        transactions = [
            t for t in ledger_data.transactions if t.id == self.transaction_id
        ]
        if len(transactions) != 1:
            yield from self._compose_invalid_transaction_id(len(transactions))
            return

        yield from self._compose_transaction_details(transactions[0])

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.app.pop_screen()


class AccountTreeSearch(Input):
    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)
        word = e.value.strip()

        if not word:
            state.accounts_tree_filters = []
            mutate_app_state(self.app)
            return

        def _search_filter(path: AccountPath) -> bool:
            label = state.account_labels.get(path, path.lower())
            return word.lower() in path.lower() or word.lower() in label.lower()

        state.accounts_tree_filters = [_search_filter]
        mutate_app_state(self.app)


class TransactionBaseSearchInput(Input):
    def __init__(
        self, on_submit: Callable[[], None] | None = None, **kwargs: Any
    ) -> None:
        self.on_submit = on_submit
        super().__init__(**kwargs)

    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)
        word = e.value.strip()

        if not word:
            state.transactions_list_filters[self.filter_key] = lambda _: True
            mutate_app_state(self.app)
            return

        state.transactions_list_filters[self.filter_key] = partial(
            self._search_filter, word
        )
        mutate_app_state(self.app)

    @abstractmethod
    def _search_filter(self, word: str, tx: LedgerTransaction) -> bool:
        pass

    @property
    @abstractmethod
    def filter_key(self) -> str:
        pass

    async def action_submit(self) -> None:
        if self.on_submit:
            self.on_submit()


class TransactionDescriptionSearch(TransactionBaseSearchInput):
    @property
    def filter_key(self) -> str:
        return "DESCRIPTION"

    def _search_filter(self, word: str, tx: LedgerTransaction) -> bool:
        return word.lower() in tx.description.lower()


class TransactionAccountSearch(TransactionBaseSearchInput):
    @property
    def filter_key(self) -> str:
        return "ACCOUNT"

    def _search_filter(self, word: str, tx: LedgerTransaction) -> bool:
        app_state = get_app_state(self.app)

        accounts_path_set = {p.account.lower() for p in tx.postings}
        accounts_label_set = {
            app_state.account_labels.get(p.account, "").lower() for p in tx.postings
        }
        for account in accounts_path_set | accounts_label_set:
            if word.lower() in account:
                return True
        return False


class TransactionFromDateSearch(TransactionBaseSearchInput, MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "0000-00-00")
        validators = kwargs.pop("validators", []) + [Date()]
        super().__init__(template=template, validators=validators, **kwargs)

    @property
    def filter_key(self) -> str:
        return "FROM_DATE"

    def _search_filter(self, word: str, tx: LedgerTransaction) -> bool:
        try:
            from_date = date(*[int(p) for p in word.split("-") if p])
            return tx.date >= from_date
        except (TypeError, ValueError):
            return True


class TransactionToDateSearch(TransactionBaseSearchInput, MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "0000-00-00")
        validators = kwargs.pop("validators", []) + [Date()]

        super().__init__(template=template, validators=validators, **kwargs)

    @property
    def filter_key(self) -> str:
        return "TO_DATE"

    def _search_filter(self, word: str, tx: LedgerTransaction) -> bool:
        try:
            to_date = date(*[int(p) for p in word.split("-") if p])
            return tx.date <= to_date
        except (TypeError, ValueError):
            return True


class TransactionsScreen(Screen[None]):
    CSS_PATH = "../styles/transactions.tcss"

    BINDINGS = [
        ("a", "focus_on_accounts_search_input", "Search Account"),
        ("s", "focus_on_transaction_search_input", "Search Transaction"),
        ("t", "focus_on_table", "Focus On Transactions Tabel"),
        ("e", "focus_on_tree", "Focus On Accounts Tree"),
        ("r", "request_refresh", "Refresh"),
        ("escape", "focus_on_pane", "Unfocus"),
    ]

    def action_request_refresh(self) -> None:
        self.app.push_screen(RefreshScreen())

    def ns(self, name: str) -> str:
        return f"transactions--{name}"

    def show_account_details(self, account: AccountPath) -> None:
        self.app.push_screen(AccountDetailsScreen(account))

    def show_transaction_details(self, transaction_id: str | None) -> None:
        self.app.push_screen(TransactionDetailsScreen(transaction_id))

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("Dravik / Transactions", id=self.ns("header"))
            with ScrollableContainer(id=self.ns("grid")):
                with VerticalScroll(id=self.ns("left-side")):
                    yield AccountTreeSearch(
                        placeholder="Search account ...",
                        id=self.ns("accounts-tree-search"),
                    )
                    yield AccountsTree(
                        self.show_account_details,
                        id=self.ns("accounts_tree"),
                    )
                with Vertical(id=self.ns("right-side")):
                    with Grid(id=self.ns("statusbar")):
                        for account, color in get_app_state(self.app).pinned_accounts:
                            yield HoldingsLabel(
                                account, color=color, classes=self.ns("holding")
                            )

                    with Grid(id=self.ns("searchbar-labels")):
                        yield Label("Description:")
                        yield Label("From Date:")
                        yield Label("To Date:")
                        yield Label("Account:")

                    with Grid(id=self.ns("searchbar-inputs")):
                        yield TransactionDescriptionSearch(
                            on_submit=self._focus_on_table,
                            placeholder="...",
                            id=self.ns("description-search"),
                        )
                        yield TransactionFromDateSearch(
                            on_submit=self._focus_on_table, placeholder="1970-01-01"
                        )
                        yield TransactionToDateSearch(
                            on_submit=self._focus_on_table,
                            placeholder="2040-12-31",
                        )
                        yield TransactionAccountSearch(
                            on_submit=self._focus_on_table, placeholder="Path or Label"
                        )

                    yield TransactionsTable(
                        self.show_transaction_details,
                        id=self.ns("dtble"),
                    )
        yield Footer()

    def action_focus_on_accounts_search_input(self) -> None:
        self.query_one(f"#{self.ns('accounts-tree-search')}").focus()

    def action_focus_on_transaction_search_input(self) -> None:
        self.query_one(f"#{self.ns('description-search')}").focus()

    def action_focus_on_table(self) -> None:
        self._focus_on_table()

    def _focus_on_table(self) -> None:
        self.query_one(f"#{self.ns('dtble')}").focus()

    def action_focus_on_tree(self) -> None:
        self.query_one(f"#{self.ns('accounts_tree')}").focus()

    def action_focus_on_pane(self) -> None:
        self.query_one(f"#{self.ns('grid')}").focus()

    def _resize_transactions_table_to_optimal(self) -> None:
        """
        Calculates used height by components except the table,
        and finds the optimal height for transaction tables and sets it.
        """
        used_heights = sum(
            [
                self.query_one(f"#{self.ns('statusbar')}").size.height,
                self.query_one(f"#{self.ns('searchbar-labels')}").size.height,
                self.query_one(f"#{self.ns('searchbar-inputs')}").size.height,
            ]
        )
        remaining_height = max(1, self.app.size.height - used_heights)
        # No idea why 7 is the best!
        self.query_one(f"#{self.ns('dtble')}").styles.height = remaining_height - 7

    def on_resize(self, _: Resize) -> None:
        self._resize_transactions_table_to_optimal()
