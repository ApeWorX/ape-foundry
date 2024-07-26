import os
import random
import shutil
from bisect import bisect_right
from copy import copy
from subprocess import PIPE, call
from typing import Literal, Optional, Union, cast

from ape.api import (
    BlockAPI,
    ForkedNetworkAPI,
    PluginConfig,
    ReceiptAPI,
    SubprocessProvider,
    TestProviderAPI,
    TraceAPI,
    TransactionAPI,
)
from ape.exceptions import (
    ContractLogicError,
    OutOfGasError,
    SubprocessError,
    TransactionError,
    VirtualMachineError,
)
from ape.logging import logger
from ape.types import AddressType, BlockID, ContractCode, SnapshotID
from ape.utils import cached_property
from ape_ethereum.provider import Web3Provider
from ape_ethereum.trace import TraceApproach, TransactionTrace
from ape_test import ApeTestConfig
from eth_pydantic_types import HashBytes32, HexBytes
from eth_typing import HexStr
from eth_utils import add_0x_prefix, is_0x_prefixed, is_hex, to_hex
from pydantic import field_validator, model_validator
from pydantic_settings import SettingsConfigDict
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

EPHEMERAL_PORTS_START = 49152
EPHEMERAL_PORTS_END = 60999
DEFAULT_PORT = 8545
FOUNDRY_CHAIN_ID = 31337


class FoundryForkConfig(PluginConfig):
    upstream_provider: Optional[str] = None
    block_number: Optional[int] = None
    evm_version: Optional[str] = None


class FoundryNetworkConfig(PluginConfig):
    host: Optional[Union[str, Literal["auto"]]] = None
    """The host address or ``"auto"`` to use localhost with a random port (with attempts)."""

    manage_process: bool = True
    """
    If ``True`` and the host is local and Anvil is not running, will attempt to start.
    Defaults to ``True``. If ``host`` is remote, will not be able to start.
    """

    evm_version: Optional[str] = None
    """The EVM hardfork to use, e.g. `shanghai`."""

    # Retry strategy configs, try increasing these if you're getting FoundrySubprocessError
    request_timeout: int = 30
    fork_request_timeout: int = 300
    process_attempts: int = 5

    # RPC defaults
    base_fee: int = 0
    priority_fee: int = 0
    gas_price: int = 0

    # For setting the values in --fork and --fork-block-number command arguments.
    # Used only in FoundryForkProvider.
    # Mapping of ecosystem_name => network_name => FoundryForkConfig
    fork: dict[str, dict[str, FoundryForkConfig]] = {}

    disable_block_gas_limit: bool = False
    """
    Disable the ``call.gas_limit <= block.gas_limit`` constraint.
    """

    auto_mine: bool = True
    """
    Automatically mine blocks instead of manually doing so.
    """

    block_time: Optional[int] = None
    """
    Set a block time to allow mining to happen on an interval
    rather than only when a new transaction is submitted.
    """

    model_config = SettingsConfigDict(extra="allow")

    @field_validator("fork", mode="before")
    @classmethod
    def _validate_fork(cls, value):
        return value or {}


def _call(*args):
    return call([*args], stderr=PIPE, stdout=PIPE, stdin=PIPE)


