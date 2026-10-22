# Production Cutover Operational Runbook

**Work item:** `production-cutover-runbook` (Session D)
**Authority:** `docs/ai/BRIEFING_PRODUCTION_CUTOVER_RUNBOOK.md` (Antigravity Engineering Lane, 2026-10-05)
**Base commit:** `234c024` · **branch:** `develop` · **compiled against:** Tier 5J `5933c0d` runner + verifier
**Target site (rehearsal):** `v16.localhost` · **Target site (real cutover):** *production site — insert at execution time*
**Status:** Rehearsed green on `v16.localhost` (`evidence/rehearsal-dry-run.log`); **execution NOT authorized** —
`production_mutation_authorized` remains unset/false.

> **Read this first.** This document is an *operational procedure*, not a change record. Every command in
> §§1–5 has been executed on `v16.localhost` during rehearsal and its observed output is quoted or
> referenced in `evidence/rehearsal-dry-run.log`. Steps marked **[OWNER-GATED]** or **[NOT REHEARSED]**
> were deliberately *not* executed by the rehearsal; they are the only unproven lines in this runbook and
> they are listed again in §10.

---

## 0. Roles, invariants and abort posture

| Role | Responsibility |
|---|---|
| **Operator** (this session / on-call engineer) | Executes §§1–5 verbatim, captures every log, stops at the first red gate. |
| **Verifier** (Antigravity Engineering Lane) | Independently audits gates and evidence, executes the local commit. |
| **Owner** (Mohamed Elrefae) | Sole authority to set `production_mutation_authorized: true` and to authorize a rollback. |

**Invariants — never violated by this runbook or by either helper script:**

1. `production_mutation_authorized` stays `false`/absent unless the **owner** flips it at T-0 (§3.1). Neither
   `cutover_smoke_tests.py` nor `cutover_orchestrator.py` contains code that writes this key.
2. Rehearsal is **read-only against the database**: runner `--dry-run`, verifier (read-only), smoke tests
   (queries only, `frappe.db.rollback()` in `finally`). The only writes the rehearsal performs are
   `bench backup` (backup artefacts) and `bench set-maintenance-mode` (site config, restored in the same step).
3. Zero edits under `apps/frappe` or `apps/erpnext`.
4. **R4 privacy:** no Arabic report cells or Arabic values are printed, logged or committed. Evidence carries
   counts, verdicts, latencies and column/row geometry only.
5. Strictly local: no push, no remote CI, hooks disabled for any local commit by the verifier.
6. **Fail-closed:** every gate exits non-zero on failure; a red gate means *stop*, not *continue*.
7. Redis ports `11000` / `13000` are ephemeral during rehearsal and are terminated when the session ends.

**Abort posture:** the cutover window is aborted (not partially completed) whenever a gate in §1, §2 or §4
fails and cannot be re-established within the window budget. Rollback (§5) is only entered on a *failed T-0
apply* or a *failed post-cutover smoke suite*.

---

## 1. Pre-Cutover Checklist — T minus 24h

Goal: prove that a restore point exists and that the bench is quiesced, before any cutover work begins.

### 1.1 Quiesce writers (F-5J-7, F-D-5)

```bash
# 1. stop scheduling new work
bench disable-scheduler                 # site-scoped when run as: bench --site <site> disable-scheduler
# 2. confirm no concurrent test/bench jobs are running
ps -eo pid,etime,pcpu,args --sort=-pcpu | grep -E "python|maria" | grep -v grep
cat /proc/loadavg                       # note load1/load5; the smoke header records it too
```

> **[F-D-5] Latency gates are only meaningful on a quiesced bench.** During rehearsal, concurrent
> test-suite traffic spiked `Account` link-search P95 to ~30 ms and refused the baseline pin. Re-run after
> quiescing; the smoke script retries `--establish-attempts` times (default 3) and reports `load1/load5`
> on every attempt so contention is visible, never silent.

### 1.2 Maintenance mode ON

```bash
bench --site <site> set-maintenance-mode on
bench --site <site> set-maintenance-mode off   # only if you are still pre-window; see §3.2
```

Verified during rehearsal: the on→off toggle moved `maintenance_mode` `0 → 1 → 0` with `rc=0` both ways
(`rehearsal-dry-run.log`, step `P6a`/`P6b`). Keep the site in maintenance mode for the whole window (§3.2);
the smoke suite refuses `maintenance_mode=1` unless `--allow-maintenance` is passed — **the real cutover
runs smoke tests with maintenance still ON and `--allow-maintenance`, then deactivates it (§4.6).**

