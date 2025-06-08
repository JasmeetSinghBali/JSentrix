# 💫 Contributing to jsentrix

Let us make contribution easy, collaborative and fun.

## 🎯 Submit your Contribution through PR

To make a contribution, follow these steps:

1. Fork and clone this repository
2. Do the changes on your fork with dedicated feature branch `feature/f1`
3. If you modified the code (new feature or bug-fix), please add tests for it
4. Include proper documentation / docstring and examples to run the feature
5. Ensure that all tests pass
6. Submit a pull request

For more details about pull requests, please read [GitHub's guides](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).

### 📁 Clean Architecture File Placement Guide

> 📝 General Rules
```bash
Domain is the core. It should never import from other layers.

Application coordinates domain logic and use cases.

Infrastructure implements the “how” (databases, APIs).

Interface is the “entrypoint” for users or external systems.

Utils are for cross-cutting, generic code.
```
> 🚦 When in Doubt
```bash
Ask: Is this file about business rules? → domain/

Is it about how the app works or coordinates? → application/

Is it a concrete implementation or integration? → infrastructure/

Is it an adapter for the outside world? → interface/

Is it a generic helper? → utils/
```

### 📦 Package manager

We use `uv` as our package manager. You can install uv by following the instructions [here](https://docs.astral.sh/uv/getting-started/installation/).

Please DO NOT use pip ,conda or poetry to install the dependencies for gateway and mcp_server. Instead, use uv:

```bash
# seperately in gateway/ and mcp_server/
uv sync
# uv sync will:
# Creates/Updates the Virtual Environment
# Installs Dependencies
# Handles Lockfile (uv.lock)
# Installs Project in Editable Mode
```

### 📌 Pre-commit

To ensure our standards, make sure to install pre-commit reff: [here](https://pre-commit.com/#install) before starting to contribute.

```bash
# navigate to Jsentrix
python -m venv .venv
# activate
pip install pre-commit
pre-commit install
pre-commit run --all-files

```

### 📌 Sphinx-doc

```bash
NOTE- sphinx shud also be installed in root jsentrix venv only
pip install sphinx
sphinx-quickstart docs # one time
# Separate source and build directories: yes
# Project name: JSentrix
# Author name: Jasmeet Singh Bali
# Project release/version: 1.0
# Use autodoc extension: no (add it manually)
# Use intersphinx extension: no
# Use todo extension: no
# Use coverage extension: no
# Use mathjax extension: no
# Use viewcode extension: no
# Use githubpages extension: no

# edit generated docs- docs/source/conf.py
# at top
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))
# in extension add
'sphinx.ext.autodoc'
# to generate api docs
# sphinx-apidoc -o docs/api . # generates docs/api/modules.rst


# scanning gateway and mcp_server and put generated .rst files into docs/source/api
sphinx-apidoc -o docs/source/api/gateway -e -M gateway/src
sphinx-apidoc -o docs/source/api/mcp_server -e -M mcp_server
# -o docs/source/api/gateway puts gateway docs in their own subfolder.
# -e creates a separate page for each module.
# -M puts each module on its own page, not just subpackages.


# in docs/source/index.rst use restructuredtext to update docs or custom sections with .rst files
# inside of docs/
make clean html

#💡  NOTE- IN case any module not found error then install those via pip in root jsentrix/.venv then delete docs/build and docs/source/api and then rerun sphinx-apidoc for gateway and mcp_server and finally make clean html commands inside docs
```


### 📌 Instrumentation/Tracing

```bash
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html

```

### 🧪 Testing

We use `pytest` to test our code. You can run the tests by running the following command:

```bash
# navigate to mcp_server or gateway
pytest ./tests/
```
Make sure that all tests pass before submitting a pull request.

We look forward to your pull requests and can't wait to see your contributions!