#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

from setuptools import find_packages, setup  # type: ignore

extras_require = {
    "test": [  # `test` GitHub Action jobs uses this
        "pytest>=6.0,<7.0",  # Core testing package
        "pytest-xdist",  # multi-process runner
        "pytest-cov",  # Coverage analyzer plugin
        "hypothesis>=6.2.0,<7.0",  # Strategy-based fuzzer
    ],
    "lint": [
        "black>=22.3.0,<23.0",  # auto-formatter and linter
        "mypy>=0.910,<1.0",  # Static type analyzer
        "flake8>=3.8.3,<4.0",  # Style linter
        "isort>=5.10.1,<6.0",  # Import sorting linter
        "types-requests",  # NOTE: Needed due to mypy typeshed
    ],
    "doc": [
        "Sphinx>=3.4.3,<4",  # Documentation generator
        "sphinx_rtd_theme>=0.1.9,<1",  # Readthedocs.org theme
        "towncrier>=19.2.0, <20",  # Generate release notes
    ],
    "release": [  # `release` GitHub Action job uses this
        "setuptools",  # Installation tool
        "setuptools-scm",  # Installation tool
        "wheel",  # Packaging tool
        "twine",  # Package upload tool
    ],
    "dev": [
        "commitizen>=2.24",  # Manage commits and publishing releases
        "pre-commit>=2.18",  # Ensure that linters are run prior to committing
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

readme_path, readme_content_type = "./README.md", "text/x-rst"
if os.path.exists("./README.md"):
    readme_path, readme_content_type = "./README.md", "text/markdown"

with open(readme_path) as readme:
    long_description = readme.read()


setup(
    name="ape-foundry",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="""ape-foundry: Ape network provider for Foundry""",
    long_description=long_description,
    long_description_content_type=readme_content_type,
    author="ApeWorX Ltd.",
    author_email="admin@apeworx.io",
    url="https://github.com/ApeWorX/ape-foundry",
    include_package_data=True,
    install_requires=[
        "eth-ape>=0.2.1,<0.3.0",
        "importlib-metadata ; python_version<'3.8'",
        "evm-trace>=0.1.0.a1",
    ],  # NOTE: Add 3rd party libraries here
    python_requires=">=3.7.2,<4",
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
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
