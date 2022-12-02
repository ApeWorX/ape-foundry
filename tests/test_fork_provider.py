import tempfile
from pathlib import Path

import pytest
from ape.exceptions import ContractLogicError
from ape_ethereum.ecosystem import NETWORKS

TESTS_DIRECTORY = Path(__file__).parent
TEST_ADDRESS = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture
def mainnet_fork_contract_instance(owner, contract_container, mainnet_fork_provider):
    return owner.deploy(contract_container)


@pytest.mark.fork
def test_multiple_providers(networks, connected_provider, mainnet_fork_port, goerli_fork_port):
    assert networks.active_provider.name == "foundry"
    assert networks.active_provider.network.name == "local"
    assert networks.active_provider.port == 8545

    with networks.ethereum.mainnet_fork.use_provider(
        "foundry", provider_settings={"port": mainnet_fork_port}
    ):
        assert networks.active_provider.name == "foundry"
        assert networks.active_provider.network.name == "mainnet-fork"
        assert networks.active_provider.port == mainnet_fork_port

        with networks.ethereum.goerli_fork.use_provider(
            "foundry", provider_settings={"port": goerli_fork_port}
        ):
            assert networks.active_provider.name == "foundry"
            assert networks.active_provider.network.name == "goerli-fork"
            assert networks.active_provider.port == goerli_fork_port

        assert networks.active_provider.name == "foundry"
        assert networks.active_provider.network.name == "mainnet-fork"
        assert networks.active_provider.port == mainnet_fork_port

    assert networks.active_provider.name == "foundry"
    assert networks.active_provider.network.name == "local"
    assert networks.active_provider.port == 8545


@pytest.mark.parametrize("network", [k for k in NETWORKS.keys()])
def test_fork_config(config, network):
    plugin_config = config.get_config("foundry")
    network_config = plugin_config["fork"].get("ethereum", {}).get(network, {})
    assert network_config.get("upstream_provider") == "alchemy", "config not registered"


@pytest.mark.fork
def test_goerli_impersonate(accounts, goerli_fork_provider):
    impersonated_account = accounts[TEST_ADDRESS]
    other_account = accounts[0]
    receipt = impersonated_account.transfer(other_account, "1 wei")
    assert receipt.receiver == other_account
    assert receipt.sender == impersonated_account


@pytest.mark.fork
def test_mainnet_impersonate(accounts, mainnet_fork_provider):
    impersonated_account = accounts[TEST_ADDRESS]
    other_account = accounts[0]
    receipt = impersonated_account.transfer(other_account, "1 wei")
    assert receipt.receiver == other_account
    assert receipt.sender == impersonated_account


@pytest.mark.fork
def test_request_timeout(networks, config, mainnet_fork_provider):
    actual = mainnet_fork_provider.web3.provider._request_kwargs["timeout"]
    expected = 360  # Value set in `ape-config.yaml`
    assert actual == expected

    # Test default behavior
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        with config.using_project(temp_dir):
            assert networks.active_provider.timeout == 300


@pytest.mark.fork
def test_reset_fork_no_fork_block_number(networks, goerli_fork_provider):
    goerli_fork_provider.mine(5)
    prev_block_num = goerli_fork_provider.get_block("latest").number
    goerli_fork_provider.reset_fork()
    block_num_after_reset = goerli_fork_provider.get_block("latest").number
    assert block_num_after_reset < prev_block_num


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_argument(networks, goerli_fork_provider):
    goerli_fork_provider.mine(5)
    prev_block_num = goerli_fork_provider.get_block("latest").number
    new_block_number = prev_block_num - 1
    goerli_fork_provider.reset_fork(block_number=new_block_number)
    block_num_after_reset = goerli_fork_provider.get_block("latest").number
    assert block_num_after_reset == new_block_number


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_config(networks, mainnet_fork_provider):
    mainnet_fork_provider.mine(5)
    mainnet_fork_provider.reset_fork()
    block_num_after_reset = mainnet_fork_provider.get_block("latest").number
    assert block_num_after_reset == 15776634  # Specified in ape-config.yaml


@pytest.mark.fork
def test_transaction(owner, mainnet_fork_contract_instance):
    receipt = mainnet_fork_contract_instance.setNumber(6, sender=owner)
    assert receipt.sender == owner

    value = mainnet_fork_contract_instance.myNumber()
    assert value == 6


@pytest.mark.fork
def test_revert(sender, mainnet_fork_contract_instance):
    # 'sender' is not the owner so it will revert (with a message)
    with pytest.raises(ContractLogicError, match="!authorized"):
        mainnet_fork_contract_instance.setNumber(6, sender=sender)


@pytest.mark.fork
def test_contract_revert_no_message(owner, mainnet_fork_contract_instance, mainnet_fork_provider):
    # Set balance so test wouldn't normally fail from lack of funds
    mainnet_fork_provider.set_balance(mainnet_fork_contract_instance.address, "1000 ETH")

    # The Contract raises empty revert when setting number to 5.
    with pytest.raises(ContractLogicError, match="Transaction failed."):
        mainnet_fork_contract_instance.setNumber(5, sender=owner)


@pytest.mark.fork
def test_transaction_contract_as_sender(
    mainnet_fork_contract_instance, mainnet_fork_provider, convert
):
    # Set balance so test wouldn't normally fail from lack of funds
    mainnet_fork_provider.set_balance(mainnet_fork_contract_instance.address, "1000 ETH")
    mainnet_fork_contract_instance.setNumber(10, sender=mainnet_fork_contract_instance)


@pytest.mark.fork
def test_transaction_unknown_contract_as_sender(accounts, networks, mainnet_fork_provider):
    account = "0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"
    multi_sig = accounts[account]
    receipt = multi_sig.transfer(accounts[0], "100 gwei")
    assert not receipt.failed


@pytest.mark.fork
def test_get_receipt(mainnet_fork_provider, mainnet_fork_contract_instance, owner):
    receipt = mainnet_fork_contract_instance.setAddress(owner.address, sender=owner)
    actual = mainnet_fork_provider.get_receipt(receipt.txn_hash)
    assert receipt.txn_hash == actual.txn_hash
    assert actual.receiver == mainnet_fork_contract_instance.address
    assert actual.sender == receipt.sender
