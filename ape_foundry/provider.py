import os
import random
import shutil
from bisect import bisect_right
from copy import copy
from itertools import tee
from pathlib import Path
from subprocess import PIPE, call
from typing import Any, Dict, Iterator, List, Literal, Optional, Tuple, Union, cast

from ape._pydantic_compat import root_validator
from ape.api import (
    BlockAPI,
    ForkedNetworkAPI,
    PluginConfig,
    ReceiptAPI,
    SubprocessProvider,
    TestProviderAPI,
    TransactionAPI,
    Web3Provider,
)
from ape.exceptions import (
    APINotImplementedError,
    ContractLogicError,
    OutOfGasError,
    SubprocessError,
    TransactionError,
    VirtualMachineError,
)
from ape.logging import logger
from ape.types import (
    AddressType,
    BlockID,
    CallTreeNode,
    ContractCode,
    SnapshotID,
    SourceTraceback,
    TraceFrame,
)
from ape.utils import cached_property
from ape_test import Config as TestConfig
from eth_typing import HexStr
from eth_utils import add_0x_prefix, is_0x_prefixed, is_hex, to_hex
from ethpm_types import HexBytes
from evm_trace import CallType, ParityTraceList
from evm_trace import TraceFrame as EvmTraceFrame
from evm_trace import get_calltree_from_geth_trace, get_calltree_from_parity_trace
from web3 import HTTPProvider, Web3
from web3.exceptions import ContractCustomError
from web3.exceptions import ContractLogicError as Web3ContractLogicError
from web3.exceptions import ExtraDataLengthError
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.middleware import geth_poa_middleware
from web3.middleware.validation import MAX_EXTRADATA_LENGTH
from web3.types import TxParams
from yarl import URL

from ape_foundry.constants import EVM_VERSION_BY_NETWORK

from .exceptions import FoundryNotInstalledError, FoundryProviderError, FoundrySubprocessError
from .utils import to_bytes32

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
    """Deprecated. Use ``host`` config."""

    host: Optional[Union[str, Literal["auto"]]] = None
    """The host address or ``"auto"`` to use localhost with a random port (with attempts)."""

    manage_process: bool = True
    """
    If ``True`` and the host is local and Anvil is not running, will attempt to start.
    Defaults to ``True``. If ``host`` is remote, will not be able to start.
    """

    # Retry strategy configs, try increasing these if you're getting FoundrySubprocessError
    request_timeout: int = 30
    fork_request_timeout: int = 300
    process_attempts: int = 5

    # RPC defaults
    base_fee: int = 0
    priority_fee: int = 0

    # For setting the values in --fork and --fork-block-number command arguments.
    # Used only in FoundryForkProvider.
    # Mapping of ecosystem_name => network_name => FoundryForkConfig
    fork: Dict[str, Dict[str, FoundryForkConfig]] = {}

    auto_mine: bool = True
    """
    Automatically mine blocks instead of manually doing so.
    """

    block_time: Optional[int] = None
    """
    Set a block time to allow mining to happen on an interval
    rather than only when a new transaction is submitted.
    """

    class Config:
        extra = "allow"


def _call(*args):
    return call([*args], stderr=PIPE, stdout=PIPE, stdin=PIPE)


