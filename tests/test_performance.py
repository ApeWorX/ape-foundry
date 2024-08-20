from ape.api import ReceiptAPI


def test_contract_transaction_revert(benchmark, connected_provider, owner, contract_instance):
    tx = benchmark.pedantic(
        lambda *args, **kwargs: contract_instance.setNumber(*args, **kwargs),
        args=(5,),
        kwargs={"sender": owner, "raise_on_revert": False},
        rounds=5,
        warmup_rounds=1,
    )
    assert isinstance(tx, ReceiptAPI)  # Sanity check.
    stats = benchmark.stats
    median = stats.get("median")

    # Was seeing 0.44419266798649915.
    # Seeing 0.2634877339878585 as of https://github.com/ApeWorX/ape-foundry/pull/115
    assert median < 3.5
