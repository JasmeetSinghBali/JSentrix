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

Please DO NOT use pip ,conda or poetry to install the dependencies. Instead, use uv:

```bash

```

### 📌 Pre-commit

To ensure our standards, make sure to install pre-commit reff: [here](https://pre-commit.com/#install) before starting to contribute.

```bash
# navigate to mcp-server or gateway
uv --cache-dir ./pathtoloca/uv_cache add "pre-commit"
pre-commit install
pre-commit run --all-files
```

### 🧪 Testing

We use `pytest` to test our code. You can run the tests by running the following command:

```bash
# navigate to mcp-server or gateway
pytest ./tests/
```
Make sure that all tests pass before submitting a pull request.

We look forward to your pull requests and can't wait to see your contributions!