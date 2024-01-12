import os
import tempfile
from pathlib import Path

import pytest
from ape.api.accounts import ImpersonatedAccount
from ape.exceptions import ContractLogicError, TransactionError
from ape.types import CallTreeNode, TraceFrame
from ape_ethereum.transactions import TransactionStatusEnum, TransactionType
from eth_pydantic_types import HashBytes32
from eth_utils import to_int
from evm_trace import CallType
from hexbytes import HexBytes

from ape_foundry import FoundryProviderError
from ape_foundry.provider import FOUNDRY_CHAIN_ID

TEST_WALLET_ADDRESS = "0xD9b7fdb3FC0A0Aa3A507dCf0976bc23D49a9C7A3"


def test_instantiation(disconnected_provider, name):
    assert disconnected_provider.name == name


def test_connect_and_disconnect(disconnected_provider):
    # Use custom port to prevent connecting to a port used in another test.

    disconnected_provider._host = "http://127.0.0.1:8555"
    disconnected_provider.connect()

    try:
        assert disconnected_provider.is_connected
        assert disconnected_provider.chain_id == FOUNDRY_CHAIN_ID
    finally:
        disconnected_provider.disconnect()

    assert not disconnected_provider.is_connected
    assert disconnected_provider.process is None


def test_gas_price(connected_provider):
    gas_price = connected_provider.gas_price
    assert gas_price == 0


def test_uri_disconnected(disconnected_provider):
    assert disconnected_provider.uri == "http://127.0.0.1:8545"


def test_uri(connected_provider):
    assert connected_provider.uri in connected_provider.uri


def test_set_block_gas_limit(connected_provider):
    gas_limit = connected_provider.get_block("latest").gas_limit
    assert connected_provider.set_block_gas_limit(gas_limit) is True


def test_set_timestamp(connected_provider):
    start_time = connected_provider.get_block("pending").timestamp
    connected_provider.set_timestamp(start_time + 5)
    new_time = connected_provider.get_block("pending").timestamp

    # Adding 5 seconds but seconds can be weird so give it a 1 second margin.
    assert 4 <= new_time - start_time <= 6


def test_mine(connected_provider):
    block_num = connected_provider.get_block("latest").number
    connected_provider.mine(100)
    next_block_num = connected_provider.get_block("latest").number
    assert next_block_num > block_num


def test_revert_failure(connected_provider):
    assert connected_provider.revert(0xFFFF) is False


def test_get_balance(connected_provider, owner):
    assert connected_provider.get_balance(owner.address)


def test_snapshot_and_revert(connected_provider):
    snap = connected_provider.snapshot()

    block_1 = connected_provider.get_block("latest")
    connected_provider.mine()
    block_2 = connected_provider.get_block("latest")
    assert block_2.number > block_1.number
    assert block_1.hash != block_2.hash

    connected_provider.revert(snap)
    block_3 = connected_provider.get_block("latest")
    assert block_1.number == block_3.number
    assert block_1.hash == block_3.hash


def test_unlock_account(connected_provider, contract_a, accounts):
    actual = connected_provider.unlock_account(TEST_WALLET_ADDRESS)
    assert actual is True

    # Tell Anvil we no longer want this unlocked.
    connected_provider.relock_account(TEST_WALLET_ADDRESS)

    # Unlock using the more public API.
    acct = accounts[TEST_WALLET_ADDRESS]
    assert isinstance(acct, ImpersonatedAccount)

    # Ensure can transact.
    # NOTE: Using type 0 to avoid needing to set a balance.
    receipt_0 = contract_a.methodWithoutArguments(sender=acct, type=0)
    assert not receipt_0.failed


def test_get_transaction_trace(connected_provider, contract_instance, owner):
    receipt = contract_instance.setNumber(10, sender=owner)

    # Indirectly calls `connected_provider.get_transaction_trace()`
    frame_data = list(receipt.trace)
    assert frame_data
    for frame in frame_data:
        assert isinstance(frame, TraceFrame)


def test_get_call_tree(connected_provider, sender, receiver):
    transfer = sender.transfer(receiver, 1)
    call_tree = connected_provider.get_call_tree(transfer.txn_hash)
    assert isinstance(call_tree, CallTreeNode)
    assert call_tree.call_type == CallType.CALL.value
    assert repr(call_tree) == "0x70997970C51812dc3A010C7d01b50e0d17dc79C8.0x()"


