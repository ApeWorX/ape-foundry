"""
Ape network provider plugin for Foundry (Ethereum development framework and network
implementation written in Node.js).
"""

from ape import plugins
from ape.api.networks import LOCAL_NETWORK_NAME

from .providers import (
    FoundryForkProvider,
    FoundryNetworkConfig,
    FoundryProvider,
    FoundryProviderError,
    FoundrySubprocessError,
)


@plugins.register(plugins.Config)
def config_class():
    return FoundryNetworkConfig


@plugins.register(plugins.ProviderPlugin)
def providers():
    yield "ethereum", LOCAL_NETWORK_NAME, FoundryProvider
    yield "ethereum", "mainnet-fork", FoundryForkProvider
    yield "fantom", LOCAL_NETWORK_NAME, FoundryProvider
    yield "fantom", "opera-fork", FoundryForkProvider


__all__ = [
    "FoundryNetworkConfig",
    "FoundryProvider",
    "FoundryProviderError",
    "FoundrySubprocessError",
]
