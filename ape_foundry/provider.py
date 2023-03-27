import random
import shutil
from bisect import bisect_right
from copy import copy
from pathlib import Path
from subprocess import PIPE, call
from typing import Any, Dict, Iterator, List, Literal, Optional, Union, cast

from ape.api import (
    BlockAPI,
    PluginConfig,
    ReceiptAPI,
    SubprocessProvider,
    TestProviderAPI,
    TransactionAPI,
    UpstreamProvider,
    Web3Provider,
)
from ape.exceptions import (
    APINotImplementedError,
    ContractLogicError,
    OutOfGasError,
    ProviderError,
    SubprocessError,
    VirtualMachineError,
)
from ape.logging import logger
from ape.types import AddressType, BlockID, CallTreeNode, ContractCode, SnapshotID, TraceFrame
from ape.utils import cached_property
from ape_test import Config as TestConfig
from eth_typing import HexStr
from eth_utils import add_0x_prefix, is_0x_prefixed, is_hex, to_checksum_address, to_hex
from evm_trace import CallType, ParityTraceList
from evm_trace import TraceFrame as EvmTraceFrame
from evm_trace import get_calltree_from_geth_trace, get_calltree_from_parity_trace
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3
from web3.exceptions import ExtraDataLengthError
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.middleware import geth_poa_middleware
from web3.middleware.validation import MAX_EXTRADATA_LENGTH
from web3.types import TxParams

from ape_foundry.constants import EVM_VERSION_BY_NETWORK

from .exceptions import FoundryNotInstalledError, FoundryProviderError, FoundrySubprocessError

EPHEMERAL_PORTS_START = 49152
EPHEMERAL_PORTS_END = 60999
DEFAULT_PORT = 8545
FOUNDRY_CHAIN_ID = 31337


class FoundryForkConfig(PluginConfig):
    upstream_provider: Optional[str] = None
    block_number: Optional[int] = None
    evm_version: Optional[str] = None


