import random
import shutil
from bisect import bisect_right
from pathlib import Path
from subprocess import PIPE, call
from typing import Any, Dict, List, Literal, Optional, Union, cast

from ape.api import (
    BlockAPI,
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
    VirtualMachineError,
)
from ape.logging import logger
from ape.types import AddressType, BlockID, SnapshotID
from ape.utils import cached_property
from ape_test import Config as TestConfig
from eth_utils import to_checksum_address
from evm_trace import CallTreeNode, ParityTraceList, get_calltree_from_parity_trace
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.middleware import geth_poa_middleware
from web3.types import RPCEndpoint

from ape_foundry.constants import EVM_VERSION_BY_NETWORK

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
    evm_version: Optional[str] = None


class FoundryNetworkConfig(PluginConfig):
    port: Optional[Union[int, Literal["auto"]]] = DEFAULT_PORT

    # Retry strategy configs, try increasing these if you're getting FoundrySubprocessError
    network_retries: List[float] = FOUNDRY_START_NETWORK_RETRIES
    process_attempts: int = FOUNDRY_START_PROCESS_ATTEMPTS
    request_timeout: int = 30
    fork_request_timeout: int = 300

    # For setting the values in --fork and --fork-block-number command arguments.
    # Used only in FoundryForkProvider.
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
    cached_chain_id: Optional[int] = None

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
    def timeout(self) -> int:
        return self.config.request_timeout  # type: ignore

    @property
    def chain_id(self) -> int:
        if self.cached_chain_id is not None:
            return self.cached_chain_id

        elif self.cached_chain_id is None and hasattr(self.web3, "eth"):
            self.cached_chain_id = self.web3.eth.chain_id
            return self.cached_chain_id

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
        return self.conversion_manager.convert("2 gwei", int)

    @property
    def is_connected(self) -> bool:
        if self._web3 is not None and self._web3.isConnected():
            return True

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
                    # Process attempts to get started at this point.
                    self._start()

                    wait_for_key = "Listening on"
                    timeout = 10
                    iterations = 0
                    while iterations < timeout:
                        logged_lines = [x for x in self.stdout_logs_path.read_text().split("\n")]
                        for line in logged_lines:
                            if line.startswith(wait_for_key):
                                return

                        iterations += 1
                        if iterations == timeout:
                            raise ProviderError("Timed-out waiting for process to begin listening.")

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

        self._web3 = Web3(HTTPProvider(self.uri, request_kwargs={"timeout": self.timeout}))
        if not self._web3.isConnected():
            self._web3 = None
            return

        try:
            self._web3.eth.get_block_number()
        except Exception:
            # Not yet ready
            self._web3 = None
            return

        if not self.process:
            # Connected to already-running process.
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

    def set_balance(self, account: AddressType, balance: int):
        if hasattr(account, "address"):
            account = account.address  # type: ignore

        if isinstance(balance, int):
            # Anvil expects str int for balance
            balance_value = HexBytes(balance).hex()
        else:
            balance_value = str(balance)

        self._make_request("anvil_setBalance", [account, balance_value])

    def set_timestamp(self, new_timestamp: int):
        self._make_request("evm_setNextBlockTimestamp", [new_timestamp])

    def mine(self, num_blocks: int = 1):
        result = self._make_request("evm_mine", [{"blocks": num_blocks}])
        if result.get("result") != "0x0":
            raise ProviderError(f"Failed to mine.\n{result}")

    def snapshot(self) -> str:
        result = self._make_request("evm_snapshot", [])
        if "result" not in result:
            raise ProviderError(f"Failed to get snapshot ID.\n{result}")

        return result["result"]

    def revert(self, snapshot_id: SnapshotID) -> bool:
        if isinstance(snapshot_id, int):
            snapshot_id = HexBytes(snapshot_id).hex()

        result = self._make_request("evm_revert", [snapshot_id])
        return result.get("result") is True

    def unlock_account(self, address: AddressType) -> bool:
        self._make_request("anvil_impersonateAccount", [address])
        self.unlocked_accounts.append(address)
        return True

    def send_transaction(self, txn: TransactionAPI) -> ReceiptAPI:
        """
        Creates a new message call transaction or a contract creation
        for signed transactions.
        """
        sender = txn.sender
        if sender:
            sender = self.conversion_manager.convert(txn.sender, AddressType)

        if sender and sender in self.unlocked_accounts:
            # Allow for an unsigned transaction

            sender = to_checksum_address(sender)  # For mypy
            txn = self.prepare_transaction(txn)
            original_code = self.get_code(sender)
            if original_code:
                self.set_code(sender, "")

            try:
                txn_hash = self.web3.eth.send_transaction(txn.dict())  # type: ignore
                receipt = self.get_receipt(
                    txn_hash.hex(), required_confirmations=txn.required_confirmations or 0
                )
            except ValueError as err:
                raise self.get_virtual_machine_error(err) from err
            finally:
                if original_code:
                    self.set_code(sender, original_code.hex())
        else:
            receipt = super().send_transaction(txn)

        receipt.raise_for_status()
        return receipt

    def get_balance(self, address: str) -> int:
        # NOTE: Original `web3.eth.get_balance` fails when using Anvil.
        if hasattr(address, "address"):
            address = address.address  # type: ignore

        result = self._make_request("eth_getBalance", [address, "latest"]).get("result")
        if not result:
            raise ProviderError(f"Failed to get balance for account '{address}'.")

        return int(result, 16) if isinstance(result, str) else result

    def get_call_tree(self, txn_hash: str) -> CallTreeNode:
        response = self._make_request("trace_transaction", [txn_hash])

        if "error" in response:
            raise ProviderError(response["error"].get("message", "Failed to get call tree."))

        raw_trace_list = response.get("result", [])
        trace_list = ParityTraceList.parse_obj(raw_trace_list)

        if not trace_list:
            raise ProviderError(f"No trace found for transaction '{txn_hash}'")

        return get_calltree_from_parity_trace(trace_list)

    def get_virtual_machine_error(self, exception: Exception) -> VirtualMachineError:
        if not len(exception.args):
            return VirtualMachineError(base_err=exception)

        err_data = exception.args[0]
        message = str(err_data.get("message")) if isinstance(err_data, dict) else err_data

        if not message:
            return VirtualMachineError(base_err=exception)

        # Handle `ContactLogicError` similarly to other providers in `ape`.
        # by stripping off the unnecessary prefix that foundry has on reverts.
        foundry_prefix = (
            "Error: VM Exception while processing transaction: reverted with reason string "
        )
        if message.startswith(foundry_prefix):
            message = message.replace(foundry_prefix, "").strip("'")
            return ContractLogicError(revert_message=message)

        elif (
            "Transaction reverted without a reason string" in message
            or message.lower() == "execution reverted"
        ):
            return ContractLogicError()

        elif message == "Transaction ran out of gas":
            return OutOfGasError()  # type: ignore

        elif message.startswith("execution reverted: "):
            raise ContractLogicError(message.replace("execution reverted: ", "").strip())

        return VirtualMachineError(message=message)

    def set_code(self, address: AddressType, code: str):
        self._make_request("anvil_setCode", [address, code])

    def _make_request(self, rpc: str, args: list) -> Any:
        return self.web3.provider.make_request(RPCEndpoint(rpc), args)


