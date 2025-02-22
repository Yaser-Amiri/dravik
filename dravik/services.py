import json
from datetime import date
from pathlib import Path
from typing import Protocol

from dravik.hledger import Hledger
from dravik.models import AppState, Config, LedgerSnapshot


class AppProto(Protocol):
    config_path: Path
    config_dir: Path


class AppServices:
    def __init__(self, app: AppProto) -> None:
        self.app = app

    def get_hledger(self, path: str | None = None) -> Hledger:
        p = path if path else self.read_configs().ledger
        return Hledger(p)

    def get_initial_state(self) -> AppState:
        configs = self.read_configs()
        return AppState(
            accounts_tree_filters=[],
            transactions_list_filters={},
            ledger_data=self.read_hledger_data(configs.ledger),
            account_labels=configs.account_labels,
            currency_labels=configs.currency_labels,
            pinned_accounts=[(a.account, a.color) for a in configs.pinned_accounts],
            errors=[],
            insights_filters={
                "from_date": None,
                "to_date": None,
                "account": None,
                "depth": None,
                "etc_threshold": None,
                "currency": None,
            },
        )

    def read_hledger_data(self, path: str | None = None) -> LedgerSnapshot:
        hledger = self.get_hledger(path)
        return hledger.read()

    def read_configs(self) -> Config:
        with self.app.config_path.open("r") as config_file:
            return Config(**json.load(config_file))

    def create_configs(self) -> None:
        self.app.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.app.config_path.exists():
            with self.app.config_path.open("w") as f:
                f.write(Config().model_dump_json(indent=4))
                print(f"Wrote the config file on: {self.app.config_path}")  # noqa: T201

    def initial_check(self) -> None:
        configs = self.read_configs()
        hledger = Hledger(configs.ledger)
        hledger.get_version()
        hledger.check()
        hledger.get_balance_change_report(
            "expenses", date(2025, 2, 1), date(2025, 2, 20)
        )
