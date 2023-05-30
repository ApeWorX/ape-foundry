import re
import shutil
import tempfile
from pathlib import Path
from typing import List

import pytest

from .expected_traces import (
    LOCAL_GAS_REPORT,
    LOCAL_TRACE,
    MAINNET_FAIL_TRACE_FIRST_10_LINES,
    MAINNET_FAIL_TRACE_LAST_10_LINES,
    MAINNET_TRACE_FIRST_10_LINES,
    MAINNET_TRACE_LAST_10_LINES,
)

MAINNET_FAIL_TXN_HASH = "0x053cba5c12172654d894f66d5670bab6215517a94189a9ffc09bc40a589ec04d"
MAINNET_TXN_HASH = "0xb7d7f1d5ce7743e821d3026647df486f517946ef1342a1ae93c96e4a8016eab7"
EXPECTED_MAP = {
    MAINNET_TXN_HASH: (MAINNET_TRACE_FIRST_10_LINES, MAINNET_TRACE_LAST_10_LINES),
    MAINNET_FAIL_TXN_HASH: (MAINNET_FAIL_TRACE_FIRST_10_LINES, MAINNET_FAIL_TRACE_LAST_10_LINES),
}
BASE_CONTRACTS_PATH = Path(__file__).parent / "data" / "contracts" / "ethereum"


@pytest.fixture
def captrace(capsys):
    class CapTrace:
        def read_trace(self, expected_start: str, file=None):
            lines = file.readlines() if file else capsys.readouterr().out.splitlines()
            start_index = 0
            for index, line in enumerate(lines):
                if line.strip().startswith(expected_start):
                    start_index = index
                    break

            return lines[start_index:]

    return CapTrace()


@pytest.fixture(autouse=True, scope="module")
def full_contracts_cache(config):
    destination = config.DATA_FOLDER / "ethereum"
    shutil.copytree(BASE_CONTRACTS_PATH, destination)


@pytest.fixture(
    params=(MAINNET_TXN_HASH, MAINNET_FAIL_TXN_HASH),
)
def mainnet_receipt(request, mainnet_fork_provider):
    return mainnet_fork_provider.get_receipt(request.param)


@pytest.fixture
def local_receipt(contract_a, owner):
    return contract_a.methodWithoutArguments(sender=owner)


def test_local_transaction_traces(local_receipt, captrace):
    # NOTE: Strange bug in Rich where we can't use sys.stdout for testing tree output.
    # And we have to write to a file, close it, and then re-open it to see output.
    def run_test():
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a tempfile to avoid terminal inconsistencies affecting output.
            file_path = Path(temp_dir) / "temp"
            with open(file_path, "w") as file:
                local_receipt.show_trace(file=file)

            with open(file_path, "r") as file:
                lines = captrace.read_trace("Call trace for", file=file)
                assert_rich_output(lines, LOCAL_TRACE)

    run_test()

    # Verify can happen more than once.
    run_test()


def test_local_transaction_gas_report(local_receipt, captrace):
    def run_test():
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "temp"
            with open(temp_file, "w") as file:
                local_receipt.show_gas_report(file=file)

            with open(temp_file, "r") as file:
                lines = captrace.read_trace("ContractA Gas", file=file)

            assert_rich_output(lines, LOCAL_GAS_REPORT)

    run_test()

    # Verify can happen more than once.
    run_test()


@pytest.mark.manual
def test_mainnet_transaction_traces(mainnet_receipt, captrace):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "temp"

        with open(temp_file, "w") as file:
            mainnet_receipt.show_trace(file=file)

        with open(temp_file, "r") as file:
            lines = captrace.read_trace("Call trace for", file=file)

        expected_beginning, expected_ending = EXPECTED_MAP[mainnet_receipt.txn_hash]
        actual_beginning = lines[:10]
        actual_ending = lines[-10:]
        assert_rich_output(actual_beginning, expected_beginning)
        assert_rich_output(actual_ending, expected_ending)


def assert_rich_output(rich_capture: List[str], expected: str):
    expected_lines = [x.rstrip() for x in expected.splitlines() if x.rstrip()]
    actual_lines = [x.rstrip() for x in rich_capture if x.rstrip()]
    assert actual_lines, "No output."
    output = "\n".join(actual_lines)

    for actual, expected in zip(actual_lines, expected_lines):
        fail_message = f"""\n
        \tPattern: {expected},\n
        \tLine   : {actual}\n
        \n
        Complete output:
        \n{output}
        """
        try:
            assert re.match(expected, actual), fail_message
        except AssertionError:
            raise  # Let assertion errors raise as normal.
        except Exception as err:
            pytest.fail(f"{fail_message}\n{err}")

    actual_len = len(actual_lines)
    expected_len = len(expected_lines)
    if expected_len > actual_len:
        rest = "\n".join(expected_lines[actual_len:])
        pytest.fail(f"Missing expected lines: {rest}")
