from uuid import uuid4
from datetime import datetime
import json
import asyncio
from asyncio.subprocess import Process

from dravik.models import (
    LedgerSnapshot,
    LedgerPosting,
    LedgerTransaction,
)


async def run_cmd(cmd: list[str]) -> Process:
    return await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
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

    async def read(self) -> LedgerSnapshot:
        transaction_proc = await run_cmd(self.get_transaction_command())
        balances_proc = await run_cmd(self.get_balances_command())
        stats_proc = await run_cmd(self.get_stats_command())
        transaction_result, balances_result, stats_result = await asyncio.gather(
            transaction_proc.communicate(),
            balances_proc.communicate(),
            stats_proc.communicate(),
        )
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

    async def get_version(self) -> str:
        proc = await run_cmd(self.get_version_command())
        result = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(result[1].decode())
        return result[0].decode()

    async def check(self, strict: bool = False) -> str:
        proc = await run_cmd(self.get_check_command(strict))
        result = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(result[1].decode())
        return result[0].decode()
