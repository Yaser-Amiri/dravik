import asyncio
from abc import abstractmethod
from datetime import date, datetime, timedelta
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
    Grid,
)
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, MaskedInput, Static
from textual_plotext import PlotextPlot

from dravik.models import AppState, ChartsFilters
from dravik.utils import get_app_services, get_app_state, mutate_app_state
from dravik.validators import Date, Integer
from dravik.widgets import AccountPathInput, RichVerticalScroll


def request_for_update_charts(app: App[object]) -> None:
    state = get_app_state(app)
    state.last_charts_request_time = datetime.now().timestamp()
    mutate_app_state(app)


class ChartsSubmitButton(Button):
    def on_button_pressed(self) -> None:
        request_for_update_charts(self.app)


class ChartsAccountInput(AccountPathInput):
    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)
        word = e.value.strip()
        state.charts_filters["account"] = word or None
        mutate_app_state(self.app)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)


class ChartsCurrencyInput(Input):
    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)
        word = e.value.strip()
        state.charts_filters["currency"] = word or None
        mutate_app_state(self.app)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)


class ChartsDepthInput(MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "0")
        validators = kwargs.pop("validators", []) + [Integer()]
        super().__init__(template=template, validators=validators, **kwargs)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)

    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)

        try:
            word = e.value.strip()
            filter_value = int(word) if word else 1
        except (TypeError, ValueError):
            filter_value = None

        state.charts_filters["depth"] = filter_value
        mutate_app_state(self.app)


class ChartsEtcThresholdInput(MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "00")
        validators = kwargs.pop("validators", []) + [Integer()]
        super().__init__(template=template, validators=validators, **kwargs)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)

    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)

        try:
            word = e.value.strip()
            filter_value = int(word) if word else None
        except (TypeError, ValueError):
            filter_value = None

        state.charts_filters["etc_threshold"] = filter_value
        mutate_app_state(self.app)


class ChartsFromDateInput(MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "9999-99-99")
        validators = kwargs.pop("validators", []) + [Date()]
        super().__init__(template=template, validators=validators, **kwargs)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)

    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)

        try:
            filter_value = date(*[int(p) for p in e.value.strip().split("-") if p])
        except (TypeError, ValueError):
            filter_value = None

        state.charts_filters["from_date"] = filter_value
        mutate_app_state(self.app)


class ChartsToDateInput(MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "9999-99-99")
        validators = kwargs.pop("validators", []) + [Date()]
        super().__init__(template=template, validators=validators, **kwargs)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)

    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)

        try:
            filter_value = date(*[int(p) for p in e.value.strip().split("-") if p])
        except (TypeError, ValueError):
            filter_value = None

        state.charts_filters["to_date"] = filter_value
        mutate_app_state(self.app)