class FoundryNetworkConfig(PluginConfig):
    port: Optional[Union[int, Literal["auto"]]] = DEFAULT_PORT

    # Retry strategy configs, try increasing these if you're getting FoundrySubprocessError
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
        return self.config.request_timeout

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
            self.port = self.provider_settings.get("port", self.config.port)

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
                    if not self.stdout_logs_path.is_file():
                        # Process output not being captured
                        return

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
                for _ in range(self.config.process_attempts):
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
        if not self._web3.is_connected():
            self._web3 = None
            return

        # Verify is actually a Foundry provider,
        # or else skip it to possibly try another port.
        # TODO: Once we are on web3.py 0.6.0b8 or later, can just use snake_case here.
        client_version = getattr(self._web3, "client_version", getattr(self._web3, "clientVersion"))

        if "anvil" in client_version.lower():
            self._web3.eth.set_gas_price_strategy(rpc_gas_price_strategy)
        else:
            raise ProviderError(
                f"Port '{self.port}' already in use by another process that isn't an Anvil node."
            )

        self._set_poa_middleware()

    def _set_poa_middleware(self):
        try:
            block = self.web3.eth.get_block(0)
        except ExtraDataLengthError:
            began_poa = True
        else:
            began_poa = (
                "proofOfAuthorityData" in block
                or len(block.get("extraData", "")) > MAX_EXTRADATA_LENGTH
            )

        if began_poa:
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

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
            "--steps-tracing",
        ]

    def estimate_gas_cost(self, txn: TransactionAPI, **kwargs) -> int:
        txn_dict = txn.dict()

        # Anvil is unable to handle integer-based type.
        # https://github.com/foundry-rs/foundry/issues/4240
        if isinstance(txn_dict.get("type"), int):
            txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

        modified_txn = txn.__class__.construct(**txn_dict)
        return super().estimate_gas_cost(modified_txn)

    def set_balance(self, account: AddressType, amount: Union[int, float, str, bytes]):
        is_str = isinstance(amount, str)
        _is_hex = False if not is_str else is_0x_prefixed(str(amount))
        is_key_word = is_str and len(str(amount).split(" ")) > 1
        if is_key_word:
            # This allows values such as "1000 ETH".
            amount = self.conversion_manager.convert(amount, int)
            is_str = False

        amount_hex_str = str(amount)

        # Convert to hex str
        if is_str and not _is_hex:
            amount_hex_str = to_hex(int(amount))
        elif isinstance(amount, int) or isinstance(amount, bytes):
            amount_hex_str = to_hex(amount)

        self._make_request("anvil_setBalance", [account, amount_hex_str])

    def set_timestamp(self, new_timestamp: int):
        self._make_request("evm_setNextBlockTimestamp", [new_timestamp])

    def mine(self, num_blocks: int = 1):
        result = self._make_request("evm_mine", [{"blocks": num_blocks, "timestamp": None}])
        if result != "0x0":
            raise ProviderError(f"Failed to mine.\n{result}")

    def snapshot(self) -> str:
        return self._make_request("evm_snapshot", [])

    def revert(self, snapshot_id: SnapshotID) -> bool:
        if isinstance(snapshot_id, int):
            snapshot_id = HexBytes(snapshot_id).hex()

        result = self._make_request("evm_revert", [snapshot_id])
        return result is True

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
            original_code = HexBytes(self.get_code(sender))
            if original_code:
                self.set_code(sender, "")

            try:
                txn_dict = txn.dict()
                if isinstance(txn_dict.get("type"), int):
                    txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

                tx_params = cast(TxParams, txn_dict)
                txn_hash = self.web3.eth.send_transaction(tx_params)

            except ValueError as err:
                raise self.get_virtual_machine_error(err) from err
            finally:
                if original_code:
                    self.set_code(sender, original_code.hex())
        else:
            try:
                txn_hash = self.web3.eth.send_raw_transaction(txn.serialize_transaction())
            except ValueError as err:
                vm_err = self.get_virtual_machine_error(err, txn=txn)

                if "nonce too low" in str(vm_err):
                    # Add additional nonce information
                    new_err_msg = f"Nonce '{txn.nonce}' is too low"
                    raise VirtualMachineError(
                        new_err_msg, base_err=vm_err.base_err, code=vm_err.code
                    )

                vm_err.txn = txn
                raise vm_err from err

        receipt = self.get_receipt(
            txn_hash.hex(),
            required_confirmations=(
                txn.required_confirmations
                if txn.required_confirmations is not None
                else self.network.required_confirmations
            ),
        )

        if receipt.failed:
            txn_dict = receipt.transaction.dict()
            if isinstance(txn_dict.get("type"), int):
                txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

            txn_params = cast(TxParams, txn_dict)

            # Replay txn to get revert reason
            try:
                self.web3.eth.call(txn_params)
            except Exception as err:
                vm_err = self.get_virtual_machine_error(err, txn=txn)
                vm_err.txn = txn
                raise vm_err from err

        logger.info(f"Confirmed {receipt.txn_hash} (total fees paid = {receipt.total_fees_paid})")
        self.chain_manager.history.append(receipt)
        return receipt

    def send_call(self, txn: TransactionAPI, **kwargs: Any) -> bytes:
        skip_trace = kwargs.pop("skip_trace", False)
        arguments = self._prepare_call(txn, **kwargs)

        if skip_trace:
            return self._eth_call(arguments)

        show_gas = kwargs.pop("show_gas_report", False)
        show_trace = kwargs.pop("show_trace", False)
        track_gas = self.chain_manager._reports.track_gas
        needs_trace = show_gas or show_trace or track_gas
        if not needs_trace:
            return self._eth_call(arguments)

        # The user is requesting information related to a call's trace,
        # such as gas usage data.

        if "type" in arguments[0] and isinstance(arguments[0]["type"], int):
            arguments[0]["type"] = to_hex(arguments[0]["type"])

        result = self._make_request("debug_traceCall", arguments)
        trace_data = result.get("structLogs", [])
        trace_frames = (EvmTraceFrame(**f) for f in trace_data)
        return_value = HexBytes(result["returnValue"])
        root_node_kwargs = {
            "gas_cost": result.get("gas", 0),
            "address": txn.receiver,
            "calldata": txn.data,
            "value": txn.value,
            "call_type": CallType.CALL,
            "failed": False,
            "returndata": return_value,
        }

        evm_call_tree = get_calltree_from_geth_trace(trace_frames, **root_node_kwargs)

        # NOTE: Don't pass txn_hash here, as it will fail (this is not a real txn).
        call_tree = self._create_call_tree_node(evm_call_tree)

        receiver = txn.receiver
        if track_gas and show_gas and not show_trace:
            # Optimization to enrich early and in_place=True.
            call_tree.enrich()

        if track_gas and call_tree and receiver is not None:
            # Gas report being collected, likely for showing a report
            # at the end of a test run.
            # Use `in_place=False` in case also `show_trace=True`
            enriched_call_tree = call_tree.enrich(in_place=False)
            self.chain_manager._reports.append_gas(enriched_call_tree, receiver)

        if show_gas:
            enriched_call_tree = call_tree.enrich(in_place=False)
            self.chain_manager._reports.show_gas(enriched_call_tree)

        if show_trace:
            call_tree = call_tree.enrich(use_symbol_for_tokens=True)
            self.chain_manager._reports.show_trace(call_tree)

        return return_value

    def get_balance(self, address: str) -> int:
        if hasattr(address, "address"):
            address = address.address

        result = self._make_request("eth_getBalance", [address, "latest"])
        if not result:
            raise ProviderError(f"Failed to get balance for account '{address}'.")

        return int(result, 16) if isinstance(result, str) else result

    def get_transaction_trace(self, txn_hash: str) -> Iterator[TraceFrame]:
        for trace in self._get_transaction_trace(txn_hash):
            yield self._create_trace_frame(trace)

    def _get_transaction_trace(self, txn_hash: str) -> Iterator[EvmTraceFrame]:
        result = self._make_request("debug_traceTransaction", [txn_hash, {"stepsTracing": True}])
        frames = result.get("structLogs", [])
        for frame in frames:
            yield EvmTraceFrame(**frame)

    def get_call_tree(self, txn_hash: str) -> CallTreeNode:
        raw_trace_list = self._make_request("trace_transaction", [txn_hash])
        trace_list = ParityTraceList.parse_obj(raw_trace_list)

        if not trace_list:
            raise ProviderError(f"No trace found for transaction '{txn_hash}'")

        evm_call = get_calltree_from_parity_trace(trace_list)
        return self._create_call_tree_node(evm_call, txn_hash=txn_hash)

    def get_virtual_machine_error(self, exception: Exception, **kwargs) -> VirtualMachineError:
        txn = kwargs.get("txn")
        if not len(exception.args):
            return VirtualMachineError(base_err=exception, txn=txn)

        err_data = exception.args[0]
        message = str(err_data.get("message")) if isinstance(err_data, dict) else err_data

        if not message:
            return VirtualMachineError(base_err=exception, txn=txn)

        # Handle `ContactLogicError` similarly to other providers in `ape`.
        # by stripping off the unnecessary prefix that foundry has on reverts.
        foundry_prefix = (
            "Error: VM Exception while processing transaction: reverted with reason string "
        )
        if message.startswith(foundry_prefix):
            message = message.replace(foundry_prefix, "").strip("'")
            return ContractLogicError(revert_message=message, txn=txn)

        elif (
            "Transaction reverted without a reason string" in message
            or message.lower() == "execution reverted"
        ):
            return ContractLogicError(txn=txn)

        elif message == "Transaction ran out of gas":
            return OutOfGasError(txn=txn)

        elif message.startswith("execution reverted: "):
            raise ContractLogicError(message.replace("execution reverted: ", "").strip(), txn=txn)

        return VirtualMachineError(message, txn=txn)

    def set_block_gas_limit(self, gas_limit: int) -> bool:
        return self._make_request("evm_setBlockGasLimit", [hex(gas_limit)]) is True

    def set_code(self, address: AddressType, code: ContractCode) -> bool:
        if isinstance(code, bytes):
            code = code.hex()

        elif isinstance(code, str) and not is_0x_prefixed(code):
            code = add_0x_prefix(HexStr(code))

        elif not is_hex(code):
            raise ValueError(f"Value {code} is not convertible to hex")

        self._make_request("anvil_setCode", [address, code])
        return True

    def _eth_call(self, arguments: List) -> bytes:
        # Override from Web3Provider because foundry is pickier.

        txn_dict = copy(arguments[0])
        if isinstance(txn_dict.get("type"), int):
            txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

        txn_dict.pop("chainId", None)
        arguments[0] = txn_dict

        try:
            result = self._make_request("eth_call", arguments)
        except Exception as err:
            raise self.get_virtual_machine_error(err) from err

        return HexBytes(result)


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
        return self._upstream_provider.connection_str

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
        return self.config.fork_request_timeout

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
    def _upstream_provider(self) -> UpstreamProvider:
        upstream_network = self.network.ecosystem.networks[self._upstream_network_name]
        upstream_provider_name = self._fork_config.upstream_provider
        # NOTE: if 'upstream_provider_name' is 'None', this gets the default upstream provider.
        return upstream_network.get_provider(provider_name=upstream_provider_name)

    def connect(self):
        super().connect()

        # Verify that we're connected to a Foundry node with fork mode.
        upstream_provider = self._upstream_provider
        upstream_provider.connect()
        try:
            upstream_genesis_block_hash = upstream_provider.get_block(0).hash
        except ExtraDataLengthError as err:
            if isinstance(upstream_provider, Web3Provider):
                logger.error(
                    f"Upstream provider '{upstream_provider.name}' missing Geth PoA middleware."
                )
                upstream_provider.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
                upstream_genesis_block_hash = upstream_provider.get_block(0).hash
            else:
                raise ProviderError(f"Unable to get genesis block: {err}.") from err

        upstream_provider.disconnect()
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

    def reset_fork(self, block_number: Optional[int] = None):
        forking_params: Dict[str, Union[str, int]] = {"jsonRpcUrl": self.fork_url}
        block_number = block_number if block_number is not None else self.fork_block_number
        if block_number is not None:
            forking_params["blockNumber"] = block_number

        result = self._make_request("anvil_reset", [{"forking": forking_params}])

        try:
            base_fee = self.base_fee
        except APINotImplementedError:
            base_fee = None
            logger.warning("base_fee not found in block - base fee may not be reset.")

        # reset next block base fee to that of new chain head if can
        if base_fee is not None:
            self._make_request("anvil_setNextBlockBaseFeePerGas", [base_fee])

        return result