class FoundryProvider(SubprocessProvider, Web3Provider, TestProviderAPI):
    _host: Optional[str] = None
    attempted_ports: List[int] = []
    cached_chain_id: Optional[int] = None
    _did_warn_wrong_node = False

    @property
    def unlocked_accounts(self) -> List[AddressType]:
        return list(self.account_manager.test_accounts._impersonated_accounts)

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
    def connection_id(self) -> Optional[str]:
        return f"{self.network_choice}:{self._host}"

    @property
    def timeout(self) -> int:
        return self.settings.request_timeout

    @property
    def _clean_uri(self) -> str:
        try:
            return str(URL(self.uri).with_user(None).with_password(None))
        except ValueError:
            # Likely isn't a real URI.
            return self.uri

    @property
    def _port(self) -> Optional[int]:
        return URL(self.uri).port

    @property
    def chain_id(self) -> int:
        if self.cached_chain_id is not None:
            return self.cached_chain_id

        elif self.cached_chain_id is None and self._web3 is not None and hasattr(self.web3, "eth"):
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
        if self._host is not None:
            return self._host

        elif config_host := self.settings.host:
            if config_host == "auto":
                self._host = "auto"
                return self._host
            if not config_host.startswith("http"):
                if "127.0.0.1" in config_host or "localhost" in config_host:
                    self._host = f"http://{config_host}"
                else:
                    self._host = f"https://{config_host}"
            else:
                self._host = config_host

            if "127.0.0.1" in config_host or "localhost" in config_host:
                host_without_http = self._host[7:]
                if ":" not in host_without_http:
                    self._host = f"{self._host}:{DEFAULT_PORT}"

        else:
            self._host = f"http://127.0.0.1:{DEFAULT_PORT}"

        return self._host

    @property
    def http_uri(self) -> str:
        # NOTE: Overriding `Web3Provider.http_uri` implementation
        return self.uri

    @property
    def ws_uri(self) -> str:
        # NOTE: Overriding `Web3Provider.ws_uri` implementation
        return "ws" + self.uri[4:]  # Remove `http` in default URI w/ `ws`

    @property
    def priority_fee(self) -> int:
        return self.settings.priority_fee

    @property
    def is_connected(self) -> bool:
        if self._host in ("auto", None):
            # Hasn't tried yet.
            return False

        self._set_web3()
        return self._web3 is not None

    @cached_property
    def _test_config(self) -> TestConfig:
        return cast(TestConfig, self.config_manager.get_config("test"))

    @property
    def auto_mine(self) -> bool:
        return self._make_request("anvil_getAutomine", [])

    @property
    def gas_price(self) -> int:
        # TODO: Remove this once Ape > 0.6.13
        result = super().gas_price
        if isinstance(result, str) and is_0x_prefixed(result):
            return int(result, 16)

        return result

    @property
    def settings(self) -> FoundryNetworkConfig:
        return cast(FoundryNetworkConfig, super().settings)

    def __setattr__(self, attr: str, value: Any) -> None:
        # NOTE: Need to do this until https://github.com/pydantic/pydantic/pull/2625 is figured out
        if attr == "auto_mine":
            self._make_request("anvil_setAutomine", [value])

        else:
            super().__setattr__(attr, value)

    def connect(self):
        """
        Start the foundry process and verify it's up and accepting connections.
        **NOTE**: Must set port before calling 'super().connect()'.
        """

        warning = "`port` setting is deprecated. Please use `host` key that includes the port."

        if self.settings.port != DEFAULT_PORT and self.settings.host is not None:
            raise FoundryProviderError(
                "Cannot use deprecated `port` field with `host`. "
                "Place `port` at end of `host` instead."
            )

        elif self.settings.port != DEFAULT_PORT:
            # We only get here if the user configured a port without a host,
            # the old way of doing it. TODO: Can remove after 0.7.
            logger.warning(warning)
            if self.settings.port not in (None, "auto"):
                self._host = f"http://127.0.0.1:{self.settings.port}"
            else:
                # This will trigger selecting a random port on localhost and trying.
                self._host = "auto"

        if "APE_FOUNDRY_HOST" in os.environ:
            self._host = os.environ["APE_FOUNDRY_HOST"]

        elif self._host is None:
            self._host = self.uri

        if self.is_connected:
            # Connects to already running process
            self._start()

        elif self.settings.manage_process and (
            "localhost" in self._host or "127.0.0.1" in self._host or self._host == "auto"
        ):
            # Only do base-process setup if not connecting to already-running process
            # and is running on localhost.
            super().connect()
            if self._host:
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
                            raise FoundryProviderError(
                                "Timed-out waiting for process to begin listening."
                            )

                else:
                    # The user configured a host and the anvil process was already running.
                    logger.info(
                        f"Connecting to existing '{self.process_name}' "
                        f"at host '{self._clean_uri}'."
                    )
            else:
                for _ in range(self.settings.process_attempts):
                    try:
                        self._start()
                        break
                    except FoundryNotInstalledError:
                        # Is a sub-class of `FoundrySubprocessError` but we to still raise
                        # so we don't keep retrying.
                        raise
                    except SubprocessError as exc:
                        logger.info("Retrying anvil subprocess startup: %r", exc)
                        self._host = None
        else:
            raise FoundryProviderError(
                f"Failed to connect to remote Anvil node at '{self._clean_uri}'."
            )

    def _set_web3(self):
        if not self._host:
            return

        self._web3 = Web3(HTTPProvider(self.uri, request_kwargs={"timeout": self.timeout}))

        try:
            is_connected = self._web3.is_connected()
        except Exception:
            is_connected = False

        if not is_connected:
            self._web3 = None
            return

        # Verify is actually a Foundry provider,
        # or else skip it to possibly try another port.
        client_version = self._web3.client_version.lower()
        if "anvil" in client_version:
            self._web3.eth.set_gas_price_strategy(rpc_gas_price_strategy)
        elif self._port is not None:
            raise FoundryProviderError(
                f"Port '{self._port}' already in use by another process that isn't an Anvil node."
            )
        else:
            # Not sure if possible to get here.
            raise FoundryProviderError("Failed to start Anvil process.")

        def check_poa(block_id) -> bool:
            try:
                block = self.web3.eth.get_block(block_id)
            except ExtraDataLengthError:
                return True
            else:
                return (
                    "proofOfAuthorityData" in block
                    or len(block.get("extraData", "")) > MAX_EXTRADATA_LENGTH
                )

        # Handle if using PoA
        if any(map(check_poa, (0, "latest"))):
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def _start(self):
        if self.is_connected:
            return

        use_random_port = self._host == "auto"
        if use_random_port:
            self._host = None

            if DEFAULT_PORT not in self.attempted_ports:
                # First, attempt the default port before anything else.
                self._host = f"127.0.0.1:{DEFAULT_PORT}"

            # Pick a random port
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

            self.attempted_ports.append(port)
            self._host = f"http://127.0.0.1:{port}"

        elif self._host is not None and ":" in self._host and self._port is not None:
            # Append the one and only port to the attempted ports list, for honest keeping.
            self.attempted_ports.append(self._port)

        else:
            self._host = f"http://127.0.0.1:{DEFAULT_PORT}"

        if "127.0.0.1" in self._host or "localhost" in self._host:
            # Start local process
            self.start()

        elif not self.is_connected:
            raise FoundryProviderError(f"Failed to connect to Anvil node at '{self._clean_uri}'.")

    def disconnect(self):
        self._web3 = None
        self._host = None
        super().disconnect()

    def build_command(self) -> List[str]:
        cmd = [
            self.anvil_bin,
            "--port",
            f"{self._port or DEFAULT_PORT}",
            "--mnemonic",
            self.mnemonic,
            "--accounts",
            f"{self.number_of_accounts}",
            "--derivation-path",
            "m/44'/60'/0'",
            "--steps-tracing",
            "--block-base-fee-per-gas",
            f"{self.settings.base_fee}",
        ]

        if not self.settings.auto_mine:
            cmd.append("--no-mining")

        if self.settings.block_time is not None:
            cmd.extend(("--block-time", f"{self.settings.block_time}"))

        return cmd

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
            raise FoundryProviderError(f"Failed to mine.\n{result}")

    def snapshot(self) -> str:
        return self._make_request("evm_snapshot", [])

    def revert(self, snapshot_id: SnapshotID) -> bool:
        if isinstance(snapshot_id, int):
            snapshot_id = HexBytes(snapshot_id).hex()

        result = self._make_request("evm_revert", [snapshot_id])
        return result is True

    def unlock_account(self, address: AddressType) -> bool:
        self._make_request("anvil_impersonateAccount", [address])
        return True

    def relock_account(self, address: AddressType):
        self._make_request("anvil_stopImpersonatingAccount", [address])
        if address in self.account_manager.test_accounts._impersonated_accounts:
            del self.account_manager.test_accounts._impersonated_accounts[address]

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
            sender = cast(AddressType, sender)  # We know it's checksummed at this point.
            txn = self.prepare_transaction(txn)
            original_code = HexBytes(self.get_code(sender))
            if original_code:
                self.set_code(sender, "")

            txn_dict = txn.dict()
            if isinstance(txn_dict.get("type"), int):
                txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

            tx_params = cast(TxParams, txn_dict)
            try:
                txn_hash = self.web3.eth.send_transaction(tx_params)
            except ValueError as err:
                raise self.get_virtual_machine_error(err, txn=txn) from err

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
                        new_err_msg,
                        base_err=vm_err.base_err,
                        code=vm_err.code,
                        txn=txn,
                        source_traceback=vm_err.source_traceback,
                        trace=vm_err.trace,
                        contract_address=vm_err.contract_address,
                    )

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
            # NOTE: For some reason, `nonce` can't be in the txn params or else it fails.
            if "nonce" in txn_params:
                del txn_params["nonce"]

            try:
                self.web3.eth.call(txn_params)
            except Exception as err:
                vm_err = self.get_virtual_machine_error(err, txn=receipt)
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

        if self._test_runner is not None:
            track_gas = self._test_runner.gas_tracker.enabled
            track_coverage = self._test_runner.coverage_tracker.enabled
        else:
            track_gas = False
            track_coverage = False

        needs_trace = track_gas or track_coverage or show_gas or show_trace
        if not needs_trace:
            return self._eth_call(arguments)

        # The user is requesting information related to a call's trace,
        # such as gas usage data.

        if "type" in arguments[0] and isinstance(arguments[0]["type"], int):
            arguments[0]["type"] = to_hex(arguments[0]["type"])

        result, trace_frames = self._trace_call(arguments)
        trace_frames, frames_copy = tee(trace_frames)
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

        if track_gas and call_tree and receiver is not None and self._test_runner is not None:
            # Gas report being collected, likely for showing a report
            # at the end of a test run.
            # Use `in_place=False` in case also `show_trace=True`
            enriched_call_tree = call_tree.enrich(in_place=False)
            self._test_runner.gas_tracker.append_gas(enriched_call_tree, receiver)

        if track_coverage and self._test_runner is not None and receiver:
            contract_type = self.chain_manager.contracts.get(receiver)
            if contract_type:
                traceframes = (self._create_trace_frame(x) for x in frames_copy)
                method_id = HexBytes(txn.data)
                selector = (
                    contract_type.methods[method_id].selector
                    if method_id in contract_type.methods
                    else None
                )
                source_traceback = SourceTraceback.create(contract_type, traceframes, method_id)
                self._test_runner.coverage_tracker.cover(
                    source_traceback, function=selector, contract=contract_type.name
                )

        if show_gas:
            enriched_call_tree = call_tree.enrich(in_place=False)
            self.chain_manager._reports.show_gas(enriched_call_tree)

        if show_trace:
            call_tree = call_tree.enrich(use_symbol_for_tokens=True)
            self.chain_manager._reports.show_trace(call_tree)

        return return_value

    def _trace_call(self, arguments: List[Any]) -> Tuple[Dict, Iterator[EvmTraceFrame]]:
        result = self._make_request("debug_traceCall", arguments)
        trace_data = result.get("structLogs", [])
        return result, (EvmTraceFrame(**f) for f in trace_data)

    def get_balance(self, address: str) -> int:
        if hasattr(address, "address"):
            address = address.address

        result = self._make_request("eth_getBalance", [address, "latest"])
        if not result:
            raise FoundryProviderError(f"Failed to get balance for account '{address}'.")

        return int(result, 16) if isinstance(result, str) else result

    def get_transaction_trace(self, txn_hash: str) -> Iterator[TraceFrame]:
        for trace in self._get_transaction_trace(txn_hash):
            yield self._create_trace_frame(trace)

    def _get_transaction_trace(self, txn_hash: str) -> Iterator[EvmTraceFrame]:
        result = self._make_request(
            "debug_traceTransaction", [txn_hash, {"stepsTracing": True, "enableMemory": True}]
        )
        frames = result.get("structLogs", [])
        for frame in frames:
            yield EvmTraceFrame(**frame)

    def get_call_tree(self, txn_hash: str) -> CallTreeNode:
        raw_trace_list = self._make_request("trace_transaction", [txn_hash])
        trace_list = ParityTraceList.parse_obj(raw_trace_list)

        if not trace_list:
            raise FoundryProviderError(f"No trace found for transaction '{txn_hash}'")

        evm_call = get_calltree_from_parity_trace(trace_list)
        return self._create_call_tree_node(evm_call, txn_hash=txn_hash)

    def get_virtual_machine_error(self, exception: Exception, **kwargs) -> VirtualMachineError:
        if not len(exception.args):
            return VirtualMachineError(base_err=exception, **kwargs)

        err_data = exception.args[0]
        message = str(err_data.get("message")) if isinstance(err_data, dict) else err_data

        if not message:
            return VirtualMachineError(base_err=exception, **kwargs)

        # Handle `ContactLogicError` similarly to other providers in `ape`.
        # by stripping off the unnecessary prefix that foundry has on reverts.
        foundry_prefix = (
            "Error: VM Exception while processing transaction: reverted with reason string "
        )
        if message.startswith(foundry_prefix):
            message = message.replace(foundry_prefix, "").strip("'")
            err = ContractLogicError(base_err=exception, revert_message=message, **kwargs)
            return self.compiler_manager.enrich_error(err)

        elif "Transaction reverted without a reason string" in message:
            err = ContractLogicError(base_err=exception, **kwargs)
            return self.compiler_manager.enrich_error(err)

        elif message.lower() == "execution reverted":
            err = ContractLogicError(TransactionError.DEFAULT_MESSAGE, base_err=exception, **kwargs)

            if isinstance(exception, Web3ContractLogicError):
                # Check for custom error.
                data = {}
                if "trace" in kwargs:
                    kwargs["trace"], new_trace = tee(kwargs["trace"])
                    data = list(new_trace)[-1].raw

                elif "txn" in kwargs:
                    try:
                        txn_hash = kwargs["txn"].txn_hash.hex()
                        data = list(self.get_transaction_trace(txn_hash))[-1].raw
                    except Exception:
                        pass

                if data.get("op") == "REVERT":
                    custom_err = "".join([x[2:] for x in data["memory"][4:]])
                    if custom_err:
                        err.message = f"0x{custom_err}"

            err.message = (
                TransactionError.DEFAULT_MESSAGE if err.message in ("", "0x", None) else err.message
            )
            return self.compiler_manager.enrich_error(err)

        elif message == "Transaction ran out of gas" or "OutOfGas" in message:
            return OutOfGasError(base_err=exception, **kwargs)

        elif message.startswith("execution reverted: "):
            message = (
                message.replace("execution reverted: ", "").strip()
                or TransactionError.DEFAULT_MESSAGE
            )
            err = ContractLogicError(message, base_err=exception, **kwargs)
            return self.compiler_manager.enrich_error(err)

        elif isinstance(exception, ContractCustomError):
            # Is raw hex (custom exception)
            message = TransactionError.DEFAULT_MESSAGE if message in ("", None, "0x") else message
            err = ContractLogicError(message, base_err=exception, **kwargs)
            return self.compiler_manager.enrich_error(err)

        return VirtualMachineError(message, **kwargs)

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

    def set_storage(self, address: AddressType, slot: int, value: HexBytes):
        self._make_request(
            "anvil_setStorageAt",
            [address, to_bytes32(slot).hex(), to_bytes32(value).hex()],
        )

    def _eth_call(self, arguments: List) -> bytes:
        # Override from Web3Provider because foundry is pickier.

        txn_dict = copy(arguments[0])
        if isinstance(txn_dict.get("type"), int):
            txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

        txn_dict.pop("chainId", None)
        arguments[0] = txn_dict
        trace = None

        try:
            result = self._make_request("eth_call", arguments)
        except Exception as err:
            contract_address = arguments[0].get("to") if len(arguments) > 0 else None
            tb = None
            if contract_address:
                try:
                    trace, trace2 = tee(
                        self._create_trace_frame(x) for x in self._trace_call(arguments)[1]
                    )
                    contract_type = self.chain_manager.contracts.get(contract_address)
                    method_id = arguments[0].get("data", "")[:10] or None
                    tb = (
                        SourceTraceback.create(contract_type, trace2, method_id)
                        if method_id and contract_type
                        else None
                    )
                except Exception as sub_err:
                    logger.error(f"Error getting source traceback: {sub_err}")

            if trace is None:
                trace = (self._create_trace_frame(x) for x in self._trace_call(arguments)[1])

            raise self.get_virtual_machine_error(
                err, trace=trace, contract_address=contract_address, source_traceback=tb
            ) from err

        return HexBytes(result)