### 1.3 Database full backup + validation

```bash
bench --site <site> backup --with-files --compress
```

**Validation (all four are performed automatically by the orchestrator — §6, step `P2`):**

| # | Check | Command / logic | Pass criterion |
|---|---|---|---|
| 1 | Existence | newest `*.sql.gz` under `sites/<site>/private/backups/` | present |
| 2 | Non-trivial size | `os.path.getsize` | ≥ 1024 bytes (rehearsal: **68.0 MiB**) |
| 3 | Age | `mtime` now | ≤ 24 h (rehearsal: **0 min old**) |
| 4 | gzip integrity | full stream read to EOF | no CRC/truncation error |

Optional deeper restorability probe (**executed, quoted for reference**):

```bash
zcat sites/<site>/private/backups/<dump>.sql.gz | grep -c '^CREATE TABLE'      # 771
zcat <dump>.sql.gz | grep -o '^CREATE TABLE `tab[A-Za-z ]*`' | wc -l
# then assert every one of the 15 cutover tables (Company, Account, Cost Center, Warehouse,
# Project, Item Group, Customer Group, Supplier Group, Territory, Department, Task, UOM, Item,
# Customer, Terms and Conditions) plus `tabTranslation` appears in that list.
```

Observed on the rehearsal dump `20261006_021223-v16_localhost-database.sql.gz`: **771 tables, all 15
cutover tables present, `tabTranslation` present.** A full `bench restore` is deliberately **[NOT
REHEARSED]** — it is destructive and needs MariaDB root credentials (§5).

**Backup inventory at rehearsal close** (`sites/v16.localhost/private/backups/`):

| Artefact | Size | Origin |
|---|---|---|
| `20261005_215245-v16_localhost-database.sql.gz` | 71,141,291 B | Tier 5J readiness backup (digest pinned in 5J `MANIFEST.json`) |
| `20261006_021223-v16_localhost-{database,files,private-files,site_config}*` | 68.0 MiB + 171.9 KiB + 1.1 MiB | This runbook's T-24h rehearsal step |

### 1.4 Remaining pre-flight gates (orchestrator `--phase preflight`)

```bash
env/bin/python docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_orchestrator.py \
    --site <site> --phase preflight
```

`P1` site + governance flag (must read `None`/`false` at this point) · `P2` backup (1.3) · `P3` disk headroom
≥ 2 GiB (rehearsal: **2.47 GiB free — see [F-D-6]** ) · `P4` redis PING on `queue:11000` + `cache:13000` ·
`P5` DB connection + `arabic`/`norm` columns + `utf8mb4` on all 15 cutover tables + row census ·
`P6` maintenance-mode state.

**T-24h exit criteria:** every `P*` green, backup validated, writers quiesced. Otherwise abort the window.

---

## 2. Dry-Run Validation — T minus 1h

```bash
env/bin/python docs/ai/work-items/production-migration-readiness/evidence/scripts/run_production_bilingual_migration.py \
    --site <site> --dry-run --allow-sites <site>
```

Assert, in this order (all fail-closed):

1. `rc == 0` (rc `1` = pre-flight/gate failure, rc `2` = classification conflict).
2. `CLASSIFY` line shows **0 `CONFLICT`, 0 `ABSENT`**, and
   `WOULD_WRITE` = 0 **or** the expected non-zero count for a *first-time* production load,
   with `ALREADY_APPLIED` = the remainder.
3. Preflight lines: values bundle sha matches the committed expectation, schema/utf8mb4/hooks present,
   **fresh backup (≤ 24 h)**, redis reachable, governance gate honoured.
4. Immediately afterwards, the post-migration verifier:

```bash
env/bin/python docs/ai/work-items/production-migration-readiness/evidence/scripts/verify_production_bilingual_migration.py \
    --site <site> [--pre <pre_state.json> --snapshot-out <post_state.json>]
```
   `rc == 0` and `VERIFY RESULT: PASS` (V1 counts, V2 norms, V3 frozen fields, V4 trees, V5 probes).

**Observed during rehearsal (idempotent staging site, 188 rows already applied):**

```
CLASSIFY {"ABSENT": 0, "ALREADY_APPLIED": 188, "CONFLICT": 0, "WOULD_WRITE": 0}
RESULT: PASS dry-run, 0 writes, 0 would_write, 188 already_applied (0.4s)
rc=0
VERIFY RESULT: PASS (V1 counts, V2 norms, V3 frozen, V4 trees, V5 probes)   rc=0
```

