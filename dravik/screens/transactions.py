from abc import abstractmethod
from collections.abc import Callable
from datetime import date, timedelta
from functools import partial
from itertools import groupby
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import (
    Grid,
    ScrollableContainer,
    Vertical,
    VerticalScroll,
)
from textual.events import Resize
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Input,
    Label,
    MaskedInput,
    Static,
    Tree,
)

from dravik.models import (
    AccountPath,
    AppState,
    LedgerPosting,
    LedgerSnapshot,
    LedgerTransaction,
)
from dravik.screens.refresh import RefreshScreen
from dravik.utils import get_app_state, mutate_app_state
from dravik.validators import Date
from dravik.widgets import AccountPathInput, HoldingsLabel, RichTable


class TransactionsTable(RichTable):
    """
    A table that shows list of ledger transactions and reads it from state of the app.
    """

    BINDINGS = [
        Binding(".", "toggle_total", "Toggle Total"),
    ]

    def __init__(
        self, select_callback: Callable[[str | None], None], *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.select_callback = select_callback
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("Date", "Description", "Amount", "Out-Goings", "In-Goings")

    def action_toggle_total(self) -> None:
        state = get_app_state(self.app)
        state.show_total_row_in_transactions_table = (
            not state.show_total_row_in_transactions_table
        )
        mutate_app_state(self.app)

    def on_data_table_row_selected(self, e: DataTable.RowSelected) -> None:
        id = e.row_key.value
        self.select_callback(id)

    def _posting_text_fmt(self, left: str, right: str, width: int = 80) -> str:
        """
        Format a posting in a specific width, like: `assets:banks:chase    100 USD`
        """
        space = max(0, width - len(left) - len(right))
        return f"{left}{' ' * space}{right}"

    def _posting_cell_fmt(self, postings: list[LedgerPosting], w: int) -> Text:
        """
        Renders postings that blong to the same cell (either in/out goings)
        """
        account_labels = get_app_state(self.app).account_labels
        currency_labels = get_app_state(self.app).currency_labels
        r = ""
        for p in postings:
            r += self._posting_text_fmt(
                account_labels.get(p.account, p.account),
                f"{p.amount} {currency_labels.get(p.currency, p.currency)}\n",
                w + 3,
            )
        return Text(r, style="italic #FAFAD2", justify="right")

    def _calculate_postings_col_width(self, data: list[LedgerPosting]) -> int:
        """
        Calculates width of a cell that should contain postings
        """
        account_labels = get_app_state(self.app).account_labels
        currency_labels = get_app_state(self.app).currency_labels
        return max(
            [
                len(
                    f"{account_labels.get(a.account, a.account)} {a.amount}"
                    f"{currency_labels.get(a.currency, a.currency)}"
                )
                for a in data
            ]
            + [10],  # default size
        )

    def _calculate_total_col_value(self, postings: list[LedgerPosting]) -> str:
        """
        Calculates value of `total amount` column, returns string like `10 $\n20 EUR`
        """
        postings = sorted(
            [p for p in postings if p.amount >= 0], key=lambda x: x.currency
        )
        currency_labels = get_app_state(self.app).currency_labels

        sum_per_currency = {}
        for currency, group in groupby(postings, lambda x: x.currency):
            sum_per_currency[currency] = sum([p.amount for p in group] + [0])

        return "\n".join(
            [f"{v} {currency_labels.get(k, k)}" for k, v in sum_per_currency.items()]
        )

    def _regenerate_table_data(
        self, ledger_data: LedgerSnapshot
    ) -> list[RichTable.IngestableDataRow]:
        """
        Recalculates rows of the table and returns them.
        """
        rows: list[RichTable.IngestableDataRow] = []
        state = get_app_state(self.app)
        filter_functions = state.transactions_list_filters.values()
        transactions = [
            tx
            for tx in ledger_data.transactions
            if all(fn(tx) for fn in filter_functions)
        ]

        ingoing_postings = [
            p for tx in transactions for p in tx.postings if p.amount > 0
        ]
        outgoing_postings = [
            p for tx in transactions for p in tx.postings if p.amount < 0
        ]
        ingoing_col_width = self._calculate_postings_col_width(ingoing_postings)
        outgoing_col_width = self._calculate_postings_col_width(outgoing_postings)

        for tx in sorted(transactions, key=lambda x: x.date, reverse=True):
            total_tx_amount = self._calculate_total_col_value(tx.postings)
            ingoing_postings_cell = self._posting_cell_fmt(
                [p for p in tx.postings if p.amount > 0],
                ingoing_col_width,
            )
            outgoing_postings_cell = self._posting_cell_fmt(
                [p for p in tx.postings if p.amount < 0],
                outgoing_col_width,
            )
            rows.append(
                {
                    "cells": [
                        str(tx.date),
                        tx.description[:30]
                        + ("" if len(tx.description) <= 30 else " ✂"),
                        f"{total_tx_amount}",
                        outgoing_postings_cell,
                        ingoing_postings_cell,
                    ],
                    "key": tx.id,
                    "height": max(
                        1,
                        str(outgoing_postings_cell).count("\n"),
                        str(ingoing_postings_cell).count("\n"),
                        total_tx_amount.count("\n") + 1,
                    ),
                }
            )

        if state.show_total_row_in_transactions_table:
            total_amount = self._calculate_total_col_value(
                [p for tx in transactions for p in tx.postings]
            )
            rows.insert(
                0,
                {
                    "cells": ["", "T O T A L", total_amount, "", ""],
                    "key": "TOTAL",
                    "height": max(1, total_amount.count("\n") + 1),
                },
            )
        return rows

    def on_mount(self) -> None:
        def _x(s: AppState) -> None:
            self.set_data(self._regenerate_table_data(s.ledger_data))

        self.watch(self.app, "state", _x)


class AccountsTree(Tree[str]):
    BINDINGS = [
        ("j", "cursor_down", "Cursor Up"),
        ("k", "cursor_up", "Cursor Down"),
    ]

    def __init__(
        self,
        select_callback: Callable[[AccountPath], None],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__("Accounts", *args, **kwargs)
        self.auto_expand = False
        self.select_callback = select_callback

    def on_tree_node_selected(self, n: Tree.NodeSelected[str]) -> None:
        if n.node.data is None:
            return
        self.select_callback(n.node.data)

    def on_mount(self) -> None:
        def _x(e: AppState) -> None:
            self.clear()
            nodes_map_by_path = {"": self.root}

            # filter by seach inputs
            balances = [
                (path, holdings)
                for path, holdings in e.ledger_data.balances.items()
                if all(fn(path) for fn in e.accounts_tree_filters)
            ]

            # sort is important to make it DFS
            # because api of creaing a node as leaf or regular node is different
            # and we want dont to make a leaf named "assets" when we have an path
            # like "assets:bank:chase"
            balances.sort(key=lambda x: x[0].count(":"), reverse=True)

            for path, _ in balances:
                account_sections = path.split(":")
                for indx, section in enumerate(account_sections):
                    new_node_path = ":".join(account_sections[: indx + 1])
                    if new_node_path in nodes_map_by_path:
                        continue

                    prev_node_path = ":".join(account_sections[:indx])
                    prev_node = nodes_map_by_path[prev_node_path]
                    add_node_fn = (
                        prev_node.add_leaf
                        if len(account_sections) == indx + 1
                        else partial(prev_node.add, expand=True)
                    )
                    account_label = e.account_labels.get(
                        new_node_path, section.capitalize()
                    )
                    new_node = add_node_fn(label=account_label, data=new_node_path)
                    nodes_map_by_path[new_node_path] = new_node

            self.root.expand()

        self.watch(self.app, "state", _x)


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
                f"There are {count_str} transactions with this "
                f"ID ({self.transaction_id}).",
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
                yield Label(f"Date: {tx.date!s}")
                if tx.secondary_date:
                    yield Label(f"Secondary Date: {tx.secondary_date!s}")
                yield Label(f"Description: {tx.description}")
                yield Label(f"Status: {tx.status.capitalize()}")
                yield Label("\nPostings:")
                for posting in tx.postings:
                    left = f"    {posting.account}:"
                    right = f"{posting.amount} {posting.currency}"
                    yield Label(
                        Text(_posting_text_fmt(left, right, 50), style="#03AC13")
                    )

                if tx.tags:
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
    def __init__(
        self, on_submit: Callable[[], None] | None = None, **kwargs: Any
    ) -> None:
        self.on_submit = on_submit
        super().__init__(**kwargs)

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

    async def action_submit(self) -> None:
        if self.on_submit:
            self.on_submit()


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


class TransactionAccountSearch(AccountPathInput, TransactionBaseSearchInput):
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
        Binding("0", "clear_date_filters", "Clear Date Filters", show=False),
        Binding("1", "filter_current_week", "Filter Current Week", show=False),
        Binding("2", "filter_current_month", "Filter Current Month", show=False),
        Binding("3", "filter_previous_week", "Filter Previous Week", show=False),
        Binding("4", "filter_previous_month", "Filter Previous Month", show=False),
        Binding("a", "focus_on_accounts_search_input", "Search Account"),
        Binding("s", "focus_on_transaction_search_input", "Search Transaction"),
        Binding("t", "focus_on_table", "Focus On Table"),
        Binding("e", "focus_on_tree", "Focus On Tree"),
        Binding("r", "request_refresh", "Refresh"),
        Binding("escape", "focus_on_pane", "Unfocus"),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.description_search_input: TransactionDescriptionSearch | None = None
        self.from_date_input: TransactionFromDateSearch | None = None
        self.to_date_input: TransactionToDateSearch | None = None
        self.account_search_input: TransactionAccountSearch | None = None
        super().__init__(*args, **kwargs)

    def action_request_refresh(self) -> None:
        self.app.push_screen(RefreshScreen())

    def ns(self, name: str) -> str:
        return f"transactions--{name}"

    def show_account_details(self, account: AccountPath) -> None:
        self.app.push_screen(AccountDetailsScreen(account))

    def show_transaction_details(self, transaction_id: str | None) -> None:
        self.app.push_screen(TransactionDetailsScreen(transaction_id))

    def _set_date_filters(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> None:
        if self.from_date_input is None or self.to_date_input is None:
            return

        self.from_date_input.clear()
        self.to_date_input.clear()
        if from_date is not None:
            self.from_date_input.insert(str(from_date), 0)
        if to_date is not None:
            self.to_date_input.insert(str(to_date), 0)

    def action_clear_date_filters(self) -> None:
        self._set_date_filters(None, None)

    def action_filter_current_week(self) -> None:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        self._set_date_filters(start_of_week, end_of_week)

    def action_filter_current_month(self) -> None:
        today = date.today()
        start_of_month = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_of_month = next_month.replace(day=1) - timedelta(days=1)
        self._set_date_filters(start_of_month, end_of_month)

    def action_filter_previous_week(self) -> None:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday() + 7)
        end_of_week = start_of_week + timedelta(days=6)
        self._set_date_filters(start_of_week, end_of_week)

    def action_filter_previous_month(self) -> None:
        today = date.today()
        first_of_this_month = today.replace(day=1)
        last_of_previous_month = first_of_this_month - timedelta(days=1)
        start_of_previous_month = last_of_previous_month.replace(day=1)
        self._set_date_filters(start_of_previous_month, last_of_previous_month)

    def compose(self) -> ComposeResult:
        self.description_search_input = TransactionDescriptionSearch(
            on_submit=self._focus_on_table,
            placeholder="...",
            id=self.ns("description-search"),
        )
        self.from_date_input = TransactionFromDateSearch(
            on_submit=self._focus_on_table,
            placeholder="1970-01-01",
        )
        self.to_date_input = TransactionToDateSearch(
            on_submit=self._focus_on_table,
            placeholder="2040-12-31",
        )
        self.account_search_input = TransactionAccountSearch(
            on_submit=self._focus_on_table,
            placeholder="Path or Label",
        )

        with VerticalScroll():
            yield Static("Dravik / Transactions", id=self.ns("header"))
            with ScrollableContainer(id=self.ns("grid")):
                with VerticalScroll(id=self.ns("left-side")):
                    yield AccountTreeSearch(
                        placeholder="Search account ...",
                        id=self.ns("accounts-tree-search"),
                        on_submit=self.action_focus_on_tree,
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
                        yield self.description_search_input
                        yield self.from_date_input
                        yield self.to_date_input
                        yield self.account_search_input
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
