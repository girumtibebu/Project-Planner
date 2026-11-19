### Event Planner

Event planner app made for Eternal Media

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app event_planner
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/event_planner
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.

### Handoff Documentation

For client-team takeover and long-term maintainability, use this reading order:

1. [Developer Handoff Guide](docs/HANDOFF_GUIDE.md)
2. [Architecture](docs/ARCHITECTURE.md)
3. [Interaction Flows](docs/INTERACTION_FLOWS.md)
4. [Extending the Product](docs/EXTENDING_THE_PRODUCT.md)
5. [Developer Runbook](docs/DEV_RUNBOOK.md)


### License

mit