**T-1h exit criteria:** both `rc == 0`, zero `CONFLICT`/`ABSENT`. A non-zero `WOULD_WRITE` on a *first*
production load is expected and is recorded in the window log; a non-zero `CONFLICT` aborts.

---

## 3. Cutover Execution — T 0

> **[OWNER-GATED]** Steps 3.1 and 3.4 are the only steps that mutate anything. They were **not** executed
> during rehearsal. Everything else in §3 has been executed (dry-run / read-only).

### 3.1 Arm the governance gate **(owner only)**

```bash
# site_config.json is a file edit, not a bench command; edit directly:
#   sites/<site>/site_config.json   ->   "production_mutation_authorized": true
python3 - <<'PY'
import json, sys
p = "sites/<site>/site_config.json"
c = json.load(open(p))
print("production_mutation_authorized =", c.get("production_mutation_authorized"))
PY
```

Equivalent for the rehearsal/dev allowlist: pass `--allow-sites <site>` (the allowlist wins over an explicit
`false` — F-5J-4). **Never** use `--allow-open-gate` outside a rehearsal whose log states the flag is open.

### 3.2 Hold maintenance mode, start a worker

```bash
bench --site <site> set-maintenance-mode on          # confirm: bench --site <site> set-maintenance-mode off shows 0 before
bench --site <site> clear-cache
# a worker must be draining global_search_queue (F-5J-7) during/after apply:
bench worker                                         # or supervisorctl restart frappe-worker:<site>
```

### 3.3 Apply

```bash
env/bin/python docs/ai/work-items/production-migration-readiness/evidence/scripts/run_production_bilingual_migration.py \
    --site <site> --allow-sites <site>
```

`rc == 0` and `RESULT: PASS` with `CONFLICT 0` / `ABSENT 0`. The runner is transactional
(`frappe.db.begin()` … commit) and idempotent (`ALREADY_APPLIED` is a no-op); a `rc == 2` means **nothing was
written** — read the classification, fix, re-run from §2.

### 3.4 Immediate verification

```bash
env/bin/python docs/ai/work-items/production-migration-readiness/evidence/scripts/verify_production_bilingual_migration.py \
    --site <site> --pre <T-1h pre_state.json> --snapshot-out <post_state.json>
```

`rc == 0` + `VERIFY RESULT: PASS`. Compare `post_state` against the T-1h `pre_state` for the frozen
(non-cutover) columns: they must be byte-identical.

---

## 4. Post-Cutover Smoke Tests

```bash
env/bin/python docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_smoke_tests.py \
    --site <site> --expect-gate <open|closed> --baseline evidence/latency-baseline.json \
    [--allow-maintenance]        # only while the site is still in maintenance mode
```

`rc == 0` + `SMOKE RESULT: PASS`; any failed check ⇒ `rc == 1` ⇒ §5.

| ID | Check | Contract | Rehearsal observation |
|---|---|---|---|
| **S1** | Registry bootstrap | 15 cutover doctypes load; `arabic` + `norm` columns present; `utf8mb4` everywhere | PASS (15 doctypes) |
| **S2** | Governance gate | state matches `--expect-gate` (`closed` ⇒ `None`/`false`) | PASS (`production_mutation_authorized=None`) |
| **S3** | **Link-search latency** | every probe correct (queried row present in the result set) **and** P95 within its gate (§7) | PASS — 30/30 probes correct, worst **3.123 ms** (`Account/ar`) |
| **S4** | Transactional link sidecar | measured + disclosed (**no ratified budget** ⇒ ADVISORY, see F-D-3) | ADVISORY — Sales Invoice p95 2.619 ms worst |
| **S5** | Financial reports | `Balance Sheet` + `Profit and Loss Statement` render with ≥2 columns and ≥1 data row; **read-only** (census unchanged before/after) | PASS — 5×10 in 200.6 ms, 5×6 in 52.7 ms; `Account=2102`, `GL Entry=4` unchanged |
| **S6** | Print previews | print HTML for active transaction documents contains `<table>` and the document name | PASS — Sales Invoice / Stock Entry / Material Request rendered; **Purchase Order SKIPPED (0 documents on site) — disclosed, not a pass (F-D-4)** |
| **S7** | Maintenance mode | `maintenance_mode` is off unless `--allow-maintenance` | PASS (`maintenance_mode is off (site serving traffic)`) |
| **S8** | Redis | `queue:11000` + `cache:13000` answer PING | PASS |

