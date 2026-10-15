# Construction ERP — Customer Distribution (F28-D003)

`bench get-app` ships the whole checkout, including documents classified "must not ship"
(program evidence under `docs/ai/`, historical test evidence, session memory). Until the
owner authorises a delivery route, **the full Git checkout is not an approved customer
artifact**. This file defines the curated customer set and how it is verified.

## Customer set

- `construction/` package, **excluding**:
  - `construction/public/dist/js/*.map` (build outputs; regenerable via `bench build`)
  - `construction/tests/*.png` and any future committed screenshots (evidence, not fixtures)
  - `__pycache__` / `*.pyc` (git-ignored; verifier fails if any are tracked)
- Repo root customer files: `README.md`, `LICENSE*`, `pyproject.toml`, `requirements.txt`
- Customer docs: `docs/CUSTOMER_ONBOARDING.md`, `docs/MAINTENANCE.md`,
  `docs/onboarding.md`, `docs/token_reference.md`, `docs/PERMISSION_SETUP.md`, `docs/BILINGUAL_TASK_GUIDES.md`

## Never in the customer set

- `docs/ai/` (program evidence, session memory, manifests, catalogs)
- `docs/feature_reviews/evidence/`, `docs/translation/`, scope-context raw logs
- `orchestrator/`, `tests_offline/` (already excluded from sdist)
- `erpnext-mcp-server/` (outside the package; separate delivery decision, still open)
- `.map` files anywhere under `construction/public/dist/`

## Verification

```bash
python3 scripts/verify_distribution.py
```

The script fails on: any tracked `.map` under `construction/public/dist/`, any tracked
`.png` under `construction/tests/`, any tracked `__pycache__`/`.pyc`, any `setup.py` at the
root (legacy metadata removed 2026-10-14), and any path from the never-ship list appearing
in the customer set. Run it before final `bench get-app` qualification.
