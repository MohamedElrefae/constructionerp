# Clean isolated Python environment build

**Date:** 2026-10-05
**Purpose:** Resolve the Python 3.14 clean-install failure in the newly created `rebuilt-env` and bind the resulting package metadata to source provenance. This is package-install evidence only; no Frappe site/database command, application test, or runtime security approval is included.

## Result

The clean Python 3.14.5 environment installed 177 resolved public/runtime requirements with `uv 0.11.14`. Exact local Frappe, ERPNext, and Construction sources were then installed editable with `--no-deps`. `pip check` reports `No broken requirements found.` The final environment freeze contains 180 distributions, including those three local apps and pip.

The initial build failed on `PyPika==0.48.9` from PyPI: its source build evaluates the removed `ast.Str` API on Python 3.14. Frappe's pinned source metadata shows why removing PyPika would be incorrect. Frappe declares `PyPika @ git+https://github.com/frappe/pypika@2c50e6142b2d61d2d243e466fdd5dc03b3d918f2`; Frappe's query builder imports `pypika`, and ERPNext production modules also import `pypika` directly. The distribution name and version alone do not identify the patched source.

Frappe also declares `gunicorn @ git+https://github.com/frappe/gunicorn@bb554053bb87218120d76ab6676af7015680e8b6`. The rebuild replaces the two same-version PyPI records with those exact public Git source references in [REBUILT_PUBLIC_REQUIREMENTS.txt](REBUILT_PUBLIC_REQUIREMENTS.txt). Neither dependency was removed. No other dependency was excluded: the inherited requirement inventory includes packages that may support runtime, tests, or bench tooling, and this bounded task did not establish grounds to remove them.

## Provenance and evidence

- Frappe: `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`, distribution `frappe 16.18.1`.
- ERPNext: `2807c9f08fff3f161c0a2e10745a26aa6331ffd5`, distribution `erpnext 16.18.3`.
- Construction: candidate checkout `fd218cf6e3682dc97fc9e90480cf31261a2297ed`, distribution `construction 0.0.5`. At the captured build fingerprint, the checkout had concurrent modifications in `construction/api/bilingual_reports.py`, `construction/hooks.py`, `construction/public/css/modern_theme.css`, and `construction/public/js/theme_loader_v24.js`; the editable install points to that live checkout. The build manifest records a source-tree and diff digest for this state. This metadata build does not validate those changes; preserve their owner’s review boundary.
- Installed PyPika `0.48.9` direct URL records commit `2c50e6142b2d61d2d243e466fdd5dc03b3d918f2`; Gunicorn `23.0.0` direct URL records commit `bb554053bb87218120d76ab6676af7015680e8b6`.
- Requirement file SHA-256, installed package metadata, runtime source SHAs, and the working-tree status at the captured build fingerprint are recorded in the private [build manifest](/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/end-to-end-20261005/build/rebuilt-env-manifest.json). The resolved package freeze is at [rebuilt-env-freeze.txt](/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/end-to-end-20261005/build/rebuilt-env-freeze.txt).
- The original failure is retained at `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/logs/clean-rebuild-20261005.log`. The successful requirements resolution, editable local install, and `pip check` logs are `clean-rebuild-20261005-v2.log`, `clean-rebuild-20261005-local-apps.log`, and `clean-rebuild-20261005-pip-check.log` in that same private Bench logs directory.

This clean build confirms that the recorded dependency declarations install together and that their metadata requirements are consistent. It does not confirm Frappe application imports, browser behavior, fresh site installation, business tests, vendor security, or release readiness. The owner decides whether and how to adopt this isolated environment.