The suite ends with `frappe.db.rollback()` in a `finally:` block — a run can never leave a transaction open.

### 4.1 Baseline establishment (T-1h, before the window)

```bash
cutover_smoke_tests.py --site <site> --write-baseline evidence/latency-baseline.json
```

Creates `evidence/latency-baseline.json` (the non-regression pin, §7). Retries up to `--establish-attempts`
(default 3, `--establish-pause` 5 s) and refuses to pin anything worse than `--baseline-cap-ms` (default 10.0).

### 4.2 Human desk checks (not automatable)

1. Desk link search on all 15 doctypes returns the expected rows (Arabic + English query).
2. Bilingual financial report viewer shows both language columns with no leakage of Arabic in cell text
   outside the language in use (R4 — verify visually, do not paste into the log).
3. Open one live Sales Invoice / Material Request print preview end-to-end.
4. Confirm the scheduler was re-enabled: `bench --site <site> enable-scheduler`.

### 4.3 Deactivate maintenance mode

```bash
bench --site <site> set-maintenance-mode off
python3 -c "import json;print(json.load(open('sites/<site>/site_config.json')).get('maintenance_mode'))"  # must print 0
```

**Post-cutover exit criteria:** `SMOKE RESULT: PASS`, S5 census unchanged, maintenance off, gate still in the
expected state for the phase.

---

## 5. Emergency Rollback Protocol

**Trigger (owner decision, one of):**
* T-0 apply returned `rc == 2` **and** the conflict cannot be resolved inside the window; or
* post-cutover smoke (§4) fails after one quiesced retry; or
* data integrity is in doubt (tree/norm/census mismatch reported by the verifier).

**Precondition:** a validated backup from §1.3 that is ≤ 24 h old.

**Sequence — run top to bottom, stop only at the end:**

```bash
# 5.1 freeze
bench --site <site> set-maintenance-mode on
bench disable-scheduler
ps -eo pid,args | grep -E "rq worker|bench worker" | grep -v grep     # stop workers draining the queue

# 5.2 capture the failed state BEFORE overwriting it (evidence for the incident record)
bench --site <site> backup --with-files --compress --backup-path sites/<site>/private/backups/pre-rollback-$(date +%Y%m%d_%H%M%S)

# 5.3 restore  [OWNER-GATED / NOT REHEARSED — destructive, needs MariaDB root credentials]
bench --site <site> restore sites/<site>/private/backups/<T-24h>.sql.gz \
      --with-public-files   sites/<site>/private/backups/<T-24h>-files.tgz \
      --with-private-files  sites/<site>/private/backups/<T-24h>-private-files.tgz \
      --mariadb-root-username <root> --mariadb-root-password '<root-password>'
#        (bench help verified: restore [OPTIONS] SQL_FILE_PATH, --with-public-files,
#         --with-private-files, --db-name, --mariadb-root-username/--mariadb-root-password, --force)

# 5.4 re-apply governance + runtime state
python3 -c "import json;p='sites/<site>/site_config.json';c=json.load(open(p));c.pop('production_mutation_authorized',None);json.dump(c,open(p,'w'),indent=1)"
bench --site <site> migrate                     # only if schema/patch drift is expected after restore
bench --site <site> clear-cache
bench --site <site> set-maintenance-mode off

# 5.5 prove the restore
env/bin/python docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_smoke_tests.py \
    --site <site> --expect-gate closed --baseline evidence/latency-baseline.json
env/bin/python docs/ai/work-items/production-migration-readiness/evidence/scripts/verify_production_bilingual_migration.py \
    --site <site> --pre <pre_state.json>
```

**Rollback is complete only when** S1/S2/S5/S7/S8 pass, the verifier returns `rc == 0`, the census matches
the T-24h pre-state, and `production_mutation_authorized` is absent/false.

> **Disclosed gap:** the restore line is **[NOT REHEARSED]** — executing it destroys the site database, and
> the rehearsal invariant forbids database writes. Restoring into a disposable clone site on MariaDB root
> credentials is the recommended *next* rehearsal before production authorization; it is out of this
> work-item's scope (see `SCOPE.md` §out-of-scope).

---

## 6. Automated Pre-Flight / Post-Flight Wrapper — `cutover_orchestrator.py`

