import time

import pytest
from hexbytes import HexBytes

from ape_foundry.exceptions import FoundryProviderError
from ape_foundry.providers import FOUNDRY_CHAIN_ID, FoundryProvider
from tests.conftest import get_foundry_provider

TEST_WALLET_ADDRESS = "0xD9b7fdb3FC0A0Aa3A507dCf0976bc23D49a9C7A3"


def test_instantiation(foundry_disconnected):
    assert foundry_disconnected.name == "foundry"


def test_connect_and_disconnect(network_api):
    # Use custom port to prevent connecting to a port used in another test.

    foundry = get_foundry_provider(network_api)
    foundry.port = 8555
    foundry.connect()

    try:
        assert foundry.is_connected
        assert foundry.chain_id == FOUNDRY_CHAIN_ID
    finally:
        foundry.disconnect()

    assert not foundry.is_connected
    assert foundry.process is None


def test_gas_price(foundry_connected):
    gas_price = foundry_connected.gas_price
    assert gas_price > 1


def test_uri_disconnected(foundry_disconnected):
    with pytest.raises(FoundryProviderError) as err:
        _ = foundry_disconnected.uri

    assert "Can't build URI before `connect()` is called." in str(err.value)


def test_uri(foundry_connected):
    expected_uri = f"http://127.0.0.1:{foundry_connected.port}"
    assert expected_uri in foundry_connected.uri


@pytest.mark.parametrize(
    "method,args,expected",
    [
        (FoundryProvider.get_nonce, [TEST_WALLET_ADDRESS], 0),
        (FoundryProvider.get_balance, [TEST_WALLET_ADDRESS], 0),
        (FoundryProvider.get_code, [TEST_WALLET_ADDRESS], HexBytes("")),
    ],
)
def test_rpc_methods(foundry_connected, method, args, expected):
    assert method(foundry_connected, *args) == expected


def test_multiple_instances(network_api):
    """
    Validate the somewhat tricky internal logic of running multiple Foundry subprocesses
    under a single parent process.
    """
    # instantiate the providers (which will start the subprocesses) and validate the ports
    provider_1 = get_foundry_provider(network_api)
    provider_1.port = 8556
    provider_1.connect()

    # NOTE: Sleep because Foundry is fast and we want the chains to have different hashes
    time.sleep(1)

    provider_2 = get_foundry_provider(network_api)
    provider_2.port = 8557
    provider_2.connect()
    time.sleep(1)

    provider_3 = get_foundry_provider(network_api)
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


@pytest.mark.xfail(
    reason="Waiting for https://github.com/foundry-rs/foundry/issues/1511 to be resolved"
)
def test_set_timestamp(foundry_connected):
    start_time = foundry_connected.get_block("pending").timestamp
    foundry_connected.set_timestamp(start_time + 5)  # Increase by 5 seconds
    new_time = foundry_connected.get_block("pending").timestamp

    # Adding 5 seconds but seconds can be weird so give it a 1 second margin.
    assert 4 <= new_time - start_time <= 6


def test_mine(foundry_connected):
    block_num = foundry_connected.get_block("latest").number
    foundry_connected.mine()
    next_block_num = foundry_connected.get_block("latest").number
    assert next_block_num > block_num


def test_revert_failure(foundry_connected):
    assert foundry_connected.revert(0xFFFF) is False


def test_snapshot_and_revert(foundry_connected):
    snap = foundry_connected.snapshot()

    block_1 = foundry_connected.get_block("latest")
    foundry_connected.mine()
    block_2 = foundry_connected.get_block("latest")
    assert block_2.number > block_1.number
    assert block_1.hash != block_2.hash

    foundry_connected.revert(snap)
    block_3 = foundry_connected.get_block("latest")
    assert block_1.number == block_3.number
    assert block_1.hash == block_3.hash


def test_unlock_account(foundry_connected):
    actual = foundry_connected.unlock_account(TEST_WALLET_ADDRESS)
    assert actual is True
    assert TEST_WALLET_ADDRESS in foundry_connected.unlocked_accounts