class Plot(PlotextPlot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_charts_request_time: float = -1

    def on_mount(self) -> None:
        def _x(s: AppState) -> None:
            if self.last_charts_request_time == s.last_charts_request_time:
                return
            self.last_charts_request_time = s.last_charts_request_time
            self.set_data(s.charts_filters)
            self.refresh(layout=True)

        self.watch(self.app, "state", _x)

    @abstractmethod
    def set_data(self, filters: ChartsFilters) -> None:
        pass


class HistoricalBalance(Plot):
    def set_data(self, filters: ChartsFilters) -> None:
        account = filters["account"] or "expenses"

        hledger = get_app_services(self.app).get_hledger()
        hledger_result = hledger.get_historical_balance(
            account,
            filters["from_date"] or datetime.now().date() - timedelta(days=30),
            filters["to_date"] or datetime.now().date(),
        )

        plt = self.plt
        plt.clear_data()
        plt.clear_color()
        plt.clear_terminal()
        plt.clear_figure()
        plt.theme("matrix")
        plt.date_form("Y-m-d")

        available_currencies = {c for r in hledger_result.values() for c in r}
        inferred_currency = (
            list(available_currencies)[0] if len(available_currencies) > 0 else ""
        )
        currency = filters["currency"] or inferred_currency

        dates = []
        values = []
        for d, v in hledger_result.items():
            dates.append(datetime.fromordinal(d.toordinal()).strftime("%Y-%m-%d"))
            values.append(
                float(v.get(currency, 0))
            )  # the chart lib doesn't accept decimal, just float

        plt.plot(dates, values)
        plt.title(
            f"Historical Balance / Account: {account} / "
            f"Currency: {currency or 'Not Selected'}"
        )


class BalanceChange(Plot):
    def set_data(self, filters: ChartsFilters) -> None:
        account = filters["account"] or "expenses"
        depth = filters["depth"] or 2
        etc_threshold = filters["etc_threshold"] or 0
        account_labels = get_app_state(self.app).account_labels

        hledger = get_app_services(self.app).get_hledger()
        hledger_result_per_account, hledger_result_total = hledger.get_balance_change(
            account,
            filters["from_date"] or datetime.now().date() - timedelta(days=30),
            filters["to_date"] or datetime.now().date(),
            depth,
        )

        plt = self.plt
        plt.clear_data()
        plt.clear_color()
        plt.clear_terminal()
        plt.clear_figure()
        plt.theme("matrix")
        plt.date_form("Y-m-d")

        available_currencies = {
            c for r in hledger_result_per_account.values() for c in r
        }
        inferred_currency = (
            list(available_currencies)[0] if len(available_currencies) > 0 else ""
        )
        currency = filters["currency"] or inferred_currency

        total_amount = hledger_result_total.get(currency, 0)
        under_threshold_amount: float = 0

        accounts = []
        values = []
        for a, holdings in hledger_result_per_account.items():
            value = holdings.get(currency)
            if value is None:
                continue
            if value / total_amount * 100 <= etc_threshold:
                under_threshold_amount += float(value)
            else:
                accounts.append(account_labels.get(a, a))
                values.append(
                    float(value)
                )  # the chart lib doesn't accept decimal, just float

        if under_threshold_amount > 0:
            accounts.append("Sum of Under Threshold")
            values.append(under_threshold_amount)

        plt.bar(accounts, values, orientation="horizontal")
        plt.title(
            f"Historical Balance / Account: {account} / "
            f"Currency: {currency or 'Not Selected'} / "
            f"Total: {total_amount}"
        )


class ChartsScreen(Screen[None]):
    CSS_PATH = "../styles/charts.tcss"

    BINDINGS = [
        Binding("s", "focus_on_filters", "Focus On Filters"),
        Binding("escape", "unfocus", "Unfocus"),
        Binding("0", "reset_date_filters", "Reset Date Filters", show=False),
        Binding("1", "filter_current_week", "Filter Current Week", show=False),
        Binding("2", "filter_current_month", "Filter Current Month", show=False),
        Binding("3", "filter_previous_week", "Filter Previous Week", show=False),
        Binding("4", "filter_previous_month", "Filter Previous Month", show=False),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.from_date_input: ChartsFromDateInput | None
        self.to_date_input: ChartsToDateInput | None
        self.account_input: ChartsAccountInput | None
        self.depth_input: ChartsDepthInput | None
        self.currency_input: ChartsCurrencyInput | None
        self.etc_threshold: ChartsEtcThresholdInput | None
        super().__init__(*args, **kwargs)

    def ns(self, name: str) -> str:
        return f"charts--{name}"

    def compose(self) -> ComposeResult:
        today = datetime.now()
        self.account_input = ChartsAccountInput(
            placeholder="Path",
            value="expenses",
            id=self.ns("account-filter"),
        )
        self.from_date_input = ChartsFromDateInput(
            placeholder="1970-01-01",
            value=(today - timedelta(days=30)).strftime("%Y-%m-%d"),
        )
        self.to_date_input = ChartsToDateInput(
            placeholder="2040-12-31",
            value=today.strftime("%Y-%m-%d"),
        )
        self.depth_input = ChartsDepthInput(placeholder="3", value="3")
        self.currency_input = ChartsCurrencyInput(placeholder="EUR")
        self.etc_threshold = ChartsEtcThresholdInput(placeholder="1", value="1")

        yield Static("Dravik / Charts", id=self.ns("header"))
        with RichVerticalScroll(id=self.ns("container")):
            with Grid(id=self.ns("searchbar-labels")):
                yield Label("Account:")
                yield Label("Currency:")
                yield Label("From Date:")
                yield Label("To Date:")
                yield Label("Depth:")
                yield Label("Etc Threshold %:")
                yield Label("")

            with Grid(id=self.ns("searchbar-inputs")):
                yield self.account_input
                yield self.currency_input
                yield self.from_date_input
                yield self.to_date_input
                yield self.depth_input
                yield self.etc_threshold
                yield ChartsSubmitButton(
                    "Submit Filters",
                    variant="primary",
                    id=self.ns("submit"),
                )
            yield HistoricalBalance(id=self.ns("historical-balance-plot"))
            yield BalanceChange(id=self.ns("balance-change-plot"))
        yield Footer()

    def action_focus_on_filters(self) -> None:
        self.query_one(f"#{self.ns('account-filter')}").focus()

    def action_unfocus(self) -> None:
        self.query_one(f"#{self.ns('container')}").focus()

    def on_mount(self) -> None:
        self.query_one(f"#{self.ns('submit')}").focus()

    async def _set_date_filters(self, from_date: date, to_date: date) -> None:
        if self.from_date_input is None or self.to_date_input is None:
            return

        self.from_date_input.insert(str(from_date), 0)
        self.to_date_input.insert(str(to_date), 0)
        # without the sleep, probably the filters (on state) are no updated yet
        # this way I give the loop a chance to run the effects of inputs and then
        # I request for updating the charts.
        # This doesn't guarantee anything but solves the bug good enought for now.
        await asyncio.sleep(0.01)
        request_for_update_charts(self.app)

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
