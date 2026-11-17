import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import click
from ape.api.scripts import ScriptRunnerAPI
from ape.cli.commands import ConnectedProviderCommand
from ape.cli.options import account_option

from ape_foundry.exceptions import (
    ForgeNotInstalledError,
    ForgeScriptError,
    FoundryProviderError,
    UnsupportedForgeSignerError,
)

if TYPE_CHECKING:
    from ape.api.accounts import AccountAPI
    from ape.api.providers import ProviderAPI

FOUNDRY_SCRIPTS_FOLDER_NAME = "script"


class ForgeScriptRunner(ScriptRunnerAPI):
    """
    Runs Foundry scripts (``.s.sol``) through ``forge script`` with Ape's network and account.
    """

    @property
    def scripts_folder_name(self) -> str:
        return FOUNDRY_SCRIPTS_FOLDER_NAME

    def get_command(self, script_path: Path, name: str) -> click.Command:
        @click.command(
            cls=ConnectedProviderCommand,
            name=name,
            short_help=f"Run '{script_path.name}' with forge",
            context_settings={"ignore_unknown_options": True},
        )
        @account_option()
        @click.option("--broadcast", is_flag=True, help="Send the script's transactions")
        @click.argument("forge_args", nargs=-1, type=click.UNPROCESSED)
        def run(account, broadcast, forge_args, provider):
            run_forge_script(
                script_path, provider, account, broadcast=broadcast, forge_args=forge_args
            )

        return run


def run_forge_script(
    script_path: Path,
    provider: "ProviderAPI",
    account: "AccountAPI",
    *,
    broadcast: bool,
    forge_args: tuple[str, ...] = (),
):
    """
    Run ``script_path`` with ``forge script`` against ``provider``, signing as ``account``.
    """
    command = build_forge_script_command(
        script_path,
        get_rpc_url(provider),
        build_signing_args(account),
        broadcast=broadcast,
        forge_args=forge_args,
    )
    result = subprocess.run(command)
    if result.returncode != 0:
        raise ForgeScriptError(result.returncode)


def build_forge_script_command(
    script_path: Path,
    rpc_url: str,
    signing_args: list[str],
    *,
    broadcast: bool,
    forge_args: tuple[str, ...] = (),
) -> list[str]:
    """
    The ``forge script`` argv for ``script_path``.
    """
    broadcast_args = ["--broadcast"] if broadcast else []
    return [
        find_forge(),
        "script",
        str(script_path),
        "--rpc-url",
        rpc_url,
        *signing_args,
        *broadcast_args,
        *forge_args,
    ]


def build_signing_args(account: "AccountAPI") -> list[str]:
    """
    The ``forge`` arguments that sign as ``account``.
    """
    from ape.api.accounts import ImpersonatedAccount
    from ape_accounts.accounts import KeyfileAccount
    from ape_test.accounts import TestAccount

    if isinstance(account, TestAccount):
        return ["--private-key", account.private_key]

    elif isinstance(account, KeyfileAccount):
        return ["--keystore", str(account.keyfile_path), "--sender", str(account.address)]

    elif isinstance(account, ImpersonatedAccount):
        return ["--unlocked", "--sender", str(account.address)]

    raise UnsupportedForgeSignerError(account)


def get_rpc_url(provider: "ProviderAPI") -> str:
    """
    The HTTP RPC URL ``forge`` reaches ``provider`` at.
    """
    if not provider.http_uri:
        raise FoundryProviderError(f"Provider '{provider.name}' has no HTTP RPC URL.")

    return provider.http_uri


def find_forge() -> str:
    """
    The path to the ``forge`` executable.
    """
    if forge := shutil.which("forge"):
        return forge

    raise ForgeNotInstalledError()
