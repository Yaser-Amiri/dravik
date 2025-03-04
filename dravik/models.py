from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

type AccountPath = str
type AccountLabel = str
type Currency = str
type Amount = Decimal


@dataclass
class LedgerPosting:
    account: AccountPath
    amount: Amount
    currency: Currency
    comment: str


class TransactionStatus(StrEnum):
    UNMARKED = "UNMARKED"
    PENDING = "PENDING"
    CLEARED = "CLEARED"


@dataclass
class LedgerTransaction:
    id: str
    secondary_date: date | None
    status: TransactionStatus
    date: date
    description: str
    postings: list[LedgerPosting]
    tags: dict[str, str]


@dataclass
class LedgerSnapshot:
    balances: dict[AccountPath, dict[Currency, Amount]]
    transactions: list[LedgerTransaction]
    commodities: set[Currency]
    stats: str | None = None


class ReportType(StrEnum):
    BALANCE_SHEET = "BALANCE_SHEET"
    CASH_FLOW = "CASH_FLOW"
    INCOME_STATEMENT = "INCOME_STATEMENT"


@dataclass
class ReportSectionResult:
    title: str
    per_account: dict[AccountPath, dict[Currency, Amount]]
    total: dict[Currency, Amount]


@dataclass
class ReportResult:
    title: str
    sections: list[ReportSectionResult]
    total: dict[Currency, Amount]


class ChartsFilters(TypedDict):
    from_date: date | None
    to_date: date | None
    account: AccountPath | None
    currency: Currency | None
    depth: int | None
    etc_threshold: int | None


class ReportsFilters(TypedDict):
    from_date: date | None
    to_date: date | None


@dataclass
class AppState:
    ledger_data: LedgerSnapshot
    accounts_tree_filters: list[Callable[[AccountPath], bool]]
    transactions_list_filters: dict[str, Callable[[LedgerTransaction], bool]]
    account_labels: dict[AccountPath, AccountLabel]
    currency_labels: dict[Currency, str]
    pinned_accounts: list[tuple[AccountPath, str]]
    errors: list[Exception]
    # charts filters is not like other filters because the filtering doesn't
    # happen in this process, we pass it directly to hledger
    charts_filters: ChartsFilters
    reports_filters: ReportsFilters
    last_charts_request_time: float = 0
    last_reports_request_time: float = 0
    requested_report: ReportType = ReportType.BALANCE_SHEET
    show_total_row_in_transactions_table: bool = False


class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    class _PinnedAccount(BaseModel):
        account: str
        color: str

    ledger: str | None = None
    account_labels: dict[str, str] = Field(default_factory=dict)
    currency_labels: dict[str, str] = Field(default_factory=dict)
    pinned_accounts: list[_PinnedAccount] = Field(default_factory=list)
