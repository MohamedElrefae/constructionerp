# F31 — Preparation: snapshot binding, checkout inspection, site plan (evidence)

Date: 2026-10-14 · HEAD: `fa380226d641f32f749c7ae003f82eeb6404ba2c` (repo has moved past the
`09c8cb1` cited in the program summary — all references below use the measured HEAD).

## 1. Delivery-method binding

`bench get-app` retrieves **committed** repository content only. The 126 uncommitted F38-batch
entries would silently not ship, so testing the worktree while calling it "the candidate"
would be false evidence. Two delivery methods, labelled:

| Method | Content | Label |
|---|---|---|
| **Snapshot** (this qualification) | HEAD `fa38022` + tracked diff + 81 untracked files (all hashed below). **No commit; history untouched.** | `worktree snapshot 2026-10-14` |
| **`bench get-app`** (final) | the exact committed candidate, after the F38 batch lands | awaits commit; must re-run this qualification |

Snapshot manifest (`/tmp/opencode/f31-snapshot-manifest.json`):

- `tracked_diff_sha256`: sha256 of `git diff HEAD` (2,377 lines) — recorded in manifest
- untracked entries: 79 paths → 81 files, each sha256-hashed
- pyproject line-ending discipline: the file uses CRLF; an earlier edit normalised it and
  produced 94/86 phantom churn — restored so the diff is exactly the 10-line sdist change.

## 2. Checkout inspection (Git delivery route — wheel/sdist exclusions do not protect it)

| Check | Result |
|---|---|
| Live UAT credentials (`F04pm#2026!`, `TmpAdmin#2026!`, …) in repo | **none found** (all patterns) |
| Historical placeholder passwords (`"admin"`, `ct-w60x-evidence-N`) | present in old evidence scripts under `docs/feature_reviews/evidence/` and `docs/ai/work-items/scope-context-portability/evidence/` — pre-program test fixtures, not live credentials; classified, not removed (historical evidence preservation) |
| Private keys / API keys / secrets | none found |
| Tracked bytecode (`__pycache__` / `.pyc`) | **0 tracked** (235 dirs / 1,589 files on disk are git-ignored) |
| `.bak` / `.orig` / `.rej` | none remain (the two Sidebar `.bak` files were removed in F30) |
| `dist/` build output | absent (removed after F28 verification; git-ignored) |
| `node_modules` | absent |

## 3. Site qualification plan (isolated sites — pending MariaDB root credential)

| Site | Purpose | Steps |
|---|---|---|
| `f31fresh.localhost` | fresh install | new site → install app (snapshot) → migrate → migrate again (idempotence) → permission reconciliation → ordinary-role access → Sidebar/workspaces → assets → scaffold tables present |
| `f31upgrade.localhost` | upgrade from prior baseline | new site → restore F02 backup `20261013_052916` (68 MB, verified present) → install app → migrate → financial history / settings / scaffolds preserved |

Blocked on: MariaDB root password (not in bench config; `~/.my.cnf` password rejected).
Owner selected "provide root password" — sites to be created on receipt.

## 6. Existing-site evidence (2026-10-14 — migrate passed, second migrate clean)

- Migration replay: first pass refused on F31-D001 drift (fail-closed holds); after the file v1.1 update + origin re-stamps, migrate **passed** through `after_migrate` hooks; **second migrate exit=0**. Counts unchanged: 36/94/12/235/45.
- Permission reconciliation: **matches baseline** (14 doctypes, 0 drift).
- Financial history: BOQ line-total sum 209,855.00 across 94 items; 162 structures / 188 files — all unchanged across every migrate attempt.
- Settings: `enable_scope_context` restored **0 → 1** with persisted readback (see F31-D002); `enable_variation_orders` = 1.
- Workload sampling (read-only, maintainer persona): price_history 9 rows in 0.13s; missing_analysis 4 rows in 0.03s; BOQ-item list in 0.00s. No concurrency/volume claim (D1 profile pending F37).
- Backups: fresh verified sets for all three sites (rehearsal `20261014_234948`, localhost `20261014_235018`, v16.localhost `20261014_235052`; `gzip -t` clean).
- Patch comparison: 39 in `patches.txt`, 40 logged (one historical extra), **zero pending**.

## 7. Status

F31 **rehearsal migration/replay verified** (migrate + clean second migrate, §6); **F31
incomplete** pending fresh-install and isolated-upgrade qualification (DBA blocker). The v1.1
article change carries the owner direction only — the retained v1.0 reviewer names are base
provenance, not a fresh quorum. F31-D001 resolved for migration; F31-D002 resolved for the
current ON posture, with the unexplained OFF transition retained as an operational finding.

## 8. Private-documentation classification (Git delivery route)

Wheel/sdist exclusions do not protect `bench get-app`, which ships the whole checkout. The
checkout carries three documentation classes:

| Class | Paths | Content | Git-delivery verdict |
|---|---|---|---|
| Customer-facing | `README.md`, `docs/onboarding.md`, `docs/token_reference.md`, user guides | install/build/entry statements, token refs | shippable |
| Internal program evidence | `docs/ai/` (work items, SESSION_MEMORY, catalogs, manifests), `DOCUMENTATION_INDEX.md` | 43 credential-procedure mentions in SESSION_MEMORY alone; 27 evidence docs naming internal site hostnames; fixture identity emails; rotation procedures. **No live credential values** (verified §2), but operational detail that must not reach customers | **must not ship** — requires a delivery route that excludes it, or an explicit owner decision |
| Historical test evidence | `docs/feature_reviews/evidence/`, `docs/translation/`, scope-context logs | old placeholder passwords, internal hostnames, raw run logs | **must not ship** — same condition |

F28-D003 (1,615 tracked files outside `construction/`) stays the vehicle for this decision.
F31 migration success will not close it. F29 guides and F27 authorization stay open likewise.
