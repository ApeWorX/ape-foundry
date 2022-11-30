def test_provider(project, networks):
    """
    Tests that the network gets set from ape-config.yaml.
    """
    assert networks.provider.name == "foundry"


def test_contract_interaction(owner, contract):
    """
    Traditional ape-test style test.
    """
    contract.setNumber(123, sender=owner)
    assert contract.myNumber() == 123


def test_transfer(accounts):
    """
    Tests that the ReceiptCapture handles transfer transactions.
    """
    accounts[0].transfer(accounts[1], "100 gwei")


def test_using_contract_with_same_type_and_method_call(owner, project):
    """
    Deploy the same contract from the ``contract`` fixture and call a method
    that gets called elsewhere in the test suite. This shows that we amass
    results across all instances of contract types when making the gas report.
    """
    contract = project.TestContractVy.deploy(sender=owner)
    contract.setNumber(123, sender=owner)
    assert contract.myNumber() == 123


def test_two_contracts_with_same_symbol(owner, accounts, project):
    """
    Tests against scenario when using 2 tokens with same symbol.
    There was almost a bug where the contract IDs clashed.
    This is to help prevent future bugs related to this.
    """
    receiver = accounts[1]
    token_a = project.TokenA.deploy(sender=owner)
    token_b = project.TokenB.deploy(sender=owner)
    token_a.transfer(receiver, 5, sender=owner)
    token_b.transfer(receiver, 6, sender=owner)
    assert token_a.balanceOf(receiver) == 5
    assert token_b.balanceOf(receiver) == 6


def test_call_method_excluded_from_cli_options(owner, contract):
    """
    Call a method so that we can intentionally ignore it via command
    line options and test that it does not show in the report.
    """
    receipt = contract.fooAndBar(sender=owner)
    assert not receipt.failed


def test_call_method_excluded_from_config(owner, contract):
    """
    Call a method excluded in the ``ape-config.yaml`` file
    for asserting it does not show in gas report.
    """
    receipt = contract.setAddress(owner.address, sender=owner)
    assert not receipt.failed
