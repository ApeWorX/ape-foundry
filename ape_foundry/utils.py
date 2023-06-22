from typing import Union

from eth_utils import to_bytes, to_hex
from ethpm_types import HexBytes


# TODO: Upstream to ape core
def to_bytes32(value: Union[int, str, bytes, HexBytes]) -> HexBytes:
    if isinstance(value, int):
        value = to_bytes(value)

    elif isinstance(value, str):
        if set(value.lower().replace("0x", "")) > set("0123456789abcdef"):
            raise TypeError(f"'{value}' not valid hexstr")

        value = to_bytes(hexstr=value)

    elif not isinstance(value, bytes):
        raise TypeError(f"Cannot convert type '{type(value)}' to 'bytes'")

    if len(value) > 32:
        raise ValueError(f"Value '{to_hex(value)}' must be <= 32 bytes")

    return HexBytes(value.rjust(32, b"\x00"))