```bash
env/bin/python docs/ai/work-items/production-cutover-runbook/evidence/scripts/cutover_orchestrator.py \
    --site <site> --phase <preflight|dry-run|smoke|rehearsal> [options]
```

| Phase | Steps run |
|---|---|
| `preflight` | P1 site+gate → P2 backup validation (§1.3) → P3 disk → P4 redis → P5 DB/schema → P6 maintenance |
| `dry-run` | D1 migration runner `--dry-run` → D2 post-migration verifier |
| `smoke` | S1 `cutover_smoke_tests.py` |
| `rehearsal` | all of the above (this is what `evidence/rehearsal-dry-run.log` records) |

Options: `--yes` (non-interactive) · `--take-backup` (runs the T-24h `bench backup`) · `--demo-maintenance`
(shows the on→off toggle, leaves the site serving) · `--force` (bypass **only** the backup age gate) ·
`--allow-sites` (default `v16.localhost`) · `--allow-open-gate` (proceed although the gate is open —
rehearsal only) · `--allow-maintenance` · `--establish-baseline` · `--skip-latency` (**diagnostic only —
never for a real cutover**).

**Exit codes:** `0` all gates PASS, `1` any gate fails (summary lines carry `[FAIL] <step>`).
**Safety properties:** no database write; never sets `production_mutation_authorized`; interactive prompts
unless `--yes`; the database name is redacted from all output; fail-closed — a red step stops the phase.

---

## 7. Latency contract (S3/S4 gate semantics)

* **Surface:** `searchable_dropdown.api.search.searchable_link_search` — the desk path
  (`desk_link_search.dispatcher`).
* **Metric:** nearest-rank P95, `min` over `--rounds` rounds of `--samples` timed queries after `--warmup`;
  correctness is checked separately (the probed row must be in the returned set) and is a **hard** gate.
* **Gate:** each probe is compared against
  * **absolute ADR Tier-1 ceiling `1.50 ms`** (`docs/ai/work-items/bilingual-performance-sla.md`) if it was
    compliant in the baseline pin, else
  * **`baseline_p95 × 1.25`** (`--regression-tolerance`, non-regression) if it breached at baseline.
* **`S3-absolute`** always reports ADR Tier-1 compliance separately as **ADVISORY**, so pre-existing drift is
  disclosed but is never mistaken for cutover-induced regression.
* **Establish mode** (`--write-baseline`, no pin yet): pin only if every P95 ≤ `--baseline-cap-ms`
  (default 10.0 ms), retried `--establish-attempts` times with `load1/load5` reported each attempt.
* `--skip-latency` exists for diagnosis; a real cutover must never use it (the script says so in its log line).
* **Query shape:** S3 probes with the *full stored value* of one row per doctype (a worst case for
  `LIKE %…%`), not a short typeahead prefix. Both shapes were measured for `Account` and land in the same
  band (F-D-1, `evidence/account-latency-investigation.log`), so the shape does not change any verdict here —
  but a future re-calibration must state which shape the ceiling governs.

---

## 8. Findings from rehearsal (F-D-*)