class FoundryForkProvider(FoundryProvider):
    """
    A Foundry provider that uses ``--fork``, like:
    ``npx foundry node --fork <upstream-provider-url>``.

    Set the ``upstream_provider`` in the ``foundry.fork`` config
    section of your ``ape-config.yaml` file to specify which provider
    to use as your archive node.
    """

    @property
    def fork_url(self) -> str:
        return self._upstream_provider.connection_str  # type: ignore

    @property
    def fork_block_number(self) -> Optional[int]:
        return self._fork_config.block_number

    def get_block(self, block_id: BlockID) -> BlockAPI:
        if isinstance(block_id, str) and block_id.isnumeric():
            block_id = int(block_id)

        block_data = dict(self.web3.eth.get_block(block_id))

        # Fix Foundry-specific differences
        if "baseFeePerGas" in block_data and block_data.get("baseFeePerGas") is None:
            block_data["baseFeePerGas"] = 0

        return self.network.ecosystem.decode_block(block_data)

    def detect_evm_version(self) -> Optional[str]:
        if self.fork_block_number is None:
            return None

        ecosystem = self._upstream_provider.network.ecosystem.name
        network = self._upstream_provider.network.name
        try:
            hardforks = EVM_VERSION_BY_NETWORK[ecosystem][network]
        except KeyError:
            return None

        keys = sorted(hardforks)
        index = bisect_right(keys, self.fork_block_number) - 1
        return hardforks[keys[index]]

    @property
    def timeout(self) -> int:
        return self.config.fork_request_timeout  # type: ignore

    @property
    def _upstream_network_name(self) -> str:
        return self.network.name.replace("-fork", "")

    @cached_property
    def _fork_config(self) -> FoundryForkConfig:
        config = cast(FoundryNetworkConfig, self.config)
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
        # NOTE: if 'upstream_provider_name' is 'None', this gets the default upstream provider.
        return upstream_network.get_provider(provider_name=upstream_provider_name)

    def connect(self):
        super().connect()

        # Verify that we're connected to a Foundry node with fork mode.
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

        if not self.fork_url:
            raise FoundryProviderError("Upstream provider does not have a ``connection_str``.")

        if self.fork_url.replace("localhost", "127.0.0.1") == self.uri:
            raise FoundryProviderError(
                "Invalid upstream-fork URL. Can't be same as local anvil node."
            )

        cmd = super().build_command()
        cmd.extend(("--fork-url", self.fork_url))
        if self.fork_block_number is not None:
            cmd.extend(("--fork-block-number", str(self.fork_block_number)))

            if self._fork_config.evm_version is None:
                self._fork_config.evm_version = self.detect_evm_version()

        if self._fork_config.evm_version is not None:
            cmd.extend(("--hardfork", self._fork_config.evm_version))

        return cmd

    def reset_fork(self):
        self._make_request(
            "anvil_reset", [{"jsonRpcUrl": self.fork_url, "blockNumber": self.fork_block_number}]
        )
