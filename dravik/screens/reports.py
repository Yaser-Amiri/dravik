import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    MaskedInput,
    Static,
)

from dravik.models import AppState, ReportsFilters, ReportType
from dravik.utils import get_app_services, get_app_state, mutate_app_state
from dravik.validators import Date
from dravik.widgets import RichTable


def request_for_update_reports(app: App[object]) -> None:
    state = get_app_state(app)
    state.last_reports_request_time = datetime.now().timestamp()
    mutate_app_state(app)


class ReportsSubmitButton(Button):
    def on_button_pressed(self) -> None:
        request_for_update_reports(self.app)


class ReportsFromDateInput(MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "9999-99-99")
        validators = kwargs.pop("validators", []) + [Date()]
        super().__init__(template=template, validators=validators, **kwargs)

    async def action_submit(self) -> None:
        request_for_update_reports(self.app)

    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)

        try:
            filter_value = date(*[int(p) for p in e.value.strip().split("-") if p])
        except (TypeError, ValueError):
            filter_value = None

        state.reports_filters["from_date"] = filter_value
        mutate_app_state(self.app)


class ReportsToDateInput(MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "9999-99-99")
        validators = kwargs.pop("validators", []) + [Date()]
        super().__init__(template=template, validators=validators, **kwargs)

    async def action_submit(self) -> None:
        request_for_update_reports(self.app)

    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)

        try:
            filter_value = date(*[int(p) for p in e.value.strip().split("-") if p])
        except (TypeError, ValueError):
            filter_value = None

        state.reports_filters["to_date"] = filter_value
        mutate_app_state(self.app)


class ReportTable(RichTable):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_reports_request_time: float = -1
        self.cursor_type = "row"
        self.zebra_stripes = False
        self.show_header = False
        self.cell_padding = 3
        self.add_columns("Categories", "Balance")

    def on_mount(self) -> None:
        def _x(s: AppState) -> None:
            if self.last_reports_request_time == s.last_reports_request_time:
                return
            self.last_reports_request_time = s.last_reports_request_time
            self._update(s.reports_filters)
            self.refresh(layout=True)

        self.watch(self.app, "state", _x)

    def _update(self, filters: ReportsFilters) -> None:
        state = get_app_state(self.app)
        hledger = get_app_services(self.app).get_hledger()
        hledger_result = hledger.get_report(
            state.requested_report,
            filters["from_date"] or datetime.now().date() - timedelta(days=30),
            filters["to_date"] or datetime.now().date(),
        )
        account_labels = state.account_labels
        currency_labels = state.currency_labels

        self.clear()
        self.add_row(Text(hledger_result.title, style="bold #FAFAD2"))

        for section in hledger_result.sections:
            self.add_row()
            self.add_row(Text(section.title, style="bold #FAFAD2"), "")
            for account, balance in section.per_account.items():
                balance_str = " & ".join(
                    [
                        f"{amount} {currency_labels.get(currency, currency)}"
                        for currency, amount in balance.items()
                    ]
                )
                self.add_row(Text(account_labels.get(account, account)), balance_str)

        # Net
        self.add_row()
        total_balance_str = " & ".join(
            [
                f"{amount} {currency_labels.get(currency, currency)}"
                for currency, amount in hledger_result.total.items()
            ]
        )
        self.add_row(Text("Net:", style="bold #FAFAD2"), total_balance_str)
        self.add_row()


