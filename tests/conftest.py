from pathlib import Path
from tempfile import mkdtemp

import ape
import pytest
from _pytest.runner import pytest_runtest_makereport as orig_pytest_runtest_makereport
from ape.api.networks import LOCAL_NETWORK_NAME
from ape.contracts import ContractContainer, ContractInstance
from ethpm_types import ContractType

from ape_foundry import FoundryForkProvider, FoundryProvider

# NOTE: Ensure that we don't use local paths for the DATA FOLDER
ape.config.DATA_FOLDER = Path(mkdtemp()).resolve()

BASE_CONTRACTS_PATH = Path(__file__).parent / "data" / "contracts"


def pytest_runtest_makereport(item, call):
    tr = orig_pytest_runtest_makereport(item, call)
    if call.excinfo is not None and "too many requests" in str(call.excinfo).lower():
        tr.outcome = "skipped"
        tr.wasxfail = "reason: Alchemy requests overloaded (likely in CI)"

    return tr


@pytest.fixture(scope="session", autouse=True)
def in_tests_dir(config):
    with config.using_project(Path(__file__).parent):
        yield


@pytest.fixture(scope="session")
def config():
    return ape.config


@pytest.fixture(scope="session")
def project():
    return ape.project


@pytest.fixture(scope="session")
def accounts():
    return ape.accounts.test_accounts


@pytest.fixture(scope="session")
def networks():
    return ape.networks


@pytest.fixture(scope="session")
def convert():
    return ape.convert


@pytest.fixture(scope="session")
def create_provider(local_network_api):
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


# @pytest.fixture(scope="session", params=("solidity", "vyper"))
@pytest.fixture(scope="session", params=("vyper",))
def raw_contract_type(request):
    path = BASE_CONTRACTS_PATH / "ethereum" / "local" / f"{request.param}_contract.json"
    return path.read_text()


@pytest.fixture(scope="session")
def contract_type(raw_contract_type) -> ContractType:
    return ContractType.parse_raw(raw_contract_type)


@pytest.fixture(scope="session")
def contract_container(contract_type) -> ContractContainer:
    return ContractContainer(contract_type=contract_type)


@pytest.fixture(scope="session")
def contract_instance(owner, contract_container, connected_provider) -> ContractInstance:
    return owner.deploy(contract_container)


@pytest.fixture(scope="session")
def disconnected_provider(create_provider):
    return create_provider()


@pytest.fixture(scope="session")
def connected_provider(networks):
    with networks.parse_network_choice("ethereum:local:foundry") as provider:
        yield provider


@pytest.fixture(scope="session")
def create_fork_provider(networks):
    def method(port: int = 9001, network: str = "mainnet"):
        network_api = networks.ecosystems["ethereum"][f"{network}-fork"]
        provider = FoundryForkProvider(
            name="foundry",
            network=network_api,
            request_header={},
            data_folder=Path("."),
            provider_settings={},
        )
        provider.port = port
        return provider

    return method


@pytest.fixture(scope="session")
def receipt(connected_provider, owner, contract_instance):
    return contract_instance.setNumber(6, sender=owner)