| ID | Finding | Disposition |
|---|---|---|
| **F-D-1** | **`Account` link search sits at or above the ADR Tier-1 ceiling of 1.50 ms; the other 14 cutover doctypes are 0.65–1.10 ms.** Measured on the gated desk surface: **3.075 ms** (S3 pin, full-value query), **2.698–3.340 ms** across Arabic-prefix / ASCII-prefix / full-value shapes, **1.977 ms** with a company filter applied. ADR-§4 methodology on the same data returns native 1.402–1.449 ms / governed 1.567–1.668 ms (ratio 1.081–1.190x, run-to-run spread). Unfiltered row scope (2102 rows vs 86) accounts for **+1.364 ms** of the desk-surface cost; the remainder persists with the filter. The ADR's frozen pin (native 1.322 / governed 1.482 ms) was calibrated on the synthetic fixture prefix `CT-T3-` over a handful of rows and **does not transfer** to production query text. Full method, all five sections and the numbers: `evidence/account-latency-investigation.log`. | Recorded in `latency-baseline.json` as `compliant:false`; gated by `baseline×1.25` thereafter; reported every run as `S3-absolute ADVISORY`. **Not cutover-induced** — 3.075 ms before the dry-run vs 3.123 ms after, identical within noise, and no cutover step touches Account SQL. Owner decision required (§10 item 5): either scope the cutover link field, re-index the Account search fields, or amend the ADR to state which surface/query shape Tier-1 governs. |
| **F-D-2** | Establishing the pin while other bench jobs ran produced P95 ≈ 30 ms and **refused** the pin (`baseline refused: P95 above --baseline-cap-ms 10.0`). | Re-run on a quiesced bench (§1.1). Smoke now retries up to `--establish-attempts` with load printed — a refusal is loud, never silent. |
| **F-D-3** | **Transactional link sidecar** (Sales Order / Material Request / Purchase Order / Sales Invoice, p95 0.78–2.75 ms) has **no ratified latency budget** in any ADR. | Measured and disclosed as **S4 ADVISORY** every run. A budget decision is an owner action; it is *not* silently gated. |
| **F-D-4** | `Purchase Order` has **0 documents** on the rehearsal site, so its print preview cannot be exercised. | `S6 SKIP … (nothing to preview — disclosed, not a pass)`. Must be re-run on a site that carries live POs before production. |
| **F-D-5** | Concurrent test traffic makes S3 fail spuriously (F-D-2); load average on the box is low (12 CPUs, load1 ≈ 2.4) — the spike is **DB lock contention**, not CPU. | Quiesce step §1.1 + attempt transparency in the smoke header. |
| **F-D-6** | Bench disk is **96% used, 2.47 GiB free**; the P3 gate is 2 GiB. A second `bench backup` (68 MiB) leaves little headroom. | Keep exactly one ≤24 h backup before the window; prune older dumps **that are not digest-pinned** by an earlier `MANIFEST.json`; raise P3 threshold if the site grows. |
| **F-D-7** | `frappe.get_print` resolves `assets/assets.json` relative to CWD, so scripts must run from the bench root (or `chdir(sites/)`). | Both helper scripts anchor paths off `BENCH`; the smoke suite does `os.chdir(SITES)`. Documented in the command lines above. |
| **F-D-8** | Financial reports must be generated against the **ledger-bearing** company (4 GL rows); the newest `Company` on this site has 0 GL rows and would render an empty report. | S5 selects the company by GL presence and records the geometry, never the values. |

---

## 9. Command & exit-code reference

| Command | Exit codes |
|---|---|
| `run_production_bilingual_migration.py --dry-run\|apply` | `0` pass · `1` pre-flight/gate failure · `2` `CONFLICT`/`ABSENT` classification (zero writes) |
| `verify_production_bilingual_migration.py` | `0` `VERIFY RESULT: PASS` · `1` any V-check failed |
| `cutover_smoke_tests.py` | `0` `SMOKE RESULT: PASS` · `1` any S-check failed |
| `cutover_orchestrator.py` | `0` `RESULT: PASS` · `1` any gate failed |
| `bench --site <site> backup --with-files --compress` | `0` on success (prints a Backup Summary) |
| `bench --site <site> set-maintenance-mode on\|off` | `0` on success |
| `bench --site <site> restore <dump> …` | bench's own validation; **owner-gated, not rehearsed** |

---

## 10. Evidence map & sign-off

| Deliverable | Path |
|---|---|
| Scope descriptor + rehearsal verification record | `SCOPE.md` |
| This runbook | `PRODUCTION_CUTOVER_RUNBOOK.md` |
| Post-cutover smoke suite | `evidence/scripts/cutover_smoke_tests.py` |
| Pre/post-flight orchestrator | `evidence/scripts/cutover_orchestrator.py` |
| Rehearsal execution log | `evidence/rehearsal-dry-run.log` |
| 6 lints + ADR reconciler (19/19) | `evidence/gates.log` |
| Latency baseline pin | `evidence/latency-baseline.json` |
| F-D-1 latency investigation (five sections, production-shaped queries) | `evidence/account-latency-investigation.log` |
| Manifest #35 (sha256 of every artefact) | `evidence/MANIFEST.json` |

**Not rehearsed / owner-gated — must be closed before production authorization:**

1. §3.1 setting `production_mutation_authorized: true` (owner).
2. §3.3 first-time `WOULD_WRITE` apply against a production database (all rehearsed applies were
   `ALREADY_APPLIED` no-ops on staging).
3. §5.3 `bench restore` drill on a disposable clone site.
4. §4.2 visual desk/print checks on a site that carries live Purchase Orders (F-D-4).
5. F-D-1: decide whether `Account` link search must meet the 1.50 ms Tier-1 ceiling.

**Operator sign-off:** ________________ (date: ________)  **Verifier sign-off:** ________________  **Owner authorization:** ________________
