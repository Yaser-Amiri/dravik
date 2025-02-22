from datetime import date, datetime, timedelta
from abc import abstractmethod
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import Key, Resize
from textual.screen import Screen
from textual.containers import (
    Grid,
    Vertical,
    VerticalScroll,
)
from textual.widgets import Button, Footer, Static, Input, Label, MaskedInput

from dravik.models import AccountPath, AppState, InsightsFilters
from dravik.utils import get_app_services, get_app_state, mutate_app_state
from dravik.validators import Date, Integer

from textual_plotext import PlotextPlot

from dravik.widgets import AccountPathInput


def request_for_update_charts(app: App[object]) -> None:
    state = get_app_state(app)
    state.last_insights_request_time = datetime.now().timestamp()
    mutate_app_state(app)


class InsightsSubmitButton(Button):
    def on_button_pressed(self) -> None:
        request_for_update_charts(self.app)


class InsightsAccountInput(AccountPathInput):
    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)
        word = e.value.strip()
        state.insights_filters["account"] = word or None
        mutate_app_state(self.app)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)


class InsightsCurrencyInput(Input):
    def on_input_changed(self, e: Input.Changed) -> None:
        state = get_app_state(self.app)
        word = e.value.strip()
        state.insights_filters["currency"] = word or None
        mutate_app_state(self.app)

    async def action_submit(self) -> None:
        request_for_update_charts(self.app)


class InsightsDepthInput(MaskedInput):
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

        state.insights_filters["depth"] = filter_value
        mutate_app_state(self.app)


class InsightsEtcThresholdInput(MaskedInput):
    def __init__(self, **kwargs: Any) -> None:
        template = kwargs.pop("template", "9")
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

        state.insights_filters["etc_threshold"] = filter_value
        mutate_app_state(self.app)


class InsightsFromDateInput(MaskedInput):
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

        state.insights_filters["from_date"] = filter_value
        mutate_app_state(self.app)


class InsightsToDateInput(MaskedInput):
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

        state.insights_filters["to_date"] = filter_value
        mutate_app_state(self.app)


class Plot(PlotextPlot):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_insights_request_time: float = -1

    def on_mount(self) -> None:
        def _x(s: AppState) -> None:
            if self.last_insights_request_time == s.last_insights_request_time:
                return
            self.last_insights_request_time = s.last_insights_request_time
            self.set_data(s.insights_filters)
            self.refresh(layout=True)

        self.watch(self.app, "state", _x)

    @abstractmethod
    def set_data(self, filters: InsightsFilters) -> None:
        pass


class HistoricalBalance(Plot):
    def set_data(self, filters: InsightsFilters) -> None:
        account = filters["account"] or "assets"

        hledger = get_app_services(self.app).get_hledger()
        hledger_result = hledger.get_historical_balance_report(
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
            values.append(v.get(currency, 0.0))

        plt.plot(dates, values)
        plt.title(
            f"Historical Balance / Account: {account} / "
            f"Currency: {currency or 'Not Selected'}"
        )


class InsightsScreen(Screen[None]):
    CSS_PATH = "../styles/insights.tcss"

    BINDINGS = [
        Binding("s", "focus_on_filters", "Focus On Filters"),
        Binding("escape", "focus_on_submit", "Focus On Submit"),
        Binding("0", "reset_date_filters", "Reset Date Filters", show=False),
        Binding("1", "filter_current_week", "Filter Current Week", show=False),
        Binding("2", "filter_current_month", "Filter Current Month", show=False),
        Binding("3", "filter_previous_week", "Filter Previous Week", show=False),
        Binding("4", "filter_previous_month", "Filter Previous Month", show=False),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.from_date_input: InsightsFromDateInput | None
        self.to_date_input: InsightsToDateInput | None
        self.account_input: InsightsAccountInput | None
        self.depth_input: InsightsDepthInput | None
        self.currency_input: InsightsCurrencyInput | None
        self.etc_threshold: InsightsEtcThresholdInput | None
        super().__init__(*args, **kwargs)

    def ns(self, name: str) -> str:
        return f"insights--{name}"

    def compose(self) -> ComposeResult:
        today = datetime.now()
        self.account_input = InsightsAccountInput(
            placeholder="Path",
            value="assets",
            id=self.ns("account-filter"),
        )
        self.from_date_input = InsightsFromDateInput(
            placeholder="1970-01-01",
            value=(today - timedelta(days=30)).strftime("%Y-%m-%d"),
        )
        self.to_date_input = InsightsToDateInput(
            placeholder="2040-12-31",
            value=today.strftime("%Y-%m-%d"),
        )
        self.depth_input = InsightsDepthInput(placeholder="1", value="1")
        self.currency_input = InsightsCurrencyInput(placeholder="EUR")
        self.etc_threshold = InsightsEtcThresholdInput(placeholder="5", value="5")

        with VerticalScroll():
            with Vertical(id=self.ns("container")):
                with Grid(id=self.ns("searchbar-labels")):
                    yield Label("Account:")
                    yield Label("Currency:")
                    yield Label("From Date:")
                    yield Label("To Date:")
                    yield Label("Depth:")
                    yield Label("Etc Threshold:")
                    yield Label("")

                with Grid(id=self.ns("searchbar-inputs")):
                    yield self.account_input
                    yield self.currency_input
                    yield self.from_date_input
                    yield self.to_date_input
                    yield self.depth_input
                    yield self.etc_threshold
                    yield InsightsSubmitButton(
                        "Submit Filters",
                        variant="primary",
                        id=self.ns("submit"),
                    )
                yield HistoricalBalance(id=self.ns("historical-balance-plot"))
        yield Footer()

    def action_focus_on_filters(self) -> None:
        self.query_one(f"#{self.ns('account-filter')}").focus()

    def action_focus_on_submit(self) -> None:
        self.query_one(f"#{self.ns('submit')}").focus()

    def on_mount(self) -> None:
        self.query_one(f"#{self.ns('submit')}").focus()

    def _set_date_filters(self, from_date: date, to_date: date) -> None:
        if self.from_date_input is None or self.to_date_input is None:
            return

        self.from_date_input.clear()
        self.to_date_input.clear()
        self.from_date_input.insert(str(from_date), 0)
        self.to_date_input.insert(str(to_date), 0)

    def action_reset_date_filters(self) -> None:
        today = date.today()
        self._set_date_filters(today - timedelta(days=30), today)

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
