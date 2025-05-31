from pathlib import Path

import pytest
from ape.api.networks import LOCAL_NETWORK_NAME
from ape.contracts import ContractInstance
from ape.exceptions import ContractLogicError
from ape_ethereum.ecosystem import NETWORKS

from ape_foundry import FoundryNetworkConfig

TESTS_DIRECTORY = Path(__file__).parent
TEST_ADDRESS = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture
def mainnet_fork_contract_instance(owner, contract_container, mainnet_fork_provider):
    return owner.deploy(contract_container)


@pytest.mark.fork
def test_multiple_providers(
    name, networks, ethereum, connected_provider, mainnet_fork_port, sepolia_fork_port
):
    default_host = "http://127.0.0.1:8545"
    assert networks.active_provider.name == name
    assert networks.active_provider.network.name == LOCAL_NETWORK_NAME
    assert networks.active_provider.uri == default_host
    mainnet_fork_host = f"http://127.0.0.1:{mainnet_fork_port}"

    with ethereum.mainnet_fork.use_provider(name, provider_settings={"host": mainnet_fork_host}):
        assert networks.active_provider.name == name
        assert networks.active_provider.network.name == "mainnet-fork"
        assert networks.active_provider.uri == mainnet_fork_host
        sepolia_fork_host = f"http://127.0.0.1:{sepolia_fork_port}"

        with ethereum.sepolia_fork.use_provider(
            name, provider_settings={"host": sepolia_fork_host}
        ):
            assert networks.active_provider.name == name
            assert networks.active_provider.network.name == "sepolia-fork"
            assert networks.active_provider.uri == sepolia_fork_host

        assert networks.active_provider.name == name
        assert networks.active_provider.network.name == "mainnet-fork"
        assert networks.active_provider.uri == mainnet_fork_host

    assert networks.active_provider.name == name
    assert networks.active_provider.network.name == LOCAL_NETWORK_NAME
    assert networks.active_provider.uri == default_host


@pytest.mark.parametrize("network", NETWORKS)
def test_fork_config(name, config, network):
    plugin_config = config.get_config(name)
    network_config = plugin_config["fork"].get("ethereum", {}).get(network, {})
    message = f"Config not registered for network '{network}'."
    assert network_config.get("upstream_provider") == "alchemy", message


@pytest.mark.fork
def test_sepolia_impersonate(accounts, sepolia_fork_provider):
    impersonated_account = accounts[TEST_ADDRESS]
    other_account = accounts[0]
    impersonated_account.balance += 1_000_000_000_000_000_000
    receipt = impersonated_account.transfer(other_account, "1 wei")
    assert receipt.receiver == other_account
    assert receipt.sender == impersonated_account


@pytest.mark.fork
def test_mainnet_impersonate(accounts, mainnet_fork_provider):
    impersonated_account = accounts[TEST_ADDRESS]
    other_account = accounts[0]
    impersonated_account.balance += 1_000_000_000_000_000_000
    receipt = impersonated_account.transfer(other_account, "1 wei")
    assert receipt.receiver == other_account
    assert receipt.sender == impersonated_account


@pytest.mark.fork
def test_request_timeout(networks, project, mainnet_fork_provider):
    actual = mainnet_fork_provider.web3.provider._request_kwargs["timeout"]
    expected = 360  # Value set in `ape-config.yaml`
    assert actual == expected

    # Test default behavior
    with project.temp_config(foundry={"fork_request_timeout": 300}):
        assert networks.active_provider.timeout == 300


@pytest.mark.fork
def test_reset_fork_no_fork_block_number(sepolia_fork_provider):
    sepolia_fork_provider.mine(5)
    prev_block_num = sepolia_fork_provider.get_block("latest").number
    sepolia_fork_provider.reset_fork()
    block_num_after_reset = sepolia_fork_provider.get_block("latest").number
    assert block_num_after_reset < prev_block_num


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_argument(sepolia_fork_provider):
    sepolia_fork_provider.mine(5)
    prev_block_num = sepolia_fork_provider.get_block("latest").number
    new_block_number = prev_block_num - 1
    sepolia_fork_provider.reset_fork(block_number=new_block_number)
    block_num_after_reset = sepolia_fork_provider.get_block("latest").number
    assert block_num_after_reset == new_block_number


@pytest.mark.fork
def test_reset_fork_specify_block_number_via_config(mainnet_fork_provider):
    mainnet_fork_provider.mine(5)
    mainnet_fork_provider.reset_fork()
    block_num_after_reset = mainnet_fork_provider.get_block("latest").number
    block_base_fee_after_reset = mainnet_fork_provider.get_block("latest").base_fee
    assert block_num_after_reset == 21418244  # Specified in ape-config.yaml
    assert block_base_fee_after_reset == 12273900931


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
    mainnet_fork_contract_instance,
    owner,
    contract_container,
    mainnet_fork_provider,
    convert,
):
    # Set balance so test wouldn't normally fail from lack of funds
    contract = owner.deploy(contract_container)
    mainnet_fork_provider.set_balance(contract.address, "1000 ETH")
    with pytest.raises(ContractLogicError, match="!authorized"):
        mainnet_fork_contract_instance.setNumber(10, sender=contract)


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
    with networks.polygon.amoy_fork.use_provider("foundry"):
        contract = owner.deploy(contract_container)
        assert isinstance(contract, ContractInstance)  # Didn't fail


@pytest.mark.fork
@pytest.mark.parametrize("network,port", [("amoy", 9878), ("mainnet", 9879)])
def test_provider_settings(networks, network, port):
    expected_block_number = 1234
    settings = {
        "host": f"http://127.0.0.1:{port}",
        "fork": {
            "polygon": {
                network: {
                    "block_number": expected_block_number,
                }
            }
        },
    }
    provider_ctx = networks.polygon.get_network(f"{network}-fork").use_provider(
        "foundry", provider_settings=settings
    )
    actual = provider_ctx._provider.settings
    assert actual.host == settings["host"]
    assert actual.fork["polygon"][network]["block_number"] == expected_block_number

    with provider_ctx as provider:
        assert provider.fork_block_number == expected_block_number


@pytest.mark.fork
def test_contract_interaction(mainnet_fork_provider, owner, mainnet_fork_contract_instance, mocker):
    # Spy on the estimate_gas RPC method.
    estimate_gas_spy = mocker.spy(mainnet_fork_provider.web3.eth, "estimate_gas")

    # Check what max gas is before transacting.
    max_gas = mainnet_fork_provider.max_gas

    # Invoke a method from a contract via transacting.
    receipt = mainnet_fork_contract_instance.setNumber(102, sender=owner)

    # Verify values from the receipt.
    assert not receipt.failed
    assert receipt.receiver == mainnet_fork_contract_instance.address
    assert receipt.gas_used < receipt.gas_limit
    assert receipt.gas_limit == max_gas

    # Show contract state changed.
    assert mainnet_fork_contract_instance.myNumber() == 102

    # Verify the estimate gas RPC was not used (since we are using max_gas).
    assert estimate_gas_spy.call_count == 0


def test_fork_config_none():
    cfg = FoundryNetworkConfig.model_validate({"fork": None})
    assert isinstance(cfg["fork"], dict)
