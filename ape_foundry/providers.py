import random
import shutil
from pathlib import Path
from subprocess import PIPE, call
from typing import Any, Dict, List, Optional, Union, cast

from ape._compat import Literal
from ape.api import (
    PluginConfig,
    ProviderAPI,
    ReceiptAPI,
    SubprocessProvider,
    TestProviderAPI,
    TransactionAPI,
    UpstreamProvider,
    Web3Provider,
)
from ape.exceptions import (
    ContractLogicError,
    OutOfGasError,
    ProviderError,
    SubprocessError,
    TransactionError,
    VirtualMachineError,
)
from ape.logging import logger
from ape.types import AddressType, SnapshotID
from ape.utils import cached_property, gas_estimation_error_message
from ape_test import Config as TestConfig
from web3 import HTTPProvider, Web3
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.middleware import geth_poa_middleware

from .exceptions import FoundryNotInstalledError, FoundryProviderError, FoundrySubprocessError

EPHEMERAL_PORTS_START = 49152
EPHEMERAL_PORTS_END = 60999
FOUNDRY_START_NETWORK_RETRIES = [0.1, 0.2, 0.3, 0.5, 1.0]  # seconds between network retries
FOUNDRY_START_PROCESS_ATTEMPTS = 3  # number of attempts to start subprocess before giving up
DEFAULT_PORT = 8545
FOUNDRY_CHAIN_ID = 31337


class FoundryForkConfig(PluginConfig):
    upstream_provider: Optional[str] = None
    block_number: Optional[int] = None


class FoundryNetworkConfig(PluginConfig):
    port: Optional[Union[int, Literal["auto"]]] = DEFAULT_PORT

    # Retry strategy configs, try increasing these if you're getting FoundrySubprocessError
    network_retries: List[float] = FOUNDRY_START_NETWORK_RETRIES
    process_attempts: int = FOUNDRY_START_PROCESS_ATTEMPTS

    # For setting the values in --fork and --fork-block-number command arguments.
    # Used only in FoundryMainnetForkProvider.
    # Mapping of ecosystem_name => network_name => FoundryForkConfig
    fork: Dict[str, Dict[str, FoundryForkConfig]] = {}

    class Config:
        extra = "allow"


def _call(*args):
    return call([*args], stderr=PIPE, stdout=PIPE, stdin=PIPE)