def test_request_timeout(connected_provider, config):
    # Test value set in `ape-config.yaml`
    expected = 29
    actual = connected_provider.web3.provider._request_kwargs["timeout"]
    assert actual == expected

    # Test default behavior
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        with config.using_project(temp_dir):
            assert connected_provider.timeout == 30


def test_contract_interaction(connected_provider, owner, contract_instance, mocker):
    # Spy on the estimate_gas RPC method.
    estimate_gas_spy = mocker.spy(connected_provider.web3.eth, "estimate_gas")

    # Check what max gas is before transacting.
    max_gas = connected_provider.max_gas

    # Invoke a method from a contract via transacting.
    receipt = contract_instance.setNumber(102, sender=owner)

    # Verify values from the receipt.
    assert not receipt.failed
    assert receipt.receiver == contract_instance.address
    assert receipt.gas_used < receipt.gas_limit
    assert receipt.gas_limit == max_gas

    # Show contract state changed.
    assert contract_instance.myNumber() == 102

    # Verify the estimate gas RPC was not used (since we are using max_gas).
    assert estimate_gas_spy.call_count == 0


def test_revert(sender, contract_instance):
    # 'sender' is not the owner so it will revert (with a message)
    with pytest.raises(ContractLogicError, match="!authorized"):
        contract_instance.setNumber(6, sender=sender)


def test_contract_revert_no_message(owner, contract_instance):
    # The Contract raises empty revert when setting number to 5.
    with pytest.raises(ContractLogicError, match="Transaction failed."):
        contract_instance.setNumber(5, sender=owner)


def test_transaction_contract_as_sender(
    contract_instance, contract_container, connected_provider, owner
):
    # Set balance so test wouldn't normally fail from lack of funds
    sender = owner.deploy(contract_container)
    connected_provider.set_balance(sender.address, "1000 ETH")

    with pytest.raises(ContractLogicError, match="!authorized"):
        # Task failed successfully
        contract_instance.setNumber(10, sender=sender)


@pytest.mark.parametrize(
    "amount", ("50 ETH", int(50e18), "0x2b5e3af16b1880000", "50000000000000000000")
)
def test_set_balance(connected_provider, owner, convert, amount):
    connected_provider.set_balance(owner.address, amount)
    assert owner.balance == convert("50 ETH", int)


def test_set_code(connected_provider, contract_container, owner):
    contract = contract_container.deploy(sender=owner)
    provider = connected_provider
    code = provider.get_code(contract.address)
    assert type(code) is HexBytes
    assert provider.set_code(contract.address, "0x00") is True
    assert provider.get_code(contract.address) != code
    assert provider.set_code(contract.address, code) is True
    assert provider.get_code(contract.address) == code


def test_set_storage(connected_provider, contract_container, owner):
    contract = contract_container.deploy(sender=owner)
    assert to_int(connected_provider.get_storage(contract.address, "0x2b5e3af16b1880000")) == 0
    connected_provider.set_storage(contract.address, "0x2b5e3af16b1880000", "0x1")
    assert to_int(connected_provider.get_storage(contract.address, "0x2b5e3af16b1880000")) == 1


def test_return_value(connected_provider, contract_instance, owner):
    receipt = contract_instance.setAddress(owner.address, sender=owner)
    assert receipt.return_value == 123


def test_get_receipt(connected_provider, contract_instance, owner):
    receipt = contract_instance.setAddress(owner.address, sender=owner)
    actual = connected_provider.get_receipt(receipt.txn_hash)
    assert receipt.txn_hash == actual.txn_hash
    assert actual.receiver == contract_instance.address
    assert actual.sender == receipt.sender


def test_revert_error(error_contract, not_owner):
    """
    Test matching a revert custom Solidity error.
    """
    with pytest.raises(error_contract.Unauthorized):
        error_contract.withdraw(sender=not_owner)


def test_revert_error_using_impersonated_account(error_contract, accounts, connected_provider):
    """
    Show that when a failure occurs when a txn is sent by an impersonated
    account, that everything still works.
    """
    acct = accounts[TEST_WALLET_ADDRESS]
    acct.balance = "1000 ETH"
    with pytest.raises(error_contract.Unauthorized):
        error_contract.withdraw(sender=acct)


@pytest.mark.parametrize("host", ("https://example.com", "example.com"))
def test_host(temp_config, local_network, host):
    data = {"foundry": {"host": host}}
    with temp_config(data):
        provider = local_network.get_provider("foundry")
        assert provider.uri == "https://example.com"


def test_base_fee(connected_provider):
    assert connected_provider.base_fee == 0


