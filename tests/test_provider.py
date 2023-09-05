import os
import tempfile
from pathlib import Path

import pytest
from ape.api.accounts import ImpersonatedAccount
from ape.exceptions import ContractLogicError
from ape.types import CallTreeNode, TraceFrame
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
    assert gas_price > 1


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
    receipt = contract_a.methodWithoutArguments(sender=acct)
    assert not receipt.failed


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
    assert repr(call_tree) == "0xc89D42189f0450C2b2c3c61f58Ec5d628176A1E7.0x()"


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


def test_send_transaction(contract_instance, owner):
    contract_instance.setNumber(10, sender=owner)
    assert contract_instance.myNumber() == 10


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
    assert to_int(connected_provider.get_storage_at(contract.address, "0x2b5e3af16b1880000")) == 0
    connected_provider.set_storage(contract.address, "0x2b5e3af16b1880000", "0x1")
    assert to_int(connected_provider.get_storage_at(contract.address, "0x2b5e3af16b1880000")) == 1


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
def test_host(temp_config, networks, host):
    data = {"foundry": {"host": host}}
    with temp_config(data):
        provider = networks.ethereum.local.get_provider("foundry")
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


def test_no_mining(temp_config, networks, connected_provider):
    assert "--no-mining" not in connected_provider.build_command()
    data = {"foundry": {"auto_mine": "false"}}
    with temp_config(data):
        provider = networks.ethereum.local.get_provider("foundry")
        cmd = provider.build_command()
        assert "--no-mining" in cmd


def test_block_time(temp_config, networks, connected_provider):
    assert "--block-time" not in connected_provider.build_command()
    data = {"foundry": {"block_time": 10}}
    with temp_config(data):
        provider = networks.ethereum.local.get_provider("foundry")
        cmd = provider.build_command()
        assert "--block-time" in cmd
        assert "10" in cmd


def test_remote_host(temp_config, networks, no_anvil_bin):
    data = {"foundry": {"host": "https://example.com"}}
    with temp_config(data):
        with pytest.raises(
            FoundryProviderError,
            match=r"Failed to connect to remote Anvil node at 'https://example.com'\.",
        ):
            with networks.ethereum.local.use_provider("foundry"):
                assert True


def test_remote_host_using_env_var(temp_config, networks, no_anvil_bin):
    original = os.environ.get("APE_FOUNDRY_HOST")
    os.environ["APE_FOUNDRY_HOST"] = "https://example2.com"
    try:
        with pytest.raises(
            FoundryProviderError,
            match=r"Failed to connect to remote Anvil node at 'https://example2.com'\.",
        ):
            with networks.ethereum.local.use_provider("foundry"):
                assert True

    finally:
        if original is None:
            del os.environ["APE_FOUNDRY_HOST"]
        else:
            os.environ["APE_FOUNDRY_HOST"] = original
