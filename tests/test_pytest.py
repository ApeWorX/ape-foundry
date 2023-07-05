import re
from pathlib import Path

import pytest

TESTS_PATH = Path(__file__).parent
BASE_DATA_PATH = TESTS_PATH / "data" / "python"
CONFTEST = (BASE_DATA_PATH / "pytest_test_conftest.py").read_text()
TEST_FILE = (BASE_DATA_PATH / "pytest_tests.py").read_text()
NUM_TESTS = len([x for x in TEST_FILE.split("\n") if x.startswith("def test_")])
TOKEN_B_GAS_REPORT = r"""
 +TokenB Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  __init__ +\d +\d+ + \d+ + \d+ + \d+
  balanceOf +\d +\d+ + \d+ + \d+ + \d+
  transfer +\d +\d+ + \d+ + \d+ + \d+
"""
EXPECTED_GAS_REPORT = rf"""
 +TestContractVy Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  __init__ +\d +\d+ + \d+ + \d+ + \d+
  fooAndBar +\d +\d+ + \d+ + \d+ + \d+
  myNumber +\d +\d+ + \d+ + \d+ + \d+
  setNumber +\d +\d+ + \d+ + \d+ + \d+

 +TokenA Gas

  Method +Times called +Min. +Max. +Mean +Median
 ─+
  __init__ +\d +\d+ + \d+ + \d+ + \d+
  balanceOf +\d +\d+ + \d+ + \d+ + \d+
  transfer +\d +\d+ + \d+ + \d+ + \d+
{TOKEN_B_GAS_REPORT}
"""
COVERAGE_START_PATTERN = re.compile(r"=+ Coverage Profile =+")


def filter_expected_methods(*methods_to_remove: str) -> str:
    expected = EXPECTED_GAS_REPORT
    for name in methods_to_remove:
        line = f"\n  {name} +\\d +\\d+ + \\d+ + \\d+ + \\d+"
        expected = expected.replace(line, "")

    return expected


@pytest.fixture
def ape_pytester(project, pytester):
    pytester.makeconftest(CONFTEST)
    pytester.makepyfile(TEST_FILE)
    return pytester


def run_gas_test(result, expected_report: str = EXPECTED_GAS_REPORT):
    output = "\n".join(result.outlines)
    result.assert_outcomes(passed=NUM_TESTS), f"PYTESTER FAILURE OUTPUT:\n{output}"

    gas_header_line_index = None
    for index, line in enumerate(result.outlines):
        if "Gas Profile" in line:
            gas_header_line_index = index

    assert gas_header_line_index is not None, "'Gas Profile' not in output."
    expected = expected_report.split("\n")[1:]
    start_index = gas_header_line_index + 1
    end_index = start_index + len(expected)
    actual = [x.rstrip() for x in result.outlines[start_index:end_index] if x.rstrip]
    assert "WARNING: No gas usage data found." not in actual, "Gas data missing!"

    actual_len = len(actual)
    expected_len = len(expected)

    if actual_len > expected_len:
        remainder = "\n".join(actual[expected_len:])
        pytest.fail(f"Actual contains more than expected:\n{remainder}")
    elif expected_len > actual_len:
        remainder = "\n".join(expected[actual_len:])
        pytest.fail(f"Expected contains more than actual:\n{remainder}")

    for actual_line, expected_pattern in zip(actual, expected):
        message = f"Pattern: {expected_pattern}, Line: '{actual_line}'."
        assert re.match(expected_pattern, actual_line), message


@pytest.mark.fork
def test_gas_flag_in_tests(ape_pytester):
    result = ape_pytester.runpytest("--gas")
    run_gas_test(result)

    # Verify can happen more than once.
    run_gas_test(result)


@pytest.mark.fork
def test_gas_flag_exclude_method_using_cli_option(ape_pytester):
    # NOTE: Includes both a mutable and a view method.
    expected = filter_expected_methods("fooAndBar", "myNumber")
    # Also ensure can filter out whole class
    expected = expected.replace(TOKEN_B_GAS_REPORT, "")
    result = ape_pytester.runpytest("--gas", "--gas-exclude", "*:fooAndBar,*:myNumber,tokenB:*")
    run_gas_test(result, expected_report=expected)


@pytest.mark.fork
def test_coverage(ape_pytester):
    """
    NOTE: Since vyper is required, we are unable to have decent tests
    verifying Foundry in coverage.
    TODO: Write + Run tests in an env with both vyper and foundry.
    """
    result = ape_pytester.runpytest("--coverage")
    result.assert_outcomes(passed=NUM_TESTS)
    assert any("Coverage Profile" in ln for ln in result.outlines)
    assert any("WARNING: No coverage data found." in ln for ln in result.outlines)
