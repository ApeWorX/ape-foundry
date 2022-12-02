import re
import tempfile
from pathlib import Path

import pytest
from ape.exceptions import ContractLogicError, SignatureError
from evm_trace import CallTreeNode, CallType
from hexbytes import HexBytes

from ape_foundry.exceptions import FoundryProviderError
from ape_foundry.provider import FOUNDRY_CHAIN_ID, FoundryProvider

TEST_WALLET_ADDRESS = "0xD9b7fdb3FC0A0Aa3A507dCf0976bc23D49a9C7A3"


@pytest.fixture(scope="module")
def call_expression():
    return re.compile(r"CALL: 0x([a-f]|[A-F]|\d)*.<0x([a-f]|[A-F]|\d)*> \[\d* gas]")


def test_instantiation(disconnected_provider):
    assert disconnected_provider.name == "foundry"


def test_connect_and_disconnect(disconnected_provider):
    # Use custom port to prevent connecting to a port used in another test.

    disconnected_provider.port = 8555
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
    with pytest.raises(FoundryProviderError) as err:
        _ = disconnected_provider.uri

    assert "Can't build URI before `connect()` is called." in str(err.value)


def test_uri(connected_provider):
    expected_uri = f"http://127.0.0.1:{connected_provider.port}"
    assert expected_uri in connected_provider.uri


@pytest.mark.parametrize(
    "method,args,expected",
    [
        (FoundryProvider.get_nonce, [TEST_WALLET_ADDRESS], 0),
        (FoundryProvider.get_balance, [TEST_WALLET_ADDRESS], 0),
        (FoundryProvider.get_code, [TEST_WALLET_ADDRESS], HexBytes("")),
    ],
)
def test_rpc_methods(connected_provider, method, args, expected):
    assert method(connected_provider, *args) == expected


def test_set_block_gas_limit(connected_provider):
    gas_limit = connected_provider.get_block("latest").gas_limit
    assert connected_provider.set_block_gas_limit(gas_limit) is True


def test_set_timestamp(connected_provider):
    start_time = connected_provider.get_block("pending").timestamp
    connected_provider.set_timestamp(start_time + 5)  # Increase by 5 seconds
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
    assert connected_provider.get_balance(owner)


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


def test_unlock_account(connected_provider):
    actual = connected_provider.unlock_account(TEST_WALLET_ADDRESS)
    assert actual is True
    assert TEST_WALLET_ADDRESS in connected_provider.unlocked_accounts


def test_get_call_tree(connected_provider, sender, receiver):
    transfer = sender.transfer(receiver, 1)
    call_tree = connected_provider.get_call_tree(transfer.txn_hash)
    assert isinstance(call_tree, CallTreeNode)
    assert call_tree.call_type == CallType.CALL
    assert repr(call_tree) == "CALL: 0xc89D42189f0450C2b2c3c61f58Ec5d628176A1E7 [0 gas]"


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

    # Have to be in the same test because of X-dist complications
    with pytest.raises(SignatureError):
        contract_instance.setNumber(20)


def test_revert(sender, contract_instance):
    # 'sender' is not the owner so it will revert (with a message)
    with pytest.raises(ContractLogicError) as err:
        contract_instance.setNumber(6, sender=sender)

    assert str(err.value) == "!authorized"


def test_contract_revert_no_message(owner, contract_instance):
    # The Contract raises empty revert when setting number to 5.
    with pytest.raises(ContractLogicError) as err:
        contract_instance.setNumber(5, sender=owner)

    assert str(err.value) == "Transaction failed."


def test_transaction_contract_as_sender(contract_instance, connected_provider):
    # Set balance so test wouldn't normally fail from lack of funds
    connected_provider.set_balance(contract_instance.address, "1000 ETH")
    receipt = contract_instance.setNumber(10, sender=contract_instance)
    assert receipt


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
    assert type(code) == HexBytes
    assert provider.set_code(contract.address, "0x00") is True
    assert provider.get_code(contract.address) != code
    assert provider.set_code(contract.address, code) is True
    assert provider.get_code(contract.address) == code


def test_return_value(connected_provider, contract_instance, owner):
    receipt = contract_instance.setAddress(owner.address, sender=owner)
    assert receipt.return_value == 123


def test_get_receipt(connected_provider, contract_instance, owner):
    receipt = contract_instance.setAddress(owner.address, sender=owner)
    actual = connected_provider.get_receipt(receipt.txn_hash)
    assert receipt.txn_hash == actual.txn_hash
    assert actual.receiver == contract_instance.address
    assert actual.sender == receipt.sender