class FoundryProvider(SubprocessProvider, Web3Provider, TestProviderAPI):
    _host: Optional[str] = None
    attempted_ports: list[int] = []
    cached_chain_id: Optional[int] = None
    _did_warn_wrong_node = False

    @property
    def unlocked_accounts(self) -> list[AddressType]:
        return list(self.account_manager.test_accounts._impersonated_accounts)

    @property
    def mnemonic(self) -> str:
        return self._test_config.mnemonic

    @property
    def number_of_accounts(self) -> int:
        return self._test_config.number_of_accounts

    @property
    def initial_balance(self) -> int:
        """
        Have to convert the WEI value to ETH, like Anvil expects.
        """
        bal_in_wei = self._test_config.balance
        return bal_in_wei // 10**18

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
    def is_connected(self) -> bool:
        if self._host in ("auto", None):
            # Hasn't tried yet.
            return False

        self._set_web3()
        return self._web3 is not None

    @property
    def gas_price(self) -> int:
        if self.process is not None:
            # NOTE: Workaround for bug where RPC does not honor CLI flag.
            return self.settings.gas_price

        # Not managing node so must use RPC.
        return self.web3.eth.gas_price

    @cached_property
    def _test_config(self) -> ApeTestConfig:
        return cast(ApeTestConfig, self.config_manager.get_config("test"))

    @property
    def auto_mine(self) -> bool:
        return self.make_request("anvil_getAutomine", [])

    @auto_mine.setter
    def auto_mine(self, value) -> None:
        self.make_request("anvil_setAutomine", [value])

    @property
    def evm_version(self) -> Optional[str]:
        return self.settings.evm_version

    @property
    def settings(self) -> FoundryNetworkConfig:
        return cast(FoundryNetworkConfig, super().settings)

    def connect(self):
        """
        Start the foundry process and verify it's up and accepting connections.
        **NOTE**: Must set port before calling 'super().connect()'.
        """

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

    def build_command(self) -> list[str]:
        cmd = [
            self.anvil_bin,
            "--port",
            f"{self._port or DEFAULT_PORT}",
            "--mnemonic",
            self.mnemonic,
            "--accounts",
            f"{self.number_of_accounts}",
            "--derivation-path",
            f"{self.test_config.hd_path}",
            "--balance",
            f"{self.initial_balance}",
            "--steps-tracing",
            "--block-base-fee-per-gas",
            f"{self.settings.base_fee}",
            "--gas-price",
            f"{self.settings.gas_price}",
        ]

        if not self.settings.auto_mine:
            cmd.append("--no-mining")

        if self.settings.block_time is not None:
            cmd.extend(("--block-time", f"{self.settings.block_time}"))

        if self.settings.disable_block_gas_limit:
            cmd.append("--disable-block-gas-limit")

        if evm_version := self.evm_version:
            cmd.extend(("--hardfork", evm_version))

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

        self.make_request("anvil_setBalance", [account, amount_hex_str])

    def set_timestamp(self, new_timestamp: int):
        self.make_request("evm_setNextBlockTimestamp", [new_timestamp])

    def mine(self, num_blocks: int = 1):
        # NOTE: Request fails when given numbers with any left padded 0s.
        num_blocks_arg = f"0x{HexBytes(num_blocks).hex().replace('0x', '').lstrip('0')}"
        self.make_request("anvil_mine", [num_blocks_arg])

    def snapshot(self) -> str:
        return self.make_request("evm_snapshot", [])

    def restore(self, snapshot_id: SnapshotID) -> bool:
        if isinstance(snapshot_id, int):
            snapshot_id = HexBytes(snapshot_id).hex()

        result = self.make_request("evm_revert", [snapshot_id])
        return result is True

    def unlock_account(self, address: AddressType) -> bool:
        self.make_request("anvil_impersonateAccount", [address])
        return True

    def relock_account(self, address: AddressType):
        self.make_request("anvil_stopImpersonatingAccount", [address])
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

        vm_err = None
        if sender and sender in self.unlocked_accounts:
            # Allow for an unsigned transaction
            txn = self.prepare_transaction(txn)
            txn_dict = txn.model_dump(mode="json", by_alias=True)
            if isinstance(txn_dict.get("type"), int):
                txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

            tx_params = cast(TxParams, txn_dict)
            try:
                txn_hash = self.web3.eth.send_transaction(tx_params)
            except ValueError as err:
                raise self.get_virtual_machine_error(err, txn=txn) from err

        else:
            try:
                txn_hash = self.web3.eth.send_raw_transaction(txn.serialize_transaction())
            except ValueError as err:
                vm_err = self.get_virtual_machine_error(err, txn=txn)

                if "nonce too low" in str(vm_err):
                    # Add additional nonce information
                    new_err_msg = f"Nonce '{txn.nonce}' is too low"
                    vm_err = VirtualMachineError(
                        new_err_msg,
                        base_err=vm_err.base_err,
                        code=vm_err.code,
                        txn=txn,
                        source_traceback=vm_err.source_traceback,
                        trace=vm_err.trace,
                        contract_address=vm_err.contract_address,
                    )

                txn_hash = txn.txn_hash
                if txn.raise_on_revert:
                    raise vm_err from err

        receipt = self.get_receipt(
            txn_hash.hex(),
            required_confirmations=(
                txn.required_confirmations
                if txn.required_confirmations is not None
                else self.network.required_confirmations
            ),
        )
        if vm_err:
            receipt.error = vm_err

        if receipt.failed:
            txn_dict = receipt.transaction.model_dump(mode="json", by_alias=True)
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
                receipt.error = vm_err
                if txn.raise_on_revert:
                    raise vm_err from err

            if txn.raise_on_revert:
                # If we get here, for some reason the tx-replay did not produce
                # a VM error.
                receipt.raise_for_status()

        self.chain_manager.history.append(receipt)
        return receipt

    def get_balance(self, address: AddressType, block_id: Optional[BlockID] = None) -> int:
        if hasattr(address, "address"):
            address = address.address

        result = self.make_request("eth_getBalance", [address, block_id])
        if not result:
            raise FoundryProviderError(f"Failed to get balance for account '{address}'.")

        return int(result, 16) if isinstance(result, str) else result

    def get_transaction_trace(self, transaction_hash: str, **kwargs) -> TraceAPI:
        if "debug_trace_transaction_parameters" not in kwargs:
            kwargs["debug_trace_transaction_parameters"] = {
                "stepsTracing": True,
                "enableMemory": True,
            }
        if "call_trace_approach" not in kwargs:
            kwargs["call_trace_approach"] = TraceApproach.PARITY

        return _get_transaction_trace(transaction_hash, **kwargs)

    def get_virtual_machine_error(self, exception: Exception, **kwargs) -> VirtualMachineError:
        if not len(exception.args):
            return VirtualMachineError(base_err=exception, **kwargs)

        err_data = exception.args[0]

        if isinstance(err_data, dict):
            message = str(err_data.get("message", f"{err_data}"))
        elif isinstance(err_data, str):
            message = err_data
        elif msg := getattr(exception, "message", ""):
            message = msg
        else:
            message = ""

        if not message:
            return VirtualMachineError(base_err=exception, **kwargs)

        def _handle_execution_reverted(
            exception: Exception, revert_message: Optional[str] = None, **kwargs
        ):
            if revert_message in ("", "0x", None):
                revert_message = TransactionError.DEFAULT_MESSAGE

            sub_err = ContractLogicError(
                base_err=exception, revert_message=revert_message, **kwargs
            )
            enriched = self.compiler_manager.enrich_error(sub_err)

            # Show call trace if available
            if enriched.txn:
                # Unlikely scenario where a transaction is on the error even though a receipt
                # exists.
                if isinstance(enriched.txn, TransactionAPI) and enriched.txn.receipt:
                    enriched.txn.receipt.show_trace()
                elif isinstance(enriched.txn, ReceiptAPI):
                    enriched.txn.show_trace()

            return enriched

        # Handle `ContactLogicError` similarly to other providers in `ape`.
        # by stripping off the unnecessary prefix that foundry has on reverts.
        foundry_prefix = (
            "Error: VM Exception while processing transaction: reverted with reason string "
        )
        if message.startswith(foundry_prefix):
            message = message.replace(foundry_prefix, "").strip("'")
            return _handle_execution_reverted(exception, message, **kwargs)

        elif "Transaction reverted without a reason string" in message:
            return _handle_execution_reverted(exception, **kwargs)

        elif message.lower() == "execution reverted":
            message = TransactionError.DEFAULT_MESSAGE
            if isinstance(exception, Web3ContractLogicError) and (
                msg := self._extract_custom_error(**kwargs)
            ):
                exception.message = msg

            return _handle_execution_reverted(exception, revert_message=message, **kwargs)

        elif message == "Transaction ran out of gas" or "OutOfGas" in message:
            return OutOfGasError(base_err=exception, **kwargs)

        elif message.startswith("execution reverted: "):
            message = (
                message.replace("execution reverted: ", "").strip()
                or TransactionError.DEFAULT_MESSAGE
            )
            return _handle_execution_reverted(exception, revert_message=message, **kwargs)

        elif isinstance(exception, ContractCustomError):
            # Is raw hex (custom exception)
            message = TransactionError.DEFAULT_MESSAGE if message in ("", None, "0x") else message
            return _handle_execution_reverted(exception, revert_message=message, **kwargs)

        return VirtualMachineError(message, **kwargs)

    # Abstracted for easier testing conditions.
    def _extract_custom_error(self, **kwargs) -> str:
        # Check for custom error.
        trace = None
        if "trace" in kwargs:
            trace = kwargs["trace"]

        elif "txn" in kwargs:
            txn = kwargs["txn"]
            try:
                txn_hash = txn.txn_hash if isinstance(txn.txn_hash, str) else txn.txn_hash.hex()
                trace = self.get_transaction_trace(txn_hash)
            except Exception:
                pass

        if trace is not None and (revert_msg := trace.revert_message):
            return revert_msg

        return ""

    def set_block_gas_limit(self, gas_limit: int) -> bool:
        return self.make_request("evm_setBlockGasLimit", [hex(gas_limit)]) is True

    def set_code(self, address: AddressType, code: ContractCode) -> bool:
        if isinstance(code, bytes):
            code = code.hex()

        elif isinstance(code, str) and not is_0x_prefixed(code):
            code = add_0x_prefix(HexStr(code))

        elif not is_hex(code):
            raise ValueError(f"Value {code} is not convertible to hex")

        self.make_request("anvil_setCode", [address, code])
        return True

    def set_storage(self, address: AddressType, slot: int, value: HexBytes):
        self.make_request(
            "anvil_setStorageAt",
            [
                address,
                HashBytes32.__eth_pydantic_validate__(slot).hex(),
                HashBytes32.__eth_pydantic_validate__(value).hex(),
            ],
        )

    def _eth_call(self, arguments: list, raise_on_revert: bool = True) -> HexBytes:
        # Overridden to handle unique Foundry pickiness.
        txn_dict = copy(arguments[0])
        if isinstance(txn_dict.get("type"), int):
            txn_dict["type"] = HexBytes(txn_dict["type"]).hex()

        txn_dict.pop("chainId", None)
        arguments[0] = txn_dict
        return super()._eth_call(arguments, raise_on_revert=raise_on_revert)


