# Construction ERP — Customer Distribution (F28-D003)

`bench get-app` ships the whole checkout, including documents classified "must not ship"
(program evidence under `docs/ai/`, historical test evidence, session memory). Until the
owner authorises a delivery route, **the full Git checkout is not an approved customer
artifact**. This file defines the curated customer set and how it is verified.

## Customer set

- `construction/` package, **excluding**:
  - all of `construction/tests/` (test code remains in the maintainer repository and CI)
  - all of `construction/data/localization/` (site-specific qualification manifests,
    export metadata, vendor catalog gate inputs, and localization qualification evidence)
  - every `*.map` under `construction/public/dist/` (build outputs; regenerable via `bench build`)
  - `__pycache__` / `*.pyc`
- Repo root customer files: `README.md`, `LICENSE*`, `pyproject.toml`, `requirements.txt`
- Customer docs: `docs/CUSTOMER_ONBOARDING.md`, `docs/MAINTENANCE.md`,
  `docs/onboarding.md`, `docs/token_reference.md`, `docs/PERMISSION_SETUP.md`, `docs/BILINGUAL_TASK_GUIDES.md`

## Never in the customer set

- `docs/ai/` (program evidence, session memory, manifests, catalogs)
- `docs/feature_reviews/evidence/`, `docs/translation/`, scope-context raw logs
- `orchestrator/`, `tests_offline/` (already excluded from sdist)
- `erpnext-mcp-server/` (outside the package; separate delivery decision, still open)
- `.map` files anywhere under `construction/public/dist/`
- customer tests, vendor-upgrade review JSON, and qualification data under `construction/`

## Verification

```bash
STAGE_DIR="/tmp/opencode/customer-dist-<unique-name>"
python3 scripts/stage_distribution.py --out "$STAGE_DIR"
python3 scripts/verify_staged_distribution.py --dir "$STAGE_DIR"
```

The stager reads only committed `HEAD` blobs; untracked, ignored, and working-tree changes
cannot enter the artifact. Its manifest binds the exact source commit and each staged file
hash. It only accepts a new, nonexistent output path outside and not an ancestor of the app
checkout; it never removes an existing path. The staged verifier checks the shared never-ship
policy, required runtime files and a nonempty license, customer allowlist, document links,
per-file hashes, and every canonical `content:` reference on a Released translation row.
Staging is local preparation only, not a customer install source. After owner review, transfer
the verified tree into the approved curated private customer repository and qualify that exact
release ref before documenting any customer `bench get-app` command. Never install the
engineering checkout or its development branch for a customer.
