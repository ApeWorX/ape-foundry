"""
Ape network provider plugin for Foundry (Ethereum development framework and network
implementation written in Node.js).
"""

from ape import plugins


@plugins.register(plugins.Config)
def config_class():
    from .provider import FoundryNetworkConfig

    return FoundryNetworkConfig


@plugins.register(plugins.ProviderPlugin)
def providers():
    from ape.api.networks import LOCAL_NETWORK_NAME
    from ape_ethereum.ecosystem import NETWORKS

    from .provider import FoundryForkProvider, FoundryProvider

    yield "ethereum", LOCAL_NETWORK_NAME, FoundryProvider

    for network in NETWORKS:
        yield "ethereum", f"{network}-fork", FoundryForkProvider

    yield "arbitrum", LOCAL_NETWORK_NAME, FoundryProvider
    yield "arbitrum", "mainnet-fork", FoundryForkProvider
    yield "arbitrum", "sepolia-fork", FoundryForkProvider

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
    yield "optimism", "sepolia-fork", FoundryForkProvider

    yield "polygon", LOCAL_NETWORK_NAME, FoundryProvider
    yield "polygon", "mainnet-fork", FoundryForkProvider
    yield "polygon", "amoy-fork", FoundryForkProvider

    yield "base", LOCAL_NETWORK_NAME, FoundryProvider
    yield "base", "mainnet-fork", FoundryForkProvider
    yield "base", "sepolia-fork", FoundryForkProvider

    yield "blast", LOCAL_NETWORK_NAME, FoundryProvider
    yield "blast", "mainnet-fork", FoundryForkProvider
    yield "blast", "sepolia-fork", FoundryForkProvider


def __getattr__(name: str):
    if name == "FoundryForkProvider":
        from ape_foundry.provider import FoundryForkProvider

        return FoundryForkProvider

    elif name == "FoundryNetworkConfig":
        from ape_foundry.provider import FoundryNetworkConfig

        return FoundryNetworkConfig

    elif name == "FoundryProvider":
        from ape_foundry.provider import FoundryProvider

        return FoundryProvider

    elif name == "FoundryProviderError":
        from ape_foundry.provider import FoundryProviderError

        return FoundryProviderError

    elif name == "FoundrySubprocessError":
        from ape_foundry.provider import FoundrySubprocessError

        return FoundrySubprocessError

    else:
        raise AttributeError(name)


__all__ = [
    "FoundryForkProvider",
    "FoundryNetworkConfig",
    "FoundryProvider",
    "FoundryProviderError",
    "FoundrySubprocessError",
]
