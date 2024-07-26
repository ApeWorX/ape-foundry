# Quick Start

Foundry network provider plugin for Ape.
Foundry is a development framework written in Rust for Ethereum that includes a local network implementation.

## Dependencies

- [python3](https://www.python.org/downloads) version 3.9 up to 3.12.
- Foundry. See Foundry's [Installation](https://github.com/foundry-rs/foundry#installation) documentation for steps.

## Installation

### via `pip`

You can install the latest release via [`pip`](https://pypi.org/project/pip/):

```bash
pip install ape-foundry
```

### via `setuptools`

You can clone the repository and use [`setuptools`](https://github.com/pypa/setuptools) for the most up-to-date version:

```bash
git clone https://github.com/ApeWorX/ape-foundry.git
cd ape-foundry
python3 setup.py install
```

## Quick Usage

Use the `--network ethereum:local:foundry` command line flag to use the foundry network (if it's not already configured as the default).

This network provider takes additional Foundry-specific configuration options. To use them, add these configs in your project's `ape-config.yaml`:

```yaml
foundry:
  host: https://127.0.0.1:8555
```

To select a random port, use a value of "auto":

```yaml
foundry:
  host: auto
```

This is useful for multiprocessing and starting up multiple providers.

You can also adjust the request timeout setting:

```yaml
foundry:
  request_timeout: 20  # Defaults to 30
  fork_request_timeout: 600  # Defaults to 300
```

## Mainnet Fork

The `ape-foundry` plugin also includes a mainnet fork provider.
It requires using another provider that has access to mainnet.

Use it in most commands like this:

```bash
ape console --network :mainnet-fork:foundry
```

Specify the upstream archive-data provider in your `ape-config.yaml`:

```yaml
foundry:
  fork:
    ethereum:
      mainnet:
        upstream_provider: alchemy
```

Otherwise, it defaults to the default mainnet provider plugin.
You can also specify a `block_number` and `evm_version`.

If the block number is specified, but no EVM version is specified, it is automatically set based on the block height for known networks.

**NOTE**: Make sure you have the upstream provider plugin installed for ape.

```bash
ape plugins install alchemy
```

## Remote Anvil Node

To connect to a remote anvil node, set up your config like this:

```yaml
foundry:
  host: https://anvil.example.com
```

Now, instead of launching a local process, it will attempt to connect to the remote anvil node and use this plugin as the ape interface.

To connect to a remote anvil node using an environment variable, set `APE_FOUNDRY_HOST`:

```bash
export APE_FOUNDRY_HOST=https://your-anvil.example.com`
```

## Impersonate Accounts

You can impersonate accounts using the `ape-foundry` plugin.
To impersonate an account, do the following:

```python
import pytest

@pytest.fixture
def whale(accounts):
    return accounts["example.eth"]
```

To transact, your impersonated account must have a balance.
You can achieve this by using a forked network and impersonating an account with a balance.
Alternatively, you can set your node's base fee and priority fee to `0`.

To programtically set an account's balance, do the following:

```python
from ape import accounts

account = accounts["example.eth"]
account.balance = "1000 ETH"  # This calls `anvil_setBalance` under-the-hood.
```

## Base Fee and Priority Fee

Configure your node's base fee and priority fee using the `ape-config.yaml` file.

```yaml
foundry:
  base_fee: 0
  priority_fee: 0
```

## Auto-mining

Anvil nodes by default auto-mine.
However, you can disable auto-mining on startup by configuring the foundry plugin like so:

```yaml
foundry:
  auto_mine: false
```

Else, you can disable auto-mining using the provider instance:

```python
from ape import chain

anvil = chain.provider
anvil.auto_mine = False  # calls `anvil_setAutomine` RPC.
```

### Mine on an interval

By default, Anvil will mine a new block every time a transaction is submitted.
To mine on an interval instead, set the `block_time` config:

```yaml
foundry:
  block_time: 10  # mine a new block every 10 seconds
```

## EVM Version (hardfork)

To change the EVM version for local foundry networks, use the `evm_version` config:

```yaml
foundry:
  evm_version: shanghai
```

To change the EVM version for forked networks, set it the specific forked-network config(s):

```yaml
foundry:
  fork:
    ethereum:
      mainnet:
        evm_version: shanghai
```
