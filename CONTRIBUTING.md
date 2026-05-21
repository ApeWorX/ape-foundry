# Development

To get started with working on the codebase, use the following steps prepare your local environment:

```bash
# clone the github repo and navigate into the folder
git clone https://github.com/ApeWorX/ape-foundry.git
cd ape-foundry

# install the developer dependencies
uv sync --group dev
```

## Prek Hooks

We use [`prek`](https://github.com/j178/prek) to run repository hooks and keep contributor workflows consistent.
Use of `prek` is not a requirement, but is highly recommended.

Install hooks locally from the repo root:

```bash
uv run prek install
```

Committing will now automatically run the local hooks and ensure that your commit passes all lint checks.

## Running the docs locally

First, make sure you have the docs-related tooling installed:

```bash
uv sync --group docs
```

Then, run the following from the root project directory:

```bash
sphinx-ape build .
```

For the best viewing experience, use a local server:

```bash
sphinx-ape serve .
```

Then, open your browser to `127.0.0.1:1337` and click the `ape` directory link.

You can also use the `--open` flag to automatically open the docs:

```bash
sphinx-ape serve . --open
```

## Pull Requests

Pull requests are welcomed! Please adhere to the following:

- Ensure your pull request passes our linting checks
- Include test cases for any new functionality
- Include any relevant documentation updates

It's a good idea to make pull requests early on.
A pull request represents the start of a discussion, and doesn't necessarily need to be the final, finished submission.

If you are opening a work-in-progress pull request to verify that it passes CI tests, please consider
[marking it as a draft](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests#draft-pull-requests).

Join the ApeWorX [Discord](https://discord.gg/apeworx) if you have any questions.