class ReportsScreen(Screen[None]):
    CSS_PATH = "../styles/reports.tcss"

    BINDINGS = [
        Binding("s", "focus_on_filters", "Focus On Filters"),
        Binding("i", "focus_on_table", "Focus On Table"),
        Binding("escape", "unfocus", "Unfocus"),
        Binding("0", "reset_date_filters", "Reset Date Filters", show=False),
        Binding("1", "filter_current_week", "Filter Current Week", show=False),
        Binding("2", "filter_current_month", "Filter Current Month", show=False),
        Binding("3", "filter_previous_week", "Filter Previous Week", show=False),
        Binding("4", "filter_previous_month", "Filter Previous Month", show=False),
        Binding("b", "show_balancesheet", "Balance Sheet"),
        Binding("n", "show_incomestatement", "Income Statement"),
        Binding("m", "show_cashflow", "Cash Flow"),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.from_date_input: ReportsFromDateInput | None
        self.to_date_input: ReportsToDateInput | None
        super().__init__(*args, **kwargs)

    def ns(self, name: str) -> str:
        return f"reports--{name}"

    def compose(self) -> ComposeResult:
        today = datetime.now()
        self.from_date_input = ReportsFromDateInput(
            placeholder="1970-01-01",
            value=(today - timedelta(days=30)).strftime("%Y-%m-%d"),
            id=self.ns("from-date-filter"),
        )
        self.to_date_input = ReportsToDateInput(
            placeholder="2040-12-31",
            value=today.strftime("%Y-%m-%d"),
        )

        yield Static("Dravik / Reports", id=self.ns("header"))
        with Vertical(id=self.ns("container")):
            with Grid(id=self.ns("searchbar-labels")):
                yield Label("")
                yield Label("From Date:")
                yield Label("To Date:")
                yield Label("")
                yield Label("")

            with Grid(id=self.ns("searchbar-inputs")):
                yield Label("")
                yield self.from_date_input
                yield self.to_date_input
                yield ReportsSubmitButton(
                    "Submit Filters",
                    variant="primary",
                    id=self.ns("submit"),
                )
                yield Label("")

            with Container(id=self.ns("tbl-container")):
                yield ReportTable(id=self.ns("table"))

        yield Footer()

    def action_focus_on_filters(self) -> None:
        self.query_one(f"#{self.ns('from-date-filter')}").focus()

    def action_focus_on_table(self) -> None:
        self.query_one(f"#{self.ns('table')}").focus()

    def action_unfocus(self) -> None:
        self.query_one(f"#{self.ns('submit')}").focus()

    def on_mount(self) -> None:
        self.query_one(f"#{self.ns('submit')}").focus()

    async def _set_date_filters(self, from_date: date, to_date: date) -> None:
        if self.from_date_input is None or self.to_date_input is None:
            return

        self.from_date_input.insert(str(from_date), 0)
        self.to_date_input.insert(str(to_date), 0)
        # without the sleep, probably the filters (on state) are no updated yet
        # this way I give the loop a chance to run the effects of inputs and then
        # I request for updating the reports.
        # This doesn't guarantee anything but solves the bug good enought for now.
        await asyncio.sleep(0.01)
        request_for_update_reports(self.app)

    async def action_reset_date_filters(self) -> None:
        today = date.today()
        await self._set_date_filters(today - timedelta(days=30), today)

    async def action_filter_current_week(self) -> None:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        await self._set_date_filters(start_of_week, end_of_week)

    async def action_filter_current_month(self) -> None:
        today = date.today()
        start_of_month = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_of_month = next_month.replace(day=1) - timedelta(days=1)
        await self._set_date_filters(start_of_month, end_of_month)

    async def action_filter_previous_week(self) -> None:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday() + 7)
        end_of_week = start_of_week + timedelta(days=6)
        await self._set_date_filters(start_of_week, end_of_week)

    async def action_filter_previous_month(self) -> None:
        today = date.today()
        first_of_this_month = today.replace(day=1)
        last_of_previous_month = first_of_this_month - timedelta(days=1)
        start_of_previous_month = last_of_previous_month.replace(day=1)
        await self._set_date_filters(start_of_previous_month, last_of_previous_month)

    def action_show_balancesheet(self) -> None:
        state = get_app_state(self.app)
        state.requested_report = ReportType.BALANCE_SHEET
        request_for_update_reports(self.app)

    def action_show_incomestatement(self) -> None:
        state = get_app_state(self.app)
        state.requested_report = ReportType.INCOME_STATEMENT
        request_for_update_reports(self.app)

    def action_show_cashflow(self) -> None:
        state = get_app_state(self.app)
        state.requested_report = ReportType.CASH_FLOW
        request_for_update_reports(self.app)
