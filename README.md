### Construction

construction

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
SITE_NAME="<YOUR_SITE_NAME>"
APP_REPOSITORY="<APPROVED_CUSTOMER_REPOSITORY_URL>"
APP_RELEASE_REF="<QUALIFIED_RELEASE_REF>"
bench get-app --branch "$APP_RELEASE_REF" construction "$APP_REPOSITORY"
bench --site "$SITE_NAME" install-app construction
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
- [Maintenance](docs/MAINTENANCE.md) — site updates and recovery guidance for administrators.

### Contributing

Development and code review take place in the engineering repository. The customer app
package contains no development hooks, test suite, or CI configuration; customer site
administrators should use the maintenance and onboarding guides instead.

### CI

CI and lint workflows belong to the private engineering repository and are not part of a
customer installation.


### License

mit