def test_auto_mine(connected_provider):
    assert connected_provider.auto_mine is True
    connected_provider.auto_mine = False
    assert connected_provider.auto_mine is False
    connected_provider.auto_mine = True
    assert connected_provider.auto_mine is True


@pytest.mark.parametrize(
    "message",
    (
        "Error: VM Exception while processing transaction: reverted with reason string ",
        "Transaction reverted without a reason string",
        "execution reverted",
    ),
)
def test_get_virtual_machine_error_from_contract_logic_message_includes_base_err(
    message, connected_provider
):
    exception = Exception(message)
    actual = connected_provider.get_virtual_machine_error(exception)
    assert isinstance(actual, ContractLogicError)
    assert actual.base_err == exception


def test_no_mining(temp_config, local_network, connected_provider):
    assert "--no-mining" not in connected_provider.build_command()
    data = {"foundry": {"auto_mine": "false"}}
    with temp_config(data):
        provider = local_network.get_provider("foundry")
        cmd = provider.build_command()
        assert "--no-mining" in cmd


def test_block_time(temp_config, local_network, connected_provider):
    assert "--block-time" not in connected_provider.build_command()
    data = {"foundry": {"block_time": 10}}
    with temp_config(data):
        provider = local_network.get_provider("foundry")
        cmd = provider.build_command()
        assert "--block-time" in cmd
        assert "10" in cmd


def test_remote_host(temp_config, local_network, no_anvil_bin):
    data = {"foundry": {"host": "https://example.com"}}
    with temp_config(data):
        with pytest.raises(
            FoundryProviderError,
            match=r"Failed to connect to remote Anvil node at 'https://example.com'\.",
        ):
            with local_network.use_provider("foundry"):
                assert True


def test_remote_host_using_env_var(temp_config, local_network, no_anvil_bin):
    original = os.environ.get("APE_FOUNDRY_HOST")
    os.environ["APE_FOUNDRY_HOST"] = "https://example2.com"

    try:
        with pytest.raises(
            FoundryProviderError,
            match=r"Failed to connect to remote Anvil node at 'https://example2.com'\.",
        ):
            with local_network.use_provider("foundry") as provider:
                # It shouldn't actually get to the line below,
                # but in case it does, this is a helpful debug line.
                assert provider.uri == os.environ["APE_FOUNDRY_HOST"], "env var not setting."

    finally:
        if original is None:
            del os.environ["APE_FOUNDRY_HOST"]
        else:
            os.environ["APE_FOUNDRY_HOST"] = original


def test_send_transaction_when_no_error_and_receipt_fails(
    mocker, connected_provider, owner, vyper_contract_instance
):
    mock_web3 = mocker.MagicMock()
    mock_transaction = mocker.MagicMock()
    mock_transaction.required_confirmations = 0
    mock_transaction.sender = owner.address

    start_web3 = connected_provider._web3
    connected_provider._web3 = mock_web3

    try:
        # NOTE: Value is meaningless.
        tx_hash = HashBytes32.__eth_pydantic_validate__(123**36)

        # Sending tx "works" meaning no vm error.
        mock_web3.eth.send_raw_transaction.return_value = tx_hash

        # Getting a receipt "works", but you get a failed one.
        receipt_data = {
            "failed": True,
            "blockNumber": 0,
            "txnHash": tx_hash.hex(),
            "status": TransactionStatusEnum.FAILING.value,
            "sender": owner.address,
            "receiver": vyper_contract_instance.address,
            "input": b"",
            "gasUsed": 123,
            "gasLimit": 100,
        }
        mock_web3.eth.wait_for_transaction_receipt.return_value = receipt_data

        # Attempting to replay the tx does not produce any error.
        mock_web3.eth.call.return_value = HexBytes("")

        # Execute test.
        with pytest.raises(TransactionError):
            connected_provider.send_transaction(mock_transaction)

    finally:
        connected_provider._web3 = start_web3


@pytest.mark.parametrize("tx_type", TransactionType)
def test_prepare_tx_with_max_gas(tx_type, connected_provider, ethereum, owner):
    tx = ethereum.create_transaction(type=tx_type.value, sender=owner.address)
    tx.gas_limit = None  # Undo set from validator
    assert tx.gas_limit is None, "Test setup failed - couldn't clear tx gas limit."

    # NOTE: The local network by default uses max_gas.
    actual = connected_provider.prepare_transaction(tx)
    assert actual.gas_limit == connected_provider.max_gas
