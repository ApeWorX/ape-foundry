import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from ape.exceptions import ContractLogicError
from ape.types import AddressType
from ape_ethereum.ecosystem import NETWORKS
from eth_typing import HexAddress, HexStr

TESTS_DIRECTORY = Path(__file__).parent
TEST_ADDRESS = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"


@pytest.fixture(scope="module")
def connect_to(networks, create_fork_provider):
    @contextmanager
    def connect(port: int = 8997, network: str = "mainnet"):
        current_provider = networks.active_provider
        networks.active_provider = create_fork_provider(port, network)
        networks.active_provider.connect()
        yield networks.active_provider
        networks.active_provider = current_provider

    return connect


@pytest.fixture(scope="module")
def fork_provider(connect_to):
    with connect_to() as provider:
        yield provider


@pytest.fixture(scope="module")
def fork_contract(owner, contract_container, fork_provider):
    return owner.deploy(contract_container)


@pytest.fixture(scope="module")
def mainnet_fork_network_api(networks):
    return networks.ecosystems["ethereum"]["mainnet-fork"]


@pytest.mark.parametrize("network", [k for k in NETWORKS.keys()])
def test_fork_config(config, network):
    plugin_config = config.get_config("foundry")
    network_config = plugin_config["fork"].get("ethereum", {}).get(network, {})
    assert network_config["upstream_provider"] == "alchemy", "config not registered"


@pytest.mark.fork
@pytest.mark.parametrize("upstream,port", [("mainnet", 8998), ("rinkeby", 8999)])
def test_impersonate(connect_to, convert, accounts, upstream, port):
    with connect_to(port, upstream) as provider:
        impersonated_account = accounts[TEST_ADDRESS]
        provider.set_balance(impersonated_account, convert("10000 ETH", int))
        other_account = accounts[0]
        receipt = impersonated_account.transfer(other_account, "10000 gwei")
        assert receipt.receiver == other_account
        assert receipt.sender == impersonated_account


@pytest.mark.fork
def test_request_timeout(config, fork_provider, project):
    actual = fork_provider.web3.provider._request_kwargs["timeout"]  # type: ignore
    expected = 360  # Value set in `ape-config.yaml`
    assert actual == expected

    # Test default behavior
    config_file_path = project.path / "ape-config.yaml"
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        try:
            shutil.copy(config_file_path, temp_dir)
            config_file_path.unlink()
            config._cached_configs = {}  # Force reload of configs
            assert fork_provider.timeout == 300
        finally:
            shutil.copy(temp_dir / "ape-config.yaml", project.path)


@pytest.mark.fork
def test_reset_fork(fork_provider):
    fork_provider.mine()
    prev_block_num = fork_provider.get_block("latest").number
    fork_provider.reset_fork()
    block_num_after_reset = fork_provider.get_block("latest").number
    assert block_num_after_reset < prev_block_num


@pytest.mark.fork
def test_get_balance(owner, fork_provider):
    assert fork_provider.get_balance(owner)


@pytest.mark.fork
def test_send_transaction(owner, fork_contract, fork_provider):
    receipt = fork_contract.setNumber(6, sender=owner)
    assert receipt.sender == owner
    value = fork_contract.myNumber()
    assert value == 6


@pytest.mark.fork
def test_revert(sender, fork_contract, fork_provider):
    # 'sender' is not the owner so it will revert (with a message)
    with pytest.raises(ContractLogicError) as err:
        fork_contract.setNumber(6, sender=sender)

    assert str(err.value) == "!authorized"


@pytest.mark.fork
def test_contract_revert_no_message(fork_contract, owner, fork_provider):
    # The Contract raises empty revert when setting number to 5.
    with pytest.raises(ContractLogicError) as err:
        fork_contract.setNumber(5, sender=owner)

    assert str(err.value) == "Transaction failed."


@pytest.mark.fork
def test_transaction_contract_as_sender(convert, owner, contract_container, fork_provider):
    first_instance = owner.deploy(contract_container)
    second_instance = owner.deploy(contract_container)
    amount = convert("1000 ETH", int)
    fork_provider.set_balance(second_instance, amount)

    with pytest.raises(ContractLogicError) as err:
        # Task failed successfully
        first_instance.setNumber(10, sender=second_instance)

    assert str(err.value) == "!authorized"


@pytest.mark.fork
def test_transaction_unknown_contract_as_sender(convert, accounts, fork_provider):
    account = AddressType(HexAddress(HexStr("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52")))
    multi_sig = accounts[account]
    fork_provider.set_balance(multi_sig, convert("1000 ETH", int))
    multi_sig.transfer(accounts[0], "100 gwei")
