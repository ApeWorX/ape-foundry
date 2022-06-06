import pytest
from ape.exceptions import SignatureError


def test_send_transaction(contract_instance, owner):
    contract_instance.set_number(10, sender=owner)
    assert contract_instance.my_number() == 10

    # Have to be in the same test because of X-dist complications
    with pytest.raises(SignatureError):
        contract_instance.set_number(20)
