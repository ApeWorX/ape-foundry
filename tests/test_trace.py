import re
import shutil
from pathlib import Path
from typing import List

import pytest
from ape.contracts import ContractContainer
from ethpm_types import ContractType

from .expected_traces import LOCAL_GAS_REPORT, LOCAL_TRACE, MAINNET_FAIL_TRACE, MAINNET_TRACE

MAINNET_FAIL_TXN_HASH = "0x053cba5c12172654d894f66d5670bab6215517a94189a9ffc09bc40a589ec04d"
MAINNET_TXN_HASH = "0xb7d7f1d5ce7743e821d3026647df486f517946ef1342a1ae93c96e4a8016eab7"
EXPECTED_MAP = {
    MAINNET_TXN_HASH: MAINNET_TRACE,
    MAINNET_FAIL_TXN_HASH: MAINNET_FAIL_TRACE,
}
BASE_CONTRACTS_PATH = Path(__file__).parent / "data" / "contracts" / "ethereum"


@pytest.fixture
def captrace(capsys):
    class CapTrace:
        def read_trace(self, expected_start: str):
            lines = capsys.readouterr().out.split("\n")
            start_index = 0
            for index, line in enumerate(lines):
                if line.strip() == expected_start:
                    start_index = index
                    break

            return lines[start_index:]

    return CapTrace()


@pytest.fixture(autouse=True, scope="module")
def full_contracts_cache(config):
    destination = config.DATA_FOLDER / "ethereum"
    shutil.copytree(BASE_CONTRACTS_PATH, destination)


@pytest.fixture(autouse=True, scope="module")
def provider(networks):
    with networks.parse_network_choice("ethereum:mainnet-fork:foundry") as provider:
        yield provider


@pytest.fixture(
    params=(MAINNET_TXN_HASH, MAINNET_FAIL_TXN_HASH),
    scope="module",
)
def mainnet_receipt(request, provider):
    yield provider.get_receipt(request.param)


@pytest.fixture(scope="module")
def contract_a(owner, provider):
    base_path = BASE_CONTRACTS_PATH / "local"

    def get_contract_type(suffix: str) -> ContractType:
        return ContractType.parse_file(base_path / f"contract_{suffix}.json")

    contract_c = owner.deploy(ContractContainer(get_contract_type("c")))
    contract_b = owner.deploy(ContractContainer(get_contract_type("b")), contract_c.address)
    contract_a = owner.deploy(
        ContractContainer(get_contract_type("a")), contract_b.address, contract_c.address
    )

    return contract_a


@pytest.fixture
def local_receipt(contract_a, owner):
    return contract_a.methodWithoutArguments(sender=owner)


@pytest.mark.skip("TODO")
@pytest.mark.sync
def test_local_transaction_traces(local_receipt, captrace):
    # NOTE: Strange bug in Rich where we can't use sys.stdout for testing tree output.
    # And we have to write to a file, close it, and then re-open it to see output.
    def run_test():
        local_receipt.show_trace()
        lines = captrace.read_trace("Call trace for")
        assert_rich_output(lines, LOCAL_TRACE)

    run_test()

    # Verify can happen more than once.
    run_test()


@pytest.mark.sync
def test_local_transaction_gas_report(local_receipt, captrace):
    def run_test():
        local_receipt.show_gas_report()
        lines = captrace.read_trace("ContractA Gas")
        assert_rich_output(lines, LOCAL_GAS_REPORT)

    run_test()

    # Verify can happen more than once.
    run_test()


@pytest.mark.skip("TODO")
@pytest.mark.manual
def test_mainnet_transaction_traces(mainnet_receipt, captrace):
    mainnet_receipt.show_trace()
    lines = captrace.read_trace("Call trace for")
    assert_rich_output(lines, EXPECTED_MAP[mainnet_receipt.txn_hash])


def assert_rich_output(rich_capture: List[str], expected: str):
    expected_lines = [x.rstrip() for x in expected.split("\n") if x.rstrip()]
    actual_lines = [x.rstrip() for x in rich_capture if x.rstrip()]
    assert actual_lines, "No output."

    for actual, expected in zip(actual_lines, expected_lines):
        fail_message = f"Pattern: {expected}, Line: {actual}"
        try:
            assert re.match(expected, actual), fail_message
        except Exception as err:
            pytest.fail(f"{fail_message}\n{err}")

    actual_len = len(actual_lines)
    expected_len = len(expected_lines)
    if expected_len > actual_len:
        rest = "\n".join(expected_lines[actual_len:])
        pytest.fail(f"Missing expected lines: {rest}")