class FoundryForkProvider(FoundryProvider):
    """
    A Foundry provider that uses ``--fork``, like:
    ``npx foundry node --fork <upstream-provider-url>``.

    Set the ``upstream_provider`` in the ``foundry.fork`` config
    section of your ``ape-config.yaml` file to specify which provider
    to use as your archive node.
    """

    @root_validator()
    def set_upstream_provider(cls, value):
        network = value["network"]
        adhoc_settings = value.get("provider_settings", {}).get("fork", {})
        ecosystem_name = network.ecosystem.name
        plugin_config = cls.config_manager.get_config(value["name"])
        config_settings = plugin_config.get("fork", {})

        def _get_upstream(data: Dict) -> Optional[str]:
            return (
                data.get(ecosystem_name, {})
                .get(network.name.replace("-fork", ""), {})
                .get("upstream_provider")
            )

        # If upstream provider set anywhere in provider settings, ignore.
        if name := (_get_upstream(adhoc_settings) or _get_upstream(config_settings)):
            getattr(network.ecosystem.config, network.name).upstream_provider = name

        return value

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

        ecosystem = self.forked_network.ecosystem.name
        network = self.forked_network.upstream_network.name
        try:
            hardforks = EVM_VERSION_BY_NETWORK[ecosystem][network]
        except KeyError:
            return None

        keys = sorted(hardforks)
        index = bisect_right(keys, self.fork_block_number) - 1
        return hardforks[keys[index]]

    @property
    def timeout(self) -> int:
        return self.settings.fork_request_timeout

    @property
    def _fork_config(self) -> FoundryForkConfig:
        ecosystem_name = self.network.ecosystem.name
        if ecosystem_name not in self.settings.fork:
            return FoundryForkConfig()  # Just use default

        network_name = self.forked_network.upstream_network.name
        if network_name not in self.settings.fork[ecosystem_name]:
            return FoundryForkConfig()  # Just use default

        return self.settings.fork[ecosystem_name][network_name]

    @property
    def forked_network(self) -> ForkedNetworkAPI:
        return cast(ForkedNetworkAPI, self.network)

    @property
    def upstream_provider_name(self) -> str:
        if upstream_name := self._fork_config.upstream_provider:
            self.forked_network.network_config.upstream_provider = upstream_name

        return self.forked_network.network_config.upstream_provider

    @property
    def fork_url(self) -> str:
        return self.forked_network.upstream_provider.connection_str

    def connect(self):
        super().connect()

        # If using the provider config for upstream_provider,
        # set the network one in this session, so other features work in core.
        with self.forked_network.use_upstream_provider() as upstream_provider:
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
                    raise FoundryProviderError(f"Unable to get genesis block: {err}.") from err

        if self.get_block(0).hash != upstream_genesis_block_hash:
            logger.warning(
                "Upstream network has mismatching genesis block. "
                "This could be an issue with foundry."
            )

    def build_command(self) -> List[str]:
        if not self.fork_url:
            raise FoundryProviderError("Upstream provider does not have a ``connection_str``.")

        if self.fork_url.replace("localhost", "127.0.0.1").replace("http://", "") == self.uri:
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
