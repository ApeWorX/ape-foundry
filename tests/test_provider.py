import re
import tempfile
import time
from pathlib import Path

import pytest
from ape.exceptions import ContractLogicError, SignatureError
from hexbytes import HexBytes

from ape_foundry.exceptions import FoundryProviderError
from ape_foundry.providers import FOUNDRY_CHAIN_ID, FoundryProvider

TEST_WALLET_ADDRESS = "0xD9b7fdb3FC0A0Aa3A507dCf0976bc23D49a9C7A3"


@pytest.fixture(scope="module")
def call_expression():
    return re.compile(r"CALL: 0x([a-f]|[A-F]|\d)*.<0x([a-f]|[A-F]|\d)*> \[\d* gas]")


def test_instantiation(disconnected_provider):
    assert disconnected_provider.name == "foundry"


def test_connect_and_disconnect(create_provider):
    # Use custom port to prevent connecting to a port used in another test.

    foundry = create_provider()
    foundry.port = 8555
    foundry.connect()

    try:
        assert foundry.is_connected
        assert foundry.chain_id == FOUNDRY_CHAIN_ID
    finally:
        foundry.disconnect()

    assert not foundry.is_connected
    assert foundry.process is None


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


def test_multiple_instances(create_provider):
    """
    Validate the somewhat tricky internal logic of running multiple Foundry subprocesses
    under a single parent process.
    """
    # instantiate the providers (which will start the subprocesses) and validate the ports
    provider_1 = create_provider()
    provider_1.port = 8556
    provider_1.connect()

    # NOTE: Sleep because Foundry is fast and we want the chains to have different hashes
    time.sleep(1)

    provider_2 = create_provider()
    provider_2.port = 8557
    provider_2.connect()
    time.sleep(1)

    provider_3 = create_provider()
    provider_3.port = 8558
    provider_3.connect()
    time.sleep(1)

    # The web3 clients must be different in the provider instances (compared to the
    # behavior of the EthereumProvider base class, where it's a shared classvar)
    assert provider_1._web3 != provider_2._web3 != provider_3._web3

    assert provider_1.port == 8556
    assert provider_2.port == 8557
    assert provider_3.port == 8558

    provider_1.mine()
    provider_2.mine()
    provider_3.mine()
    hash_1 = provider_1.get_block("latest").hash
    hash_2 = provider_2.get_block("latest").hash
    hash_3 = provider_3.get_block("latest").hash
    assert hash_1 != hash_2 != hash_3


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


def test_request_timeout(connected_provider, config, create_provider):
    actual = connected_provider.web3.provider._request_kwargs["timeout"]  # type: ignore
    expected = 29  # Value set in `ape-config.yaml`
    assert actual == expected

    # Test default behavior
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        with config.using_project(temp_dir):
            provider = create_provider()
            assert provider.timeout == 30


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


def test_get_call_tree(receipt, connected_provider, call_expression):
    actual = connected_provider.get_call_tree(receipt.txn_hash)
    assert call_expression.match(repr(actual))
