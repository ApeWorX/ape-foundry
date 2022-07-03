import tempfile
from pathlib import Path

import pytest
from ape.exceptions import ContractLogicError
from ape.types import AddressType
from ape_ethereum.ecosystem import NETWORKS
from eth_typing import HexAddress, HexStr

TESTS_DIRECTORY = Path(__file__).parent
TEST_ADDRESS = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture(scope="module")
def mainnet_fork_network_api(networks):
    return networks.ecosystems["ethereum"]["mainnet-fork"]


@pytest.fixture(scope="module")
def connected_mainnet_fork_provider(networks):
    with networks.parse_network_choice("ethereum:mainnet-fork:foundry") as provider:
        yield provider


@pytest.fixture(scope="module")
def fork_contract_instance(owner, contract_container, connected_mainnet_fork_provider):
    return owner.deploy(contract_container)


@pytest.mark.parametrize("network", [k for k in NETWORKS.keys()])
def test_fork_config(config, network):
    plugin_config = config.get_config("foundry")
    network_config = plugin_config["fork"].get("ethereum", {}).get(network, {})
    assert network_config["upstream_provider"] == "alchemy", "config not registered"


@pytest.mark.fork
@pytest.mark.parametrize("upstream,port", [("mainnet", 8998), ("rinkeby", 8999)])
def test_impersonate(networks, accounts, upstream, port, create_fork_provider):
    orig_provider = networks.active_provider
    provider = create_fork_provider(port, upstream)
    provider.connect()
    networks.active_provider = provider

    impersonated_account = accounts[TEST_ADDRESS]
    other_account = accounts[0]
    receipt = impersonated_account.transfer(other_account, "1 wei")
    assert receipt.receiver == other_account
    assert receipt.sender == impersonated_account

    provider.disconnect()
    networks.active_provider = orig_provider


@pytest.mark.fork
def test_request_timeout(networks, config, mainnet_fork_network_api, create_fork_provider):
    provider = create_fork_provider(port=9008)
    provider.connect()
    actual = provider.web3.provider._request_kwargs["timeout"]  # type: ignore
    expected = 360  # Value set in `ape-config.yaml`
    assert actual == expected
    provider.disconnect()

    # Test default behavior
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        with config.using_project(temp_dir):
            provider = create_fork_provider(port=9011)
            assert provider.timeout == 300


@pytest.mark.fork
def test_reset_fork(networks, create_fork_provider):
    provider = create_fork_provider(port=9010)
    provider.connect()
    provider.mine()
    prev_block_num = provider.get_block("latest").number
    provider.reset_fork()
    block_num_after_reset = provider.get_block("latest").number
    assert block_num_after_reset < prev_block_num
    provider.disconnect()


@pytest.mark.fork
def test_send_transaction(connected_mainnet_fork_provider, owner, fork_contract_instance):
    receipt = fork_contract_instance.setNumber(6, sender=owner)
    assert receipt.sender == owner
    value = fork_contract_instance.myNumber()
    assert value == 6


@pytest.mark.fork
def test_revert(sender, fork_contract_instance, connected_mainnet_fork_provider):
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
def test_transaction_contract_as_sender(
    fork_contract_instance, connected_mainnet_fork_provider, convert
):
    amount = convert("1000 ETH", int)
    connected_mainnet_fork_provider.set_balance(fork_contract_instance.address, amount)

    with pytest.raises(ContractLogicError) as err:
        # Task failed successfully
        fork_contract_instance.setNumber(10, sender=fork_contract_instance)

    assert str(err.value) == "!authorized"


@pytest.mark.fork
def test_transaction_unknown_contract_as_sender(accounts, networks, create_fork_provider, convert):
    init_provider = networks.active_provider
    provider = create_fork_provider(port=9012)
    provider.connect()
    networks.active_provider = provider
    account = AddressType(HexAddress(HexStr("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52")))
    multi_sig = accounts[account]
    # provider.set_balance(account, convert("1000 ETH", int))
    multi_sig.transfer(accounts[0], "100 gwei")
    networks.active_provider = init_provider
