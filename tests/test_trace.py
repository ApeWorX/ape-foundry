import shutil
from pathlib import Path

import pytest
from ape.contracts import ContractContainer
from ape.logging import LogLevel, logger
from ethpm_types import ContractType

from .expected_traces import LOCAL_TRACE, MAINNET_FAIL_TRACE, MAINNET_TRACE

MAINNET_FAIL_TXN_HASH = "0x053cba5c12172654d894f66d5670bab6215517a94189a9ffc09bc40a589ec04d"
MAINNET_TXN_HASH = "0xb7d7f1d5ce7743e821d3026647df486f517946ef1342a1ae93c96e4a8016eab7"
EXPECTED_MAP = {
    MAINNET_TXN_HASH: MAINNET_TRACE,
    MAINNET_FAIL_TXN_HASH: MAINNET_FAIL_TRACE,
}
BASE_CONTRACTS_PATH = Path(__file__).parent / "data" / "contracts" / "ethereum"


@pytest.fixture(autouse=True, scope="module")
def full_contracts_cache(config):
    destination = config.DATA_FOLDER / "ethereum"
    shutil.copytree(BASE_CONTRACTS_PATH, destination)


@pytest.fixture(
    params=(MAINNET_TXN_HASH, MAINNET_FAIL_TXN_HASH),
    scope="module",
)
def mainnet_receipt(request, networks):
    with networks.parse_network_choice("ethereum:mainnet-fork:foundry") as provider:
        yield provider.get_transaction(request.param)


@pytest.fixture(scope="session")
def contract_a(owner, connected_provider):
    base_path = BASE_CONTRACTS_PATH / "local"

    def get_contract_type(suffix: str) -> ContractType:
        return ContractType.parse_raw((base_path / f"contract_{suffix}.json").read_text())

    contract_c = owner.deploy(ContractContainer(get_contract_type("c")))
    contract_b = owner.deploy(ContractContainer(get_contract_type("b")), contract_c)
    contract_a = owner.deploy(
        ContractContainer(get_contract_type("a")), contract_b.address, contract_c.address
    )
    return contract_a


@pytest.fixture
def local_receipt(contract_a, owner):
    return contract_a.methodWithoutArguments(sender=owner)


@pytest.fixture
def trace_capture(capsys):
    def get():
        output, _ = capsys.readouterr()
        return [s.strip() for s in output.split("\n")]

    return get


def test_local_transaction_traces(local_receipt, trace_capture):
    logger.set_level(LogLevel.INFO)
    local_receipt.show_trace()
    captured_trace = trace_capture()
    assert all([x in LOCAL_TRACE for x in captured_trace])

    # Verify can happen more than once.
    local_receipt.show_trace()
    captured_trace = trace_capture()
    assert all([x in LOCAL_TRACE for x in captured_trace])
    logger.set_level(LogLevel.DEBUG)


@pytest.mark.manual
def test_mainnet_transaction_traces(mainnet_receipt, trace_capture):
    logger.set_level(LogLevel.INFO)
    mainnet_receipt.show_trace()
    assert all([x in EXPECTED_MAP[mainnet_receipt.txn_hash] for x in trace_capture()])
    logger.set_level(LogLevel.DEBUG)
