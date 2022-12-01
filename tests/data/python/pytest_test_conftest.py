import pytest


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def contract(project, owner):
    c = project.TestContractVy.deploy(sender=owner)

    # Show that contract transactions in fixtures appear in gas report
    c.setNumber(999, sender=owner)

    return c