class FoundryProvider(SubprocessProvider, Web3Provider, TestProviderAPI):
    port: Optional[int] = None
    attempted_ports: List[int] = []
    unlocked_accounts: List[AddressType] = []

    @property
    def mnemonic(self) -> str:
        return self._test_config.mnemonic

    @property
    def number_of_accounts(self) -> int:
        return self._test_config.number_of_accounts

    @property
    def process_name(self) -> str:
        return "anvil"

    @property
    def chain_id(self) -> int:
        if hasattr(self._web3, "eth"):
            return self._web3.eth.chain_id  # type: ignore
        else:
            return FOUNDRY_CHAIN_ID

    @cached_property
    def anvil_bin(self) -> str:
        anvil = shutil.which("anvil")

        if not anvil:
            raise FoundryNotInstalledError()
        elif _call(anvil, "--version") != 0:
            raise FoundrySubprocessError(
                "Anvil executable returned error code. See ape-foundry README for install steps."
            )

        return anvil

    @property
    def project_folder(self) -> Path:
        return self.config_manager.PROJECT_FOLDER

    @property
    def uri(self) -> str:
        if not self.port:
            raise FoundryProviderError("Can't build URI before `connect()` is called.")

        return f"http://127.0.0.1:{self.port}"

    @property
    def priority_fee(self) -> int:
        """
        Priority fee not needed in development network.
        """
        return 0

    @property
    def is_connected(self) -> bool:
        self._set_web3()
        return self._web3 is not None

    @cached_property
    def _test_config(self) -> TestConfig:
        return cast(TestConfig, self.config_manager.get_config("test"))

    def connect(self):
        """
        Start the foundry process and verify it's up and accepting connections.
        **NOTE**: Must set port before calling 'super().connect()'.
        """

        if not self.port:
            self.port = self.config.port  # type: ignore

        if self.is_connected:
            # Connects to already running process
            self._start()
        else:
            # Only do base-process setup if not connecting to already-running process
            super().connect()

            if self.port:
                self._set_web3()
                if not self._web3:
                    self._start()
                else:
                    # The user configured a port and the anvil process was already running.
                    logger.info(
                        f"Connecting to existing '{self.process_name}' at port '{self.port}'."
                    )
            else:
                for _ in range(self.config.process_attempts):  # type: ignore
                    try:
                        self._start()
                        break
                    except FoundryNotInstalledError:
                        # Is a sub-class of `FoundrySubprocessError` but we to still raise
                        # so we don't keep retrying.
                        raise
                    except SubprocessError as exc:
                        logger.info("Retrying anvil subprocess startup: %r", exc)
                        self.port = None

    def _set_web3(self):
        if not self.port:
            return

        self._web3 = Web3(HTTPProvider(self.uri))
        if not self._web3.isConnected():
            self._web3 = None
            return

        # Verify is actually a Foundry provider,
        # or else skip it to possibly try another port.
        client_version = self._web3.clientVersion

        if "anvil" in client_version.lower():
            self._web3.eth.set_gas_price_strategy(rpc_gas_price_strategy)
        else:
            raise ProviderError(
                f"Port '{self.port}' already in use by another process that isn't a Foundry node."
            )

    def _start(self):
        use_random_port = self.port == "auto"
        if use_random_port:
            self.port = None

            if DEFAULT_PORT not in self.attempted_ports and not use_random_port:
                self.port = DEFAULT_PORT
            else:
                port = random.randint(EPHEMERAL_PORTS_START, EPHEMERAL_PORTS_END)
                max_attempts = 25
                attempts = 0
                while port in self.attempted_ports:
                    port = random.randint(EPHEMERAL_PORTS_START, EPHEMERAL_PORTS_END)
                    attempts += 1
                    if attempts == max_attempts:
                        ports_str = ", ".join([str(p) for p in self.attempted_ports])
                        raise FoundryProviderError(
                            f"Unable to find an available port. Ports tried: {ports_str}"
                        )

                self.port = port

        self.attempted_ports.append(self.port)
        self.start()

    def disconnect(self):
        self._web3 = None
        self.port = None
        super().disconnect()

    def build_command(self) -> List[str]:
        return [
            self.anvil_bin,
            "--port",
            f"{self.port}",
            "--mnemonic",
            self.mnemonic,
            "--accounts",
            f"{self.number_of_accounts}",
            "--derivation-path",
            "m/44'/60'/0'",
        ]

    def _make_request(self, rpc: str, args: list) -> Any:
        return self._web3.manager.request_blocking(rpc, args)  # type: ignore

    def set_timestamp(self, new_timestamp: int):
        pending_timestamp = self.get_block("pending").timestamp
        seconds_to_increase = new_timestamp - pending_timestamp
        self._make_request("evm_increaseTime", [seconds_to_increase])

    def mine(self, num_blocks: int = 1):
        for i in range(num_blocks):
            self._make_request("evm_mine", [1])

    def snapshot(self) -> str:
        result = self._make_request("evm_snapshot", [])
        return str(result)

    def revert(self, snapshot_id: SnapshotID):
        if isinstance(snapshot_id, str) and snapshot_id.isnumeric():
            snapshot_id = int(snapshot_id)  # type: ignore

        return self._make_request("evm_revert", [snapshot_id])

    def unlock_account(self, address: AddressType) -> bool:
        self._make_request("anvil_impersonateAccount", [address])
        self.unlocked_accounts.append(address)
        return True

    def estimate_gas_cost(self, txn: TransactionAPI) -> int:
        """
        Generates and returns an estimate of how much gas is necessary
        to allow the transaction to complete.
        The transaction will not be added to the blockchain.
        """
        try:
            return super().estimate_gas_cost(txn)
        except ValueError as err:
            tx_error = _get_vm_error(err)

            # If this is the cause of a would-be revert,
            # raise ContractLogicError so that we can confirm tx-reverts.
            if isinstance(tx_error, ContractLogicError):
                raise tx_error from err

            message = gas_estimation_error_message(tx_error)
            raise TransactionError(base_err=tx_error, message=message) from err

    def send_transaction(self, txn: TransactionAPI) -> ReceiptAPI:
        """
        Creates a new message call transaction or a contract creation
        for signed transactions.
        """

        sender = txn.sender
        if sender:
            sender = self.conversion_manager.convert(txn.sender, AddressType)

        if sender in self.unlocked_accounts:
            # Allow for an unsigned transaction
            txn_dict = txn.dict()

            try:
                txn_hash = self._web3.eth.send_transaction(txn_dict)  # type: ignore
            except ValueError as err:
                raise _get_vm_error(err) from err

            receipt = self.get_transaction(
                txn_hash.hex(), required_confirmations=txn.required_confirmations or 0
            )

        try:
            receipt = super().send_transaction(txn)
        except ValueError as err:
            raise _get_vm_error(err) from err

        receipt.raise_for_status()
        return receipt


