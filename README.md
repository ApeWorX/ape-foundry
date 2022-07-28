# ape-foundry

Foundry network provider plugin for Ape. Foundry is a development framework written in Node.js for Ethereum that includes a local network implementation.

## Dependencies

* [python3](https://www.python.org/downloads) version 3.7.2 or greater, python3-dev
* Foundry. See Foundry's [Installation](https://github.com/foundry-rs/foundry#installation>) documentation for steps.

## Installation

### via ``pip``

You can install the latest release via [`pip`](https://pypi.org/project/pip/):

```bash
pip install ape-foundry
```

### via ``setuptools``

You can clone the repository and use [`setuptools`](https://github.com/pypa/setuptools) for the most up-to-date version:

```bash
git clone https://github.com/ApeWorX/ape-foundry.git
cd ape-foundry
python3 setup.py install
```

## Quick Usage

To use the plugin, first install Foundry locally into your Ape project directory:

```bash
cd your-ape-project
npm install --save-dev foundry
```

After that, you can use the ``--network ethereum:development:foundry`` command line flag to use the foundry network (if it's not already configured as the default).

This network provider takes additional Foundry-specific configuration options. To use them, add these configs in your project's ``ape-config.yaml``:

```yaml
foundry:
  port: 8555
```

To select a random port, use a value of "auto":

```yaml
foundry:
  port: auto
```

This is useful for multiprocessing and starting up multiple providers.

## Mainnet Fork

The ``ape-foundry`` plugin also includes a mainnet fork provider. It requires using another provider that has access to mainnet.

Use it in most commands like this:

```bash
ape console --network :mainnet-fork:foundry
```

Specify the upstream archive-data provider in your ``ape-config.yaml``:

```yaml
foundry:
  fork:
    ethereum:
      mainnet:
        upstream_provider: alchemy
```

Otherwise, it defaults to the default mainnet provider plugin. You can also specify a ``block_number``.

**NOTE**: Make sure you have the upstream provider plugin installed for ape.

```bash
ape plugins install alchemy
```

## Development

Please see the [contributing guide](CONTRIBUTING.md) to learn more how to contribute to this project.
Comments, questions, criticisms and pull requests are welcomed.

## License

This project is licensed under the [Apache 2.0](LICENSE).
