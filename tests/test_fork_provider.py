import tempfile
from pathlib import Path

import pytest
from ape.exceptions import ContractLogicError
from ape_ethereum.ecosystem import NETWORKS

from ape_foundry.providers import FoundryForkProvider

TESTS_DIRECTORY = Path(__file__).parent
TEST_ADDRESS = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture(scope="module")
def mainnet_fork_network_api(networks):
    return networks.ecosystems["ethereum"]["mainnet-fork"]


@pytest.fixture(scope="module")
def connected_mainnet_fork_provider(networks, mainnet_fork_network_api):
    provider = create_fork_provider(mainnet_fork_network_api)
    provider.connect()
    networks.active_provider = provider
    yield provider
    provider.disconnect()
    networks.active_provider = None


@pytest.fixture(scope="module")
def fork_contract_instance(owner, contract_container, connected_mainnet_fork_provider):
    return owner.deploy(contract_container)


def create_fork_provider(network_api, port=9001):
    provider = FoundryForkProvider(
        name="foundry",
        network=network_api,
        request_header={},
        data_folder=Path("."),
        provider_settings={},
    )
    provider.port = port
    return provider


@pytest.mark.parametrize("network", [k for k in NETWORKS.keys()])
def test_fork_config(config, network):
    plugin_config = config.get_config("foundry")
    network_config = plugin_config["fork"].get("ethereum", {}).get(network, {})
    assert network_config["upstream_provider"] == "alchemy", "config not registered"


@pytest.mark.fork
@pytest.mark.parametrize("upstream,port", [("mainnet", 8998), ("rinkeby", 8999)])
def test_impersonate(networks, accounts, upstream, port):
    network_api = networks.ecosystems["ethereum"][f"{upstream}-fork"]
    provider = create_fork_provider(network_api, port)
    provider.connect()
    orig_provider = networks.active_provider
    networks.active_provider = provider

    impersonated_account = accounts[TEST_ADDRESS]
    other_account = accounts[0]
    receipt = impersonated_account.transfer(other_account, "1 wei")
    assert receipt.receiver == other_account
    assert receipt.sender == impersonated_account

    provider.disconnect()
    networks.active_provider = orig_provider


@pytest.mark.fork
def test_request_timeout(networks, config, mainnet_fork_network_api):
    provider = create_fork_provider(mainnet_fork_network_api, 9008)
    provider.connect()
    actual = provider.web3.provider._request_kwargs["timeout"]  # type: ignore
    expected = 360  # Value set in `ape-config.yaml`
    assert actual == expected
    provider.disconnect()

    # Test default behavior
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        with config.using_project(temp_dir):
            provider = create_fork_provider(mainnet_fork_network_api, 9011)
            assert provider.timeout == 300


@pytest.mark.fork
def test_reset_fork(networks, mainnet_fork_network_api):
    provider = create_fork_provider(mainnet_fork_network_api, 9010)
    provider.connect()
    provider.mine()
    prev_block_num = provider.get_block("latest").number
    provider.reset_fork()
    block_num_after_reset = provider.get_block("latest").number
    assert block_num_after_reset < prev_block_num
    provider.disconnect()


@pytest.mark.fork
def test_transaction(owner, fork_contract_instance):
    receipt = fork_contract_instance.setNumber(6, sender=owner)
    assert receipt.sender == owner

    value = fork_contract_instance.myNumber()
    assert value == 6


@pytest.mark.fork
def test_revert(sender, fork_contract_instance):
    # 'sender' is not the owner so it will revert (with a message)
    with pytest.raises(ContractLogicError) as err:
        fork_contract_instance.setNumber(6, sender=sender)

    assert str(err.value) == "!authorized"


@pytest.mark.fork
def test_contract_revert_no_message(owner, fork_contract_instance):
    # The Contract raises empty revert when setting number to 5.
    with pytest.raises(ContractLogicError) as err:
        fork_contract_instance.setNumber(5, sender=owner)

    assert str(err.value) == "Transaction failed."


@pytest.mark.fork
def test_transaction_contract_as_sender(fork_contract_instance):
    with pytest.raises(ContractLogicError) as err:
        # Task failed successfully
        fork_contract_instance.setNumber(10, sender=fork_contract_instance)

    assert str(err.value) == "!authorized"


@pytest.mark.fork
def test_transaction_unknown_contract_as_sender(accounts, networks, mainnet_fork_network_api):
    provider = create_fork_provider(mainnet_fork_network_api, 9012)
    provider.connect()
    init_provider = networks.active_provider
    networks.active_provider = provider
    multi_sig = accounts["0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"]
    multi_sig.transfer(accounts[0], "100 gwei")
    networks.active_provider = init_provider