class FoundryForkProvider(FoundryProvider):
    """
    A Foundry provider that uses ``--fork``, like:
    ``npx foundry node --fork <upstream-provider-url>``.

    Set the ``upstream_provider`` in the ``foundry.fork`` config
    section of your ``ape-config.yaml` file to specify which provider
    to use as your archive node.
    """

    @property
    def _upstream_network_name(self) -> str:
        return self.network.name.replace("-fork", "")

    @cached_property
    def _fork_config(self) -> FoundryForkConfig:
        config = cast(FoundryNetworkConfig, self.config)

        # NOTE: Only for backwards compatibility
        if "mainnet_fork" in config.dict():
            logger.warning(
                "Use of key `mainnet_fork` in `foundry` config is deprecated. "
                "Please use the `fork` key, with `ecosystem` and `network` subkeys."
            )
            return FoundryForkConfig.parse_obj(config.dict().get("mainnet_fork"))

        ecosystem_name = self.network.ecosystem.name
        if ecosystem_name not in config.fork:
            return FoundryForkConfig()  # Just use default

        network_name = self._upstream_network_name
        if network_name not in config.fork[ecosystem_name]:
            return FoundryForkConfig()  # Just use default

        return config.fork[ecosystem_name][network_name]

    @cached_property
    def _upstream_provider(self) -> ProviderAPI:
        upstream_network = self.network.ecosystem.networks[self._upstream_network_name]
        upstream_provider_name = self._fork_config.upstream_provider
        # NOTE: if 'upstream_provider_name' is 'None', this gets the default mainnet provider.
        return upstream_network.get_provider(provider_name=upstream_provider_name)

    def connect(self):
        super().connect()

        # Verify that we're connected to a Foundry node with mainnet-fork mode.
        self._upstream_provider.connect()
        upstream_chain_id = self._upstream_provider.chain_id
        upstream_genesis_block_hash = self._upstream_provider.get_block(0).hash
        self._upstream_provider.disconnect()

        # If upstream network is rinkeby, goerli, or kovan (PoA test-nets)
        if upstream_chain_id in (4, 5, 42):
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if self.get_block(0).hash != upstream_genesis_block_hash:
            logger.warning(
                "Upstream network has mismatching genesis block. "
                "This could be an issue with foundry."
            )

    def build_command(self) -> List[str]:
        if not isinstance(self._upstream_provider, UpstreamProvider):
            raise FoundryProviderError(
                f"Provider '{self._upstream_provider.name}' is not an upstream provider."
            )

        fork_url = self._upstream_provider.connection_str  # type: ignore
        if not fork_url:
            raise FoundryProviderError("Upstream provider does not have a ``connection_str``.")

        if fork_url.replace("localhost", "127.0.0.1") == self.uri:
            raise FoundryProviderError(
                "Invalid upstream-fork URL. Can't be same as local anvil node."
            )

        cmd = super().build_command()
        cmd.extend(("--fork-url", fork_url))
        fork_block_number = self._fork_config.block_number
        if fork_block_number is not None:
            cmd.extend(("--fork-block-number", str(fork_block_number)))

        return cmd


def _get_vm_error(web3_value_error: ValueError) -> TransactionError:
    if not len(web3_value_error.args):
        return VirtualMachineError(base_err=web3_value_error)

    err_data = web3_value_error.args[0]
    if not isinstance(err_data, dict):
        return VirtualMachineError(base_err=web3_value_error)

    message = str(err_data.get("message"))
    if not message:
        return VirtualMachineError(base_err=web3_value_error)

    # Handle `ContactLogicError` similarly to other providers in `ape`.
    # by stripping off the unnecessary prefix that foundry has on reverts.
    foundry_prefix = (
        "Error: VM Exception while processing transaction: reverted with reason string "
    )
    if message.startswith(foundry_prefix):
        message = message.replace(foundry_prefix, "").strip("'")
        return ContractLogicError(revert_message=message)
    elif "Transaction reverted without a reason string" in message:
        return ContractLogicError()

    elif message == "Transaction ran out of gas":
        return OutOfGasError()

    return VirtualMachineError(message=message)
