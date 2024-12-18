from functools import cached_property
from typing import Any

from ape.exceptions import ContractNotFoundError
from ape_ethereum.trace import TraceApproach, TransactionTrace
from hexbytes import HexBytes


class AnvilTransactionTrace(TransactionTrace):
    call_trace_approach: TraceApproach = TraceApproach.PARITY
    debug_trace_transaction_parameters: dict = {
        "stepsTracing": True,
        "enableMemory": True,
    }

    @cached_property
    def return_value(self) -> Any:
        if self._enriched_calltree:
            # Only check enrichment output if was already enriched!
            # Don't enrich ONLY for return value, as that is very bad performance
            # for realistic contract interactions.
            return self._return_value_from_enriched_calltree

        # perf: Avoid any model serializing/deserializing that happens at
        #   Ape's abstract layer at this point.
        if not (data := self.provider.make_request("trace_transaction", [self.transaction_hash])):
            return (None,)

        try:
            address = data[0]["action"]["to"]
            calldata = data[0]["action"]["input"]
            contract_type = self.chain_manager.contracts[address]
            abi = contract_type.methods[calldata[:10]]
        except (KeyError, ContractNotFoundError):
            abi = self.root_method_abi

        if output := data[-1].get("result", {}).get("output"):
            return self._ecosystem.decode_returndata(abi, HexBytes(output))

        return (None,)
