from collections.abc import Callable
from functools import partial
from itertools import groupby
from typing import Any, TypedDict

from rich.text import Text
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Input, Label, Tree

from dravik.models import (
    AccountPath,
    AppState,
    LedgerPosting,
    LedgerSnapshot,
    LedgerTransaction,
)
from dravik.utils import get_app_state


class RichTable(DataTable[str | Text]):
    BINDINGS = [
        ("j", "cursor_down", "Move down"),
        ("k", "cursor_up", "Move up"),
    ]

    class IngestableDataRow(TypedDict):
        cells: list[str | Text]
        key: str | None
        height: int

    def set_data(self, data: list[IngestableDataRow]) -> None:
        self.clear()
        for r in data:
            self.add_row(*r["cells"], key=r["key"], height=r["height"])


class TransactionsTable(RichTable):
    """
    A table that shows list of ledger transactions and reads it from state of the app.
    """

    def __init__(
        self, select_callback: Callable[[str | None], None], *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.select_callback = select_callback
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("Date", "Description", "Amount", "In-Goings", "Out-Goings")

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
        width = 10  # default
        account_labels = get_app_state(self.app).account_labels
        currency_labels = get_app_state(self.app).currency_labels
        text_lenght = max(
            [
                len(
                    f"{account_labels.get(a.account, a.account)} {a.amount}"
                    f"{currency_labels.get(a.currency, a.currency)}"
                )
                for a in data
            ]
            + [0],
            default=width,
        )
        if text_lenght > width:
            width = text_lenght
        return width

    def _calculate_total_col_value(self, tx: LedgerTransaction) -> str:
        """
        Calculates value of `total amount` column, returns string like `10 $\n20 EUR`
        """
        postings = sorted(
            [p for p in tx.postings if p.amount >= 0], key=lambda x: x.currency
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
        filter_functions = get_app_state(self.app).transactions_list_filters.values()
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
            total_tx_amount = self._calculate_total_col_value(tx)
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
                        ingoing_postings_cell,
                        outgoing_postings_cell,
                    ],
                    "key": tx.id,
                    "height": max(
                        1,
                        str(outgoing_postings_cell).count("\n"),
                        str(ingoing_postings_cell).count("\n"),
                        total_tx_amount.count("\n"),
                    ),
                }
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
