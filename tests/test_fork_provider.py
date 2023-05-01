import tempfile
from pathlib import Path

import pytest
from ape.api.networks import LOCAL_NETWORK_NAME
from ape.contracts import ContractInstance
from ape.exceptions import ContractLogicError
from ape_ethereum.ecosystem import NETWORKS

TESTS_DIRECTORY = Path(__file__).parent
TEST_ADDRESS = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture
def mainnet_fork_contract_instance(owner, contract_container, mainnet_fork_provider):
    return owner.deploy(contract_container)


@pytest.mark.fork
def test_multiple_providers(
    name, networks, connected_provider, mainnet_fork_port, goerli_fork_port
):
    default_host = "http://127.0.0.1:8545"
    assert networks.active_provider.name == name
    assert networks.active_provider.network.name == LOCAL_NETWORK_NAME
    assert networks.active_provider.uri == default_host
    mainnet_fork_host = f"http://127.0.0.1:{mainnet_fork_port}"

    with networks.ethereum.mainnet_fork.use_provider(
        name, provider_settings={"host": mainnet_fork_host}
    ):
        assert networks.active_provider.name == name
        assert networks.active_provider.network.name == "mainnet-fork"
        assert networks.active_provider.uri == mainnet_fork_host
        goerli_fork_host = f"http://127.0.0.1:{goerli_fork_port}"

        with networks.ethereum.goerli_fork.use_provider(
            name, provider_settings={"host": goerli_fork_host}
        ):
            assert networks.active_provider.name == name
            assert networks.active_provider.network.name == "goerli-fork"
            assert networks.active_provider.uri == goerli_fork_host

        assert networks.active_provider.name == name
        assert networks.active_provider.network.name == "mainnet-fork"
        assert networks.active_provider.uri == mainnet_fork_host

    assert networks.active_provider.name == name
    assert networks.active_provider.network.name == LOCAL_NETWORK_NAME
    assert networks.active_provider.uri == default_host


@pytest.mark.parametrize("network", [k for k in NETWORKS.keys()])
def test_fork_config(name, config, network):
    plugin_config = config.get_config(name)
    network_config = plugin_config["fork"].get("ethereum", {}).get(network, {})
    message = f"Config not registered for network '{network}'."
    assert network_config.get("upstream_provider") == "alchemy", message


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
def test_reset_fork_no_fork_block_number(goerli_fork_provider):
    goerli_fork_provider.mine(5)
    prev_block_num = goerli_fork_provider.get_block("latest").number
    goerli_fork_provider.reset_fork()
    block_num_after_reset = goerli_fork_provider.get_block("latest").number
    assert block_num_after_reset < prev_block_num


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_argument(goerli_fork_provider):
    goerli_fork_provider.mine(5)
    prev_block_num = goerli_fork_provider.get_block("latest").number
    new_block_number = prev_block_num - 1
    goerli_fork_provider.reset_fork(block_number=new_block_number)
    block_num_after_reset = goerli_fork_provider.get_block("latest").number
    assert block_num_after_reset == new_block_number


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_config(mainnet_fork_provider):
    mainnet_fork_provider.mine(5)
    mainnet_fork_provider.reset_fork()
    block_num_after_reset = mainnet_fork_provider.get_block("latest").number
    block_base_fee_after_reset = mainnet_fork_provider.get_block("latest").base_fee
    assert block_num_after_reset == 15776634  # Specified in ape-config.yaml
    assert block_base_fee_after_reset == 28831496753


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
    # The Contract raises empty revert when setting number to 5.
    with pytest.raises(ContractLogicError, match="Transaction failed."):
        mainnet_fork_contract_instance.setNumber(5, sender=owner)


@pytest.mark.fork
def test_transaction_contract_as_sender(
    mainnet_fork_contract_instance, mainnet_fork_provider, convert
):
    # Set balance so test wouldn't normally fail from lack of funds
    mainnet_fork_provider.set_balance(mainnet_fork_contract_instance.address, "1000 ETH")
    with pytest.raises(ContractLogicError, match="!authorized"):
        # NOTE: For some reason, this only fails when for estimate gas. Otherwise, the status
        # is non-failing. This wasn't happened prior to Ape 0.6.9 because a bugfix revealed
        # that the test config was never getting applied and thus we never hit this problem
        # because it was estimating gas before (even tho should have been using max).
        mainnet_fork_contract_instance.setNumber(
            10, sender=mainnet_fork_contract_instance, gas="auto"
        )


@pytest.mark.fork
def test_transaction_unknown_contract_as_sender(accounts, mainnet_fork_provider):
    account = "0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"
    multi_sig = accounts[account]
    multi_sig.balance += accounts.conversion_manager.convert("1000 ETH", int)
    receipt = multi_sig.transfer(accounts[0], "100 gwei")
    assert not receipt.failed


@pytest.mark.fork
def test_get_receipt(mainnet_fork_provider, mainnet_fork_contract_instance, owner):
    receipt = mainnet_fork_contract_instance.setAddress(owner.address, sender=owner)
    actual = mainnet_fork_provider.get_receipt(receipt.txn_hash)
    assert receipt.txn_hash == actual.txn_hash
    assert actual.receiver == mainnet_fork_contract_instance.address
    assert actual.sender == receipt.sender


@pytest.mark.fork
def test_connect_to_polygon(networks, owner, contract_container):
    """
    Ensures we don't get PoA middleware issue.
    """
    with networks.polygon.mumbai_fork.use_provider("foundry"):
        contract = owner.deploy(contract_container)
        assert isinstance(contract, ContractInstance)  # Didn't fail
