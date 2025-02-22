from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

type AccountPath = str
type AccountLabel = str
type Currency = str


@dataclass
class LedgerPosting:
    account: AccountPath
    amount: float
    currency: Currency
    comment: str


@dataclass
class LedgerTransaction:
    id: str
    date: date
    description: str
    postings: list[LedgerPosting]
    tags: dict[str, str]


@dataclass
class LedgerSnapshot:
    balances: dict[AccountPath, dict[Currency, float]]
    transactions: list[LedgerTransaction]
    commodities: set[Currency]
    stats: str | None = None


class InsightsFilters(TypedDict):
    from_date: date | None
    to_date: date | None
    account: AccountPath | None
    currency: Currency | None
    depth: int | None
    etc_threshold: int | None


@dataclass
class AppState:
    ledger_data: LedgerSnapshot
    accounts_tree_filters: list[Callable[[AccountPath], bool]]
    transactions_list_filters: dict[str, Callable[[LedgerTransaction], bool]]
    account_labels: dict[AccountPath, AccountLabel]
    currency_labels: dict[Currency, str]
    pinned_accounts: list[tuple[AccountPath, str]]
    errors: list[Exception]
    # insights filters is not like other filters because the filtering doesn't happen
    # in this process, we pass it directly to hledger
    insights_filters: InsightsFilters
    last_insights_request_time: float = 0


class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    class _PinnedAccount(BaseModel):
        account: str
        color: str

    ledger: str | None = None
    account_labels: dict[str, str] = Field(default_factory=dict)
    currency_labels: dict[str, str] = Field(default_factory=dict)
    pinned_accounts: list[_PinnedAccount] = Field(default_factory=list)