class FoundryForkProvider(FoundryProvider):
    """
    A Foundry provider that uses ``--fork``, like:
    ``npx foundry node --fork <upstream-provider-url>``.

    Set the ``upstream_provider`` in the ``foundry.fork`` config
    section of your ``ape-config.yaml` file to specify which provider
    to use as your archive node.
    """

    @model_validator(mode="before")
    @classmethod
    def set_upstream_provider(cls, value):
        network = value["network"]
        adhoc_settings = value.get("provider_settings", {}).get("fork", {})
        ecosystem_name = network.ecosystem.name
        plugin_config = cls.config_manager.get_config(value["name"])
        config_settings = plugin_config.get("fork", {})

        def _get_upstream(data: dict) -> Optional[str]:
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

    @property
    def evm_version(self) -> Optional[str]:
        if evm_version := self._fork_config.evm_version:
            return evm_version

        return self.settings.evm_version

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
            self._fork_config.upstream_provider = upstream_name

        return self.forked_network.upstream_provider.name

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

    def build_command(self) -> list[str]:
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

        return cmd

    def reset_fork(self, block_number: Optional[int] = None):
        forking_params: dict[str, Union[str, int]] = {"jsonRpcUrl": self.fork_url}
        block_number = block_number if block_number is not None else self.fork_block_number
        if block_number is not None:
            forking_params["blockNumber"] = block_number

        # # Rest the fork
        result = self.make_request("anvil_reset", [{"forking": forking_params}])
        return result


def _get_transaction_trace(transaction_hash: str, **kwargs) -> TraceAPI:
    # Abstracted for testing purposes.
    return TransactionTrace(transaction_hash=transaction_hash, **kwargs)
