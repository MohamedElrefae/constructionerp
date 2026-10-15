### Construction

construction

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app construction
```

### Packaging

Canonical build: Flit via `pyproject.toml` (version 0.0.5, dynamic from
`construction/__init__.py`). `bench get-app` + `bench install-app` is the supported
delivery route; direct `pip install` of legacy `setup.py` is removed. Source maps
(`*.map` under `construction/public/dist/`) are build outputs for local debugging and are
not shipped. Canonical app entry: `/app/construction`.

### Guides

- [Customer onboarding](docs/CUSTOMER_ONBOARDING.md) — installation, first login, roles,
  languages/themes, BOQ lifecycle, support boundary.
- [Bilingual task guides](docs/BILINGUAL_TASK_GUIDES.md) — core tasks and troubleshooting
  in Arabic and English.
- [Maintenance](docs/MAINTENANCE.md) — for engineers maintaining this app.
- [Distribution](docs/DISTRIBUTION.md) — what ships to customers and what never does.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/construction
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


### License

mit
