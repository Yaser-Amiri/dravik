import subprocess
from uuid import uuid4
from datetime import datetime, date, timedelta
import json

from dravik.models import (
    AccountPath,
    Currency,
    LedgerSnapshot,
    LedgerPosting,
    LedgerTransaction,
)


def run_cmd(cmd: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class Hledger:
    def __init__(self, ledger_file_path: str | None = None) -> None:
        self.ledger_file_path = ledger_file_path

    def get_transaction_command(self) -> list[str]:
        file_params = ["-f", self.ledger_file_path] if self.ledger_file_path else []
        return [
            "hledger",
            *file_params,
            "print",
            "-O",
            "json",
        ]

    def get_balances_command(self) -> list[str]:
        file_params = ["-f", self.ledger_file_path] if self.ledger_file_path else []
        return [
            "hledger",
            *file_params,
            "bal",
            "-t",
            "--no-elide",
            "-O",
            "json",
        ]

    def get_stats_command(self) -> list[str]:
        file_params = ["-f", self.ledger_file_path] if self.ledger_file_path else []
        return [
            "hledger",
            *file_params,
            "stats",
        ]

    def get_version_command(self) -> list[str]:
        return [
            "hledger",
            "--version",
        ]

    def get_check_command(self, strict: bool = False) -> list[str]:
        file_params = ["-f", self.ledger_file_path] if self.ledger_file_path else []
        strict_params = ["--strict"] if strict else []
        return [
            "hledger",
            *file_params,
            "check",
            *strict_params,
        ]

    def get_historical_balance_command(
        self, account: AccountPath, from_date: date, to_date: date
    ) -> list[str]:
        file_params = ["-f", self.ledger_file_path] if self.ledger_file_path else []
        return [
            "hledger",
            *file_params,
            "bal",
            account,
            "--historical",
            "--daily",
            "--begin",
            from_date.strftime("%Y-%m-%d"),
            "--end",
            to_date.strftime("%Y-%m-%d"),
            "-O",
            "json",
        ]

    def get_balance_change_report_command(
        self, account: AccountPath, from_date: date, to_date: date, depth: int = 2
    ) -> list[str]:
        file_params = ["-f", self.ledger_file_path] if self.ledger_file_path else []
        return [
            "hledger",
            *file_params,
            "bal",
            "-E",
            account,
            "--begin",
            from_date.strftime("%Y-%m-%d"),
            "--end",
            to_date.strftime("%Y-%m-%d"),
            "--depth",
            str(depth),
            "-O",
            "json",
        ]

    def read(self) -> LedgerSnapshot:
        transaction_proc = run_cmd(self.get_transaction_command())
        balances_proc = run_cmd(self.get_balances_command())
        stats_proc = run_cmd(self.get_stats_command())
        transaction_result = transaction_proc.communicate()
        balances_result = balances_proc.communicate()
        stats_result = stats_proc.communicate()
        if transaction_proc.returncode != 0:
            raise Exception(transaction_result[1].decode())
        if balances_proc.returncode != 0:
            raise Exception(balances_result[1].decode())
        if stats_proc.returncode != 0:
            raise Exception(stats_result[1].decode())

        commodities = {
            bl["acommodity"] for bl in json.loads(balances_result[0].decode())[1]
        }
        balances = {
            bl[0]: {r["acommodity"]: r["aquantity"]["floatingPoint"] for r in bl[3]}
            for bl in json.loads(balances_result[0].decode())[0]
        }
        transactions: list[LedgerTransaction] = [
            LedgerTransaction(
                description=tx["tdescription"],
                date=datetime.strptime(tx["tdate"], "%Y-%m-%d").date(),
                id=str(uuid4()),
                tags={str(k): str(v) for k, v in tx["ttags"]},
                postings=[
                    LedgerPosting(
                        account=posting["paccount"],
                        amount=posting["pamount"][0]["aquantity"]["floatingPoint"],
                        currency=posting["pamount"][0]["acommodity"],
                        comment=posting["pcomment"].strip(),
                    )
                    for posting in tx["tpostings"]
                ],
            )
            for tx in json.loads(transaction_result[0].decode())
        ]
        return LedgerSnapshot(
            balances=balances,
            commodities=commodities,
            transactions=transactions,
            stats=stats_result[0].decode(),
        )

    def get_historical_balance_report(
        self, account: AccountPath, from_date: date, to_date: date
    ) -> dict[date, dict[Currency, float]]:
        proc = run_cmd(
            self.get_historical_balance_command(
                account, from_date, to_date + timedelta(days=1)
            )
        )
        cmd_result = proc.communicate()
        if proc.returncode != 0:
            raise Exception(cmd_result[1].decode())
        parsed_stdout = json.loads(cmd_result[0].decode())
        dates = [
            datetime.strptime(x[0]["contents"], "%Y-%m-%d").date()
            for x in parsed_stdout["prDates"]
        ]

        result: dict[date, dict[Currency, float]] = {}
        for index, holdings in enumerate(parsed_stdout["prTotals"]["prrAmounts"]):
            result[dates[index]] = dict(
                [(y["acommodity"], y["aquantity"]["floatingPoint"]) for y in holdings]
            )
        return result

    def get_balance_change_report(
        self, account: AccountPath, from_date: date, to_date: date, depth: int = 2
    ) -> tuple[dict[AccountPath, dict[Currency, float]], dict[Currency, float]]:
        """
        Returns a tuple, first member is per account balances and second is total
        """
        proc = run_cmd(
            self.get_balance_change_report_command(
                account, from_date, to_date + timedelta(days=1), depth
            )
        )
        result = proc.communicate()
        if proc.returncode != 0:
            raise Exception(result[1].decode())
        parsed_stdout = json.loads(result[0].decode())

        per_account = {
            bl[0]: {r["acommodity"]: r["aquantity"]["floatingPoint"] for r in bl[3]}
            for bl in parsed_stdout[0]
        }
        total = {
            r["acommodity"]: r["aquantity"]["floatingPoint"] for r in parsed_stdout[1]
        }
        return per_account, total

    def get_version(self) -> str:
        proc = run_cmd(self.get_version_command())
        result = proc.communicate()
        if proc.returncode != 0:
            raise Exception(result[1].decode())
        return result[0].decode()

    def check(self, strict: bool = False) -> str:
        proc = run_cmd(self.get_check_command(strict))
        result = proc.communicate()
        if proc.returncode != 0:
            raise Exception(result[1].decode())
        return result[0].decode()
