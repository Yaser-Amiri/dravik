from pathlib import Path
import json
from typing import Protocol


from dravik.hledger import Hledger
from dravik.models import AppState, Config, LedgerSnapshot


class AppProto(Protocol):
    config_path: Path
    config_dir: Path


class AppServices:
    def __init__(self, app: AppProto) -> None:
        self.app = app

    async def get_initial_state(self) -> AppState:
        configs = await self.read_configs()
        return AppState(
            accounts_tree_filters=[],
            transactions_list_filters={},
            ledger_data=await self.read_hledger_data(configs.ledger),
            account_labels=configs.account_labels,
            currency_labels=configs.currency_labels,
            pinned_accounts=[(a.account, a.color) for a in configs.pinned_accounts],
            errors=[],
        )

    async def read_hledger_data(self, path: str | None = None) -> LedgerSnapshot:
        p = (await self.read_configs()).ledger if not path else path
        return await Hledger(p).read()

    async def read_configs(self) -> Config:
        with open(self.app.config_path) as config_file:
            return Config(**json.load(config_file))

    async def create_configs(self) -> None:
        self.app.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.app.config_path.exists():
            with open(self.app.config_path, "w") as f:
                f.write(Config().model_dump_json(indent=4))

    async def initial_check(self) -> None:
        configs = await self.read_configs()
        hledger = Hledger(configs.ledger)
        await hledger.get_version()
        await hledger.check()
