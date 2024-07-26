#!/usr/bin/env python

from setuptools import find_packages, setup

extras_require = {
    "test": [  # `test` GitHub Action jobs uses this
        "pytest>=6.0",  # Core testing package
        "pytest-xdist",  # Multi-process runner
        "pytest-cov",  # Coverage analyzer plugin
        "pytest-mock",  # For creating mocks
        "hypothesis>=6.2.0,<7.0",  # Strategy-based fuzzer
        "ape-alchemy",  # For running fork tests
        "ape-polygon",  # For running polygon fork tests
    ],
    "lint": [
        "black>=24.4.2,<25",  # Auto-formatter and linter
        "mypy>=1.11.0,<2",  # Static type analyzer
        "types-setuptools",  # Needed for mypy type shed
        "types-requests",  # Needed for mypy type shed
        "types-PyYAML",  # Needed for mypy type shed
        "flake8>=7.1.0,<8",  # Style linter
        "flake8-breakpoint>=1.1.0,<2",  # Detect breakpoints left in code
        "flake8-print>=5.0.0,<6",  # Detect print statements left in code
        "isort>=5.13.2,<6",  # Import sorting linter
        "mdformat>=0.7.17",  # Auto-formatter for markdown
        "mdformat-gfm>=0.3.5",  # Needed for formatting GitHub-flavored markdown
        "mdformat-frontmatter>=0.4.1",  # Needed for frontmatters-style headers in issue templates
        "mdformat-pyproject>=0.0.1",  # Allows configuring in pyproject.toml
    ],
    "doc": [
        "Sphinx>=6.1.3,<7",  # Documentation generator
        "sphinx_rtd_theme>=1.2.0,<2",  # Readthedocs.org theme
        "towncrier>=19.2.0, <20",  # Generate release notes
    ],
    "release": [  # `release` GitHub Action job uses this
        "setuptools",  # Installation tool
        "setuptools-scm",  # Installation tool
        "wheel",  # Packaging tool
        "twine",  # Package upload tool
    ],
    "dev": [
        "commitizen",  # Manage commits and publishing releases
        "pre-commit",  # Ensure that linters are run prior to committing
        "IPython",  # Console for interacting
        "ipdb",  # Debugger (Must use `export PYTHONBREAKPOINT=ipdb.set_trace`)
    ],
}

# NOTE: `pip install -e .[dev]` to install package
extras_require["dev"] = (
    extras_require["test"]
    + extras_require["lint"]
    + extras_require["doc"]
    + extras_require["release"]
    + extras_require["dev"]
)


with open("./README.md") as readme:
    long_description = readme.read()


setup(
    name="ape-foundry",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="""ape-foundry: Ape network provider for Foundry""",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ApeWorX Ltd.",
    author_email="admin@apeworx.io",
    url="https://github.com/ApeWorX/ape-foundry",
    include_package_data=True,
    install_requires=[
        "eth-ape>=0.8.10,<0.9",
        "ethpm-types",  # Use same version as eth-ape
        "eth-pydantic-types",  # Use same version as eth-ape
        "evm-trace",  # Use same version as ape
        "web3",  # Use same version as ape
        "yarl",  # Use same version as ape
        "hexbytes",  # Use same version as ape
    ],
    python_requires=">=3.8,<4",
    extras_require=extras_require,
    py_modules=["ape_foundry"],
    license="Apache-2.0",
    zip_safe=False,
    keywords="ethereum",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={"ape_foundry": ["py.typed"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
