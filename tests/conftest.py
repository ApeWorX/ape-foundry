from pathlib import Path

import ape
import pytest  # type: ignore
from ape.api.networks import LOCAL_NETWORK_NAME
from ape.contracts import ContractContainer, ContractInstance
from ethpm_types import ContractType

from ape_foundry import FoundryProvider

BASE_CONTRACTS_PATH = Path(__file__).parent / "data" / "contracts"


@pytest.fixture(scope="session", autouse=True)
def in_tests_dir(config):
    with config.using_project(Path(__file__).parent):
        yield


@pytest.fixture(scope="session")
def config():
    return ape.config


@pytest.fixture(scope="session")
def accounts():
    return ape.accounts.test_accounts


@pytest.fixture(scope="session")
def networks():
    return ape.networks


@pytest.fixture(scope="session")
def get_foundry_provider(local_network_api):
    def method():
        return FoundryProvider(
            name="foundry",
            network=local_network_api,
            request_header={},
            data_folder=Path("."),
            provider_settings={},
        )

    return method


@pytest.fixture(scope="session")
def sender(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def receiver(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[2]


@pytest.fixture(scope="session")
def local_network_api(networks):
    return networks.ecosystems["ethereum"][LOCAL_NETWORK_NAME]


@pytest.fixture(scope="session", params=("solidity", "vyper"))
def raw_contract_type(request):
    path = BASE_CONTRACTS_PATH / f"{request.param}_contract.json"
    return path.read_text()


@pytest.fixture(scope="session")
def contract_type(raw_contract_type) -> ContractType:
    return ContractType.parse_raw(raw_contract_type)


@pytest.fixture(scope="session")
def contract_container(contract_type) -> ContractContainer:
    return ContractContainer(contract_type=contract_type)


@pytest.fixture(scope="session")
def contract_instance(owner, contract_container, foundry_connected) -> ContractInstance:
    return owner.deploy(contract_container)


@pytest.fixture(scope="session")
def foundry_disconnected(get_foundry_provider):
    return get_foundry_provider()


@pytest.fixture(scope="session")
def foundry_connected(networks):
    with networks.parse_network_choice("ethereum:local:foundry") as provider:
        yield provider
