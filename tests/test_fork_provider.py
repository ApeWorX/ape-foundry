import tempfile
from pathlib import Path

import ape
import pytest
from ape.exceptions import ContractLogicError
from ape_ethereum.ecosystem import NETWORKS

TESTS_DIRECTORY = Path(__file__).parent
TEST_ADDRESS = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture(scope="module")
def connected_mainnet_fork_provider():
    with ape.networks.parse_network_choice("ethereum:mainnet-fork:foundry") as provider:
        yield provider


@pytest.fixture
def fork_contract_instance(owner, contract_container, connected_mainnet_fork_provider):
    return owner.deploy(contract_container)


@pytest.mark.parametrize("network", [k for k in NETWORKS.keys()])
def test_fork_config(config, network):
    plugin_config = config.get_config("foundry")
    network_config = plugin_config["fork"].get("ethereum", {}).get(network, {})
    assert network_config.get("upstream_provider") == "alchemy", "config not registered"


@pytest.mark.fork
@pytest.mark.parametrize("upstream_network,port", [("mainnet", 8998), ("goerli", 8999)])
def test_impersonate(networks, accounts, upstream_network, port, create_fork_provider):
    provider = create_fork_provider(port=port, network=upstream_network)
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
def test_request_timeout(networks, config, create_fork_provider):
    provider = create_fork_provider(9008)
    provider.connect()
    actual = provider.web3.provider._request_kwargs["timeout"]
    expected = 360  # Value set in `ape-config.yaml`
    assert actual == expected
    provider.disconnect()

    # Test default behavior
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        with config.using_project(temp_dir):
            provider = create_fork_provider(9011)
            assert provider.timeout == 300


@pytest.mark.fork
def test_reset_fork_no_fork_block_number(networks, create_fork_provider):
    provider = create_fork_provider(port=9013, network="goerli")
    provider.connect()
    provider.mine(5)
    prev_block_num = provider.get_block("latest").number
    provider.reset_fork()
    block_num_after_reset = provider.get_block("latest").number
    assert block_num_after_reset < prev_block_num
    provider.disconnect()


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_argument(networks, create_fork_provider):
    provider = create_fork_provider(port=9020, network="goerli")
    provider.connect()
    provider.mine(5)
    prev_block_num = provider.get_block("latest").number
    new_block_number = prev_block_num - 1
    provider.reset_fork(block_number=new_block_number)
    block_num_after_reset = provider.get_block("latest").number
    assert block_num_after_reset == new_block_number
    provider.disconnect()


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_config(networks, create_fork_provider):
    provider = create_fork_provider(port=9030)
    provider.connect()
    provider.mine(5)
    provider.reset_fork()
    block_num_after_reset = provider.get_block("latest").number
    assert block_num_after_reset == 15776634  # Specified in ape-config.yaml
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
    with pytest.raises(ContractLogicError, match="!authorized"):
        fork_contract_instance.setNumber(6, sender=sender)


@pytest.mark.fork
def test_contract_revert_no_message(owner, fork_contract_instance, connected_mainnet_fork_provider):
    # Set balance so test wouldn't normally fail from lack of funds
    connected_mainnet_fork_provider.set_balance(fork_contract_instance.address, "1000 ETH")

    # The Contract raises empty revert when setting number to 5.
    with pytest.raises(ContractLogicError, match="Transaction failed."):
        fork_contract_instance.setNumber(5, sender=owner)


@pytest.mark.fork
def test_transaction_contract_as_sender(
    fork_contract_instance, connected_mainnet_fork_provider, convert
):
    # Set balance so test wouldn't normally fail from lack of funds
    connected_mainnet_fork_provider.set_balance(fork_contract_instance.address, "1000 ETH")
    fork_contract_instance.setNumber(10, sender=fork_contract_instance)


@pytest.mark.fork
def test_transaction_unknown_contract_as_sender(accounts, networks, create_fork_provider):
    provider = create_fork_provider(9012)
    provider.connect()
    account = "0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"
    init_provider = networks.active_provider
    networks.active_provider = provider
    multi_sig = accounts[account]
    multi_sig.transfer(accounts[0], "100 gwei")
    networks.active_provider = init_provider


@pytest.mark.fork
def test_get_receipt(connected_mainnet_fork_provider, fork_contract_instance, owner):
    receipt = fork_contract_instance.setAddress(owner.address, sender=owner)
    actual = connected_mainnet_fork_provider.get_receipt(receipt.txn_hash)
    assert receipt.txn_hash == actual.txn_hash
    assert actual.receiver == fork_contract_instance.address
    assert actual.sender == receipt.sender
