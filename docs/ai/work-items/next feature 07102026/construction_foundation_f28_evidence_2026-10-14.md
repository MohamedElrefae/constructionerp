# F28 — Delivery artifact hygiene, packaging decisions (evidence)

Date: 2026-10-14 · Builder: isolated venv (`flit_core` 4.1.0, Flit backend) — bench env untouched.

## 1. Decisions implemented

| Decision | Action | Proof |
|---|---|---|
| Source maps excluded from customer artifacts, retained privately | Committed `.map` was already git-ignored build output (`dist/` in `.gitignore`); Flit sdist exclude extended with `construction/public/dist/js/*.map`; map hash recorded below | wheel + sdist contain **0** `.map` members |
| Flit/`pyproject.toml` canonical; conflicting legacy metadata removed | `setup.py` (version 0.1.0 vs canonical 0.0.5) deleted; the only consumers were CI pip-cache keys — both `hashFiles` lines updated to drop it | `python -m flit build` succeeds without it; wheel METADATA `Version: 0.0.5` |
| Generated test residue excluded, runtime assets preserved | 12 committed browser-test PNGs moved from `construction/tests/` (ships in the wheel) to `docs/.../f28-test-screenshots/` (outside the package); theme CSS, dist bundle `.js`, fixtures all retained | wheel contains 0 test PNGs; no test reads them (verified — they are outputs, not fixtures) |
| Manifest refreshed | New input manifest `construction_foundation_build_input_manifest_2026-10-14.json` (2,141 tracked rows with sha256); build outputs in `dist/` removed after verification (git-ignored, regenerable) | earlier F28-D006 hashes explicitly no longer bind these changes |

Removed source-map hash (private debugging reference; regenerates on every `bench build`):
`construction.bundle.2XKAHIYO.js.map` sha256 `83dbccbb…cea33a`.

## 2. Build verification (current candidate)

- `python -m flit build` → `construction-0.0.5.tar.gz` + `construction-0.0.5-py3-none-any.whl`,
  1,239 members each.
- Exclusion sweep: `.map` 0/0, `setup.py` 0/0, `tests/02_*` 0/0, `orchestrator/` 0/0,
  `tests_offline/` 0/0 (sdist/wheel).
- Version single-sourced: wheel METADATA `Name: construction, Version: 0.0.5` (dynamic from
  `construction/__init__.py`).
- Note: the MCP bridge (`erpnext-mcp-server/`) lives outside the `construction` package and
  ships in neither artifact — its delivery is a separate decision, still open.

## 3. F27 security posture (prerequisite note)

The UAT-D005 retrieval fix proves retrieval only. The bridge binds `SITE_NAME =
"v16.localhost"`, initialises Frappe without a session user (Administrator-backed), and
authorises by DocType allowlist with no per-user permission or scope check. It **remains a
security finding** and stays unavailable to customer users until its authorization boundary
is qualified under full F27. This does not block migration testing (F31), which uses no
bridge path.

## 5. Separate clean repository (D4 preparation)

Per the approved correction, the candidate was prepared in a scratch repo
(`/tmp/opencode/customer-repo`), not as an orphan branch: copied customer set → single
squashed commit → no remotes. Verification: exactly **1 reachable commit**, 1 branch,
**0 tags**, **0 remotes**; `git log --all` over `docs/ai`, `orchestrator`,
`tests_offline`, `erpnext-mcp-server`, `setup.py` is empty; **1,244 tracked files,
byte-identical** to the staged manifest (no mismatch, missing, or extra). The scratch repo
is volatile local preparation only — the durable record is this method plus the staged
manifest in the program repo. Publication and customer delivery require separate approval.

**Re-verification 2026-10-15** (the `/tmp` cleanup had wiped the 2026-10-14 scratch repo;
script preserved durably at `isolated-qualification-evidence-2026-10-15/rebuild_delivery_repo.py`):
re-staged (1,252 files, verification PASSED) → rebuilt fresh → **1 commit (`1f575b2b…`),
0 remotes, 0 tags, 0 never-ship path leaks, 1,252/1,252 byte-identical, 0 mismatches**.
Also fixed during rebuild: theme-CSS filenames contain spaces, so hash/tracking
comparisons must use NUL-delimited `git ls-files -z` (space/newline splitting falsely
reports the count). Standing rule: **re-run this rebuild+verify at delivery time from the
committed candidate**, since the scratch repo lives in volatile `/tmp`.

F28 **packaging decisions implemented and route preparation verified** (separate clean repo,
§5); artifact rebuilt and verified. Publication and customer delivery require separate
approval. F29 audience guides delivered; `.map`-for-cloud-builds policy stays an owner decision.
