"""
Ape network provider plugin for Foundry (Ethereum development framework and network
implementation written in Node.js).
"""

from ape import plugins
from ape.api.networks import LOCAL_NETWORK_NAME
from ape_ethereum.ecosystem import NETWORKS

from .provider import (
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

    for network in NETWORKS:
        yield "ethereum", f"{network}-fork", FoundryForkProvider

    yield "arbitrum", LOCAL_NETWORK_NAME, FoundryProvider
    yield "arbitrum", "mainnet-fork", FoundryForkProvider
    yield "arbitrum", "goerli-fork", FoundryForkProvider

    yield "avalanche", LOCAL_NETWORK_NAME, FoundryProvider
    yield "avalanche", "mainnet-fork", FoundryForkProvider
    yield "avalanche", "fuji-fork", FoundryForkProvider

    yield "bsc", LOCAL_NETWORK_NAME, FoundryProvider
    yield "bsc", "mainnet-fork", FoundryForkProvider
    yield "bsc", "testnet-fork", FoundryForkProvider

    yield "fantom", LOCAL_NETWORK_NAME, FoundryProvider
    yield "fantom", "opera-fork", FoundryForkProvider
    yield "fantom", "testnet-fork", FoundryForkProvider

    yield "optimism", LOCAL_NETWORK_NAME, FoundryProvider
    yield "optimism", "mainnet-fork", FoundryForkProvider
    yield "optimism", "goerli-fork", FoundryForkProvider

    yield "polygon", LOCAL_NETWORK_NAME, FoundryProvider
    yield "polygon", "mainnet-fork", FoundryForkProvider
    yield "polygon", "mumbai-fork", FoundryForkProvider


__all__ = [
    "FoundryNetworkConfig",
    "FoundryProvider",
    "FoundryProviderError",
    "FoundrySubprocessError",
]
