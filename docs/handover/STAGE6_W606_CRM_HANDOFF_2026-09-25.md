---
date: 2026-09-25
author: Agent (Antigravity / opencode session)
status: HANDOFF — W6-6 CRM cycle CLOSED; next Stage-6 scope NOT yet authorized
scope: Stage 6 governed translation cycles on `v16.localhost`
---

# Handoff — W6-6 CRM, Support & Maintenance cycle closed; next Stage-6 work

Read this before touching `SESSION_MEMORY.md`, the localization gate, or any
`stage6_*` file. Repo root: `/home/mohamed/frappe-bench/apps/construction`
(branch `develop`).

## 1. Where the repo is right now

| Item | Value |
|---|---|
| Cycle closure commit | `3344546` — `feat(localization): close W6-6 CRM support maintenance` |
| Handoff commits | `f5420a4` (publish) and `797771e` (cycle-bound HEAD wording) |
| `origin/develop` | **in sync with local `develop`** (verified 2026-09-25; see the addendum in §8 — the earlier "local only, not pushed" wording in this file and in `SESSION_MEMORY.md` was true when written and is now stale) |
| Push state | the three session commits were published to `origin` by an **external** action at 2026-09-25 01:55:09 +0300, not by the agent; no agent push occurred. **Do not push anything further without an explicit owner request.** |
| Branch / divergence | `develop`, 0 ahead / 0 behind (`git rev-list --left-right --count origin/develop...HEAD`) |
| Last cycle | W6-6 CRM, Support & Maintenance — **CLOSED**, no in-flight work |
| Site | `v16.localhost` only (governed non-production test); production and Stage 8 rollout untouched/gated |
| Catalog / decisions | 3,364 / 3,364 rows (catalog SHA `ad737758…`, decisions SHA `84a6a078…`) |
| Freshness | `packaged_rows=3364`, `critical_pass=true`, no drift |
| Inventory | 21,781 rows, Merkle `f1d00e38582fd5604b11355b744376b408f100a74ba376d59ce276d7f1c2e4e1` |

Closed-cycle facts you can rely on (also in `SESSION_MEMORY.md` §2026-09-25 and
`docs/translation/stage6-w606-crm-support-maintenance-cycle-executed-2026-09-24.md`):

- Exact authorized scope: `docs/translation/stage6_w606_crm_support_maintenance_rows_2026-09-24.csv`,
  119 rows, SHA-256 `a77b43a908859c0aea3e2c58525ec3765772c09af8617f1f17fb8c8bf12833f9`.
- Final disposition: **38 released + 76 preserved site overrides + 4 deferred
  source defects + 1 technical exception (`fieldname`)**. The earlier 42-row /
  3,368 expectation is superseded — do not resurrect it.
- Import `38 created`; post-DRY `3364/0/0/3364/0`, drift 0; sync `0/0`.
- UAT preflight PASS (13,666 `ar` boot messages), browser evidence **9/9**,
  114/114 payload+preserved keys exact, 5 excluded rows absent, no page errors.
- Tests: standalone **92/92**; module aggregate **271/271** (the aggregate covers
  11 modules and *includes* the 92 standalone — do not add them together).
- Gates: `STAGE2_EVIDENCE_BOOTSTRAP=1 python3 scripts/check_localization_gates.py --skip-evidence`
  → `errors=0`, `csv_rows=3364`; the evidence-inclusive gate was `errors=0` at
  pre-commit HEAD `ea553f2` and re-verified read-only on 2026-09-25. At any later
  HEAD it reports exactly one error, `evidence-index-head` (see §2.1).
- Admin language restored to `en`, UAT credential rotated, no browser run after
  teardown. Leave `SESSION_MEMORY.md`'s rotated-credential history alone.

## 2. Known non-issues (do not "fix" these)

1. **Evidence index HEAD mismatch is expected.**
   `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt`
   still records `CANDIDATE_HEAD: ea553f2…` while `develop` has advanced past the
   closure commit. Every
   cycle ends this way: envelopes bind the *pre-commit* HEAD and the mismatch is
   cleared by the **next approved catalog event**, not by re-running the gate now.
   Re-running `scripts/check_localization_gates.py` at today's HEAD fails with
   exactly one error, `evidence-index-head` (re-verified 2026-09-25), and passes
   all other checks with `csv_rows=3364`. Do not re-pin by hand.
2. **Proposal SHA changes on commit.** `.gitattributes` enforces LF. Reviewed
   proposals are captured with CRLF; the committed file is LF with identical
   translation bytes. Record both: reviewed CRLF
   `3d80277b516663b00f2240ed2d9476eef7eeb62803df867dbd029d74f0dcd354`,
   committed LF
   `d8a2a8df2c040434b82d4d813f96e510e454b0f11114a31cf709db62bf60f266`.
3. **Never commit these untracked paths.** They are intentional leftovers:
   - `v16.localhost/` — app-root log directory, excluded by owner directive. Note
     it is **not** listed in `.gitignore`, so exclusion is a convention, not an
     enforced rule; `git add -A` would stage it.
   - `docs/translation/stage6_w606_crm_support_maintenance_decision_rebind_2026-09-24.py`
     — dead one-shot helper: it binds decisions to the **payload** CSV, never
     writes a `content_evidence_*.txt`, never updates `decision_ref`, and pins a
     superseded decisions SHA. The correct helper is the committed
     `…content_evidence_rebind_2026-09-24.py`. Do not stage.
   - Four **orphaned** review documents (not "first drafts" — they review a
     proposal SHA that exists nowhere in the repo and claim `41 payload / 2
     technical` against the final `38 / 1 / 4`):
     `…/stage6-w606-ai-a1-crm-support-maintenance-2026-09-24.md`,
     `…-ai-a2-…`, `…-ai-a3-…`, and
     `…/stage6-w606-ai-r-crm-support-maintenance-corrected-2026-09-24.md`
     (a pre-import prediction expecting catalog 3,326). Committing any of them
     would introduce a proposal SHA matching no file. The committed truth is the
     three `…-corrected-…` reviews plus `…-ai-r-…-final-…`.
   - `docs/translation/stage6_w601_accounts_batch01_*`,
     `stage6_w601_accounts_batch02_rows_2026-09-24.csv`,
     `scripts/stage6_w601_accounts_batch01_cut_2026-09-24.py`,
     `scripts/stage6_w601_accounts_batch02_cut_2026-09-24.py` — the unapproved
     W6-01 package (§3.1). Untracked until the owner approves a scope.

## 3. Remaining work (this is the actual handoff)

Nothing is mid-flight. The next cycle requires a **separate owner-approved
scope proposal**; nothing below may be imported before that approval.

### 3.1 Next candidate — W6-1 Accounts (already cut, awaiting approval)

`docs/translation/stage6_w601_accounts_batch01_proposal_2026-09-24.md` states
it plainly: *proposal only; owner approval pending; no quorum, no import, no
catalog/decision update, no evidence re-pin, no commit, no push.*

| Artefact | Rows | SHA-256 |
|---|---:|---|
| `stage6_w601_accounts_batch01_rows_2026-09-24.csv` (exact scope) | 250 | `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd` |
| `stage6_w601_accounts_batch01_proposal_2026-09-24.csv` | 250 | `226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e` |
| `stage6_w601_accounts_batch02_rows_2026-09-24.csv` (cut only, no proposal) | 250 | `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e` |

Batch 01 disposition: 147 preserved-site-override + 103 proposed payload + 0
technical. Cut/recon/proposal builders already exist:
`scripts/stage6_w601_accounts_batch01_cut_2026-09-24.py`,
`…_batch02_cut_2026-09-24.py`,
`docs/translation/stage6_w601_accounts_batch01_{ai_proposal_build,dict,site_recon}_2026-09-24.*`.
Domain: ERPNext Accounts. The batch plan covers a **1,056-row fresh-Accounts
gap** — that figure comes from the cut scripts (`assert len(fresh) == 1056`,
derived as 1,198 eligible ledger rows − 142 already covered) and from
`docs/erpnext_ar_missing_review_filled.csv`; it is **not** the matrix row, which
still reads `1,265 (subset: ~250 user-visible flow strings)` and is superseded
by the finer cut. At 250 rows per batch the gap needs **5 batches** (4 × 250 +
56 remainder); 500 rows are cut, 556 remain. Batch 01 and Batch 02 scope sets are
disjoint (0 overlap), and Batch 01 is a reproducible slice (`fresh[:250]`).

> **Known defects in the Batch-01 proposal document** (verified 2026-09-25, see
> §8.3): it says "~4 batches" (arithmetically 5), misattributes the 1,056 figure,
> under-lists the trailing-whitespace examples (7, not 5), and does not mention
> that Batch 02 is a cut-only artifact. Its recon JSON lacks a `generated_utc`
> pin, and both cut scripts now fail their own hard-coded asserts when re-run
> because the "prior rows" glob has grown. Fix or accept these explicitly before
> treating the document as an approval artifact.

### 3.2 Other open matrix rows (proposal-only, owner mark-up still ☐)

From `stage6_workflow_matrix_proposal_2026-09-21.md`:

- **W6-6 remainder** — matrix row is *Manufacturing, assets, CRM, support,
  **EDI remaining*** (`481 + 220 + 91 + 31 + 26`). Consumed so far:
  assets 211 (`6f142646…`), manufacturing 01 250 (`0d5098f6…`), manufacturing
  02 202 (`195c7899…`), CRM/support/maintenance 119 (`a77b43a9…`) = 782 rows.
  Re-derive the true EDI/residual remainder against
  `docs/erpnext_ar_missing_review_filled.csv` before proposing — the matrix
  counts are estimates, not commitments, and no EDI cut script exists yet.
- **W6-7** — Frappe framework UI remainder (`frappe_ar_missing_review`);
  `docs/frappe_ar_missing_review.csv` is only 62 bytes, so confirm the source
  ledger before cutting anything.
- **Stage 7** — the report/print pilot (Trial Balance, General Ledger, ONE aging,
  ONE BOQ print) was approved by the owner on 2026-09-21 and the viewer/BOQ
  pilot is **built** (`construction/api/bilingual_reports.py`,
  `construction/tests/test_stage7_bilingual_reports.py`,
  `stage7-viewer-boq-pilot-2026-09-21.md`). What remains gated is the
  *data-dependent* aging/GL leg against real production masters. Note its tests
  are not in `EXPECTED_MODULES`, so they are outside the 271 aggregate.
- **Stage 8 / production** — production **rollout** is fully gated (real
  production master/ledger data ⛔, named production site ⛔, rollout window ⛔;
  `v16.localhost` is governed non-production test). Stage 8 is **not** unstarted
  as a workstream: the isolated restore/rehearsal drill is CLOSED and
  AI-R-verified on commit `0c8057f` (see `stage8-restore-rehearsal-drill-2026-09-22.md`,
  `stage8-production-ai-r-verify-0c8057f.md`). Only production data/site/window
  authorization remains outstanding — no production data has been touched.

### 3.3 Standing rule

Propose exact scope (CSV + sha256, ~200–300 rows, **PROPOSAL ONLY**) → owner
approval → only then run. Never big-bang. Always run hardened
`scripts/uat_preflight.py` before Stage-8 validations. Sequential site
operations only.

## 4. The governed cycle recipe (run it exactly in this order)

This is the loop that produced `3344546`; it is identical for W6-3 → W6-6.

1. **Cut** exact scope with a batch `*_cut_*.py` script → rows CSV + sha256.
2. **Reconcile** against `v16.localhost` (`*_site_recon_*.py` → JSON) →
   disposition partition (released / preserved / technical / deferred).
3. **Build proposal** (`*_ai_proposal_build_*.py`, `*_dict.py`, `*_proposal_*.csv/md`).
4. **Independent quorum** AI-A1 / AI-A2 / AI-A3 on the proposal (separate
   review sessions; write `…-ai-aN-…-corrected-…md` reports).
5. **Cut import payload** (`scripts/stage6_*_cut_*.py` conventions) →
   `*_payload_applied_rows_*.csv` + `*_released_list_*.txt`.
6. **Content evidence + decision rebind** — write `*_content_evidence_*.txt`
   (tab-separated source/translated for *released* rows only), then run the
   content rebind so `decision_ref` points at `content:<path>` and decision IDs
   are recomputed via `row_decision_id(row_identity_fields(...), refs)`.
   *See gotcha G1.*
7. **Catalog update** — append rows to
   `construction/data/translations/approved_ar_overrides.csv`, rebuild
   `release_decisions.json`, then `python3 scripts/check_localization_gates.py --update-baselines`
   to refresh freshness/manifests/inventory baseline.
8. **Live dry-run + import + sync** on `v16.localhost`; capture
   `final-dryrun.txt`, `sync.txt` (must be `0/0`).
9. **Derived artifacts** — refresh
   `construction/data/localization/{freshness_evidence.json,localization_manifest.json,stage2_inventory_manifest.json,vendor_catalog_baseline.json}`,
   plus the Merkle capture `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/merkle.txt`.
10. **Bump gate expectations** — `EXPECTED_DRYRUN` in
    `scripts/check_localization_gates.py:1511` and the `3364` assertion in
    `construction/tests/test_localization_gates.py:520`, plus
    `EXPECTED_MODULES` counts at `scripts/check_localization_gates.py:1497`
    if the module suite total changes. *See gotcha G3.*
11. **UAT preflight** (hardened `scripts/uat_preflight.py`) → browser evidence
    `*_browser_evidence_*.py` + JSON + PNG under
    `docs/ai/work-items/scope-context-portability/evidence/raw-logs/<batch>/`,
    plus `uat_preflight.raw` in that same directory. Teardown: restore
    Administrator language to `en`, rotate credential, **no browser afterwards**.
    (Neither the language restoration nor the credential rotation is captured in
    a repo artifact — both are site-side attestations in the cycle report. Treat
    them as recorded testimony, not evidence.)
12. **Tests**: `python3 construction/tests/test_localization_gates.py`
    (standalone, 92) and the module aggregate (271 across 11 modules, which
    *includes* the 92); capture raw logs into CAP
    (`/tmp/opencode/stage2/` by default; override with
    `STAGE2_EVIDENCE_CAPTURE_DIR`). CAP is disposable and may not exist in a new
    session — create it before capturing. Known stale label: the governed
    `all-tests.txt` `COMMAND:` string says "x6 modules" while 11 modules run.
13. **Assemble CAP**:
    `python3 construction/tests/tools/stage2_evidence_assemble.py`
    → ten envelopes + `index.txt`. **Re-run it after any raw-log rewrite.**
14. **Gates**: scoped gate, vendor audit, translation/scope lints, `git diff --check`,
    then
    `STAGE2_EVIDENCE_BOOTSTRAP=1 python3 scripts/check_localization_gates.py --skip-evidence`
    (the `STAGE2_EVIDENCE_BOOTSTRAP=1` env var is mandatory — without it the gate
    aborts with a single `evidence-bootstrap:` error) and finally the
    evidence-inclusive `python3 scripts/check_localization_gates.py` → must be
    `errors=0` **at the pre-commit HEAD** (see §2.1).
15. **Independent AI-R** on the bundle (live SELECT-only readback; 10/10
    envelopes, 14/14 artifact bindings, payload/preserved/excluded counts,
    DRY drift 0, Administrator `en`) → `…-ai-r-…-final-….md`.
16. **Records**: cycle-executed report under `docs/translation/`, append a
    dated section to `SESSION_MEMORY.md`, update
    `docs/ai/memory_store_fallback/session-hold-state-2026-09-21.json`
    (summary + `hold_directives` entry with exact scope SHA).
17. **Stage, audit, commit — do not push without an explicit owner request.**
    Stage only the intended set; verify with `git status --short`,
    `git diff --cached --name-only`, `git diff --cached --check`,
    `git log --oneline -10`; confirm unrelated W6-1 / superseded / `v16.localhost/`
    paths stay untracked; then `git commit -m "feat(localization): close <batch>"`.
    Message style matches `git log` (`feat(localization): close W6-6 …`).
18. **Reconcile the plan** — add the cycle's row to plan §16 (Stage Progress Log),
    §17 (owner acknowledgments) and §18 (hold state: summary line + dated
    bullet), and refresh the §18 heading date list. The plan is the
    repo-authoritative record and it lagged two cycles behind until the
    reconciliation of 2026-09-25 (see §8.2).

## 5. Gotchas that actually cost time this cycle

- **G1 — decision identity must bind `content:`, never `payload:`.**
  Binding decisions to the payload CSV makes `release_decisions.json`
  disagree with the committed catalog; the full gate catches it. The
  content-rebind helper (`…content_evidence_rebind_2026-09-24.py`) is the
  authoritative fix and asserts exact expected catalog/decisions SHAs before
  mutating anything.
- **G2 — one-shot helpers are self-asserting.** Rebind/cycle scripts assert
  fixed SHAs and will refuse to run after the catalog moves. That is by
  design; recompute expectations rather than forcing them.
- **G3 — three gate constants move every cycle**: `EXPECTED_DRYRUN`,
  the standalone `assertEqual(n, …)`, and `EXPECTED_MODULES` totals. Miss one
  and the suite fails after an otherwise clean import.
- **G4 — CAP is disposable but the envelopes are not.** If you rewrite
  `gate-tests-standalone.txt` (or any raw log), re-run the assembler or the
  14 artifact bindings break. `/tmp/opencode/stage2/` may contain stale files
  from earlier batches — only the files listed under `…/raw-logs/stage2/`
  are governed.
- **G5 — proposal line endings.** Compare translation content, not bytes,
  across the CRLF→LF normalization; record both hashes in the report.

## 6. Verification cheatsheet

```bash
cd /home/mohamed/frappe-bench/apps/construction
git log --oneline -6 && git status --short && git rev-parse HEAD origin/develop

# full evidence gate (only correct immediately after an evidence re-pin,
# i.e. before the closure commit — see §2.1)
python3 scripts/check_localization_gates.py | tail -3

python3 construction/tests/test_localization_gates.py          # expect 92/92
python3 construction/tests/tools/stage2_evidence_assemble.py   # 10 envelopes + index
sha256sum docs/translation/<batch>_rows_*.csv                  # must match approval
git diff --cached --check                                      # whitespace/line-endings
```

## 7. First actions for the next agent

1. Read `AGENTS.md` → `SESSION_MEMORY.md` (top + the 2026-09-25 section) →
   this file. Verify §1 against live repo (`git log`, `git status`).
2. Decide the next scope: W6-1 Accounts batch 01 (awaiting owner approval; see
   §3.1 and §8.3 for its verified state and known defects) or a freshly derived
   W6-6 EDI remainder. Draft the PROPOSAL ONLY package.
3. **Do not import, do not push, do not touch production/Stage 8** until the
   owner approves the exact rows CSV + sha256.
4. After approval, run §4 verbatim and close with a local commit only.

## 8. Reconciliation addendum (2026-09-25, read-only verification session)

A later session was tasked with continuing the program under the standing
holds. It changed **no** catalog, decision, evidence, site, or test artifact.
Everything below is verification plus documentation truth-fixes.

### 8.1 Push state — the three session commits are published

`origin/develop` now equals local `develop` (`797771e` at verification time,
0 ahead / 0 behind). The remote-tracking reflog records
`797771e … update by push` at **2026-09-25 01:55:09 +0300**, about five minutes
after the last local commit (01:49:50). No `git push` was issued by the agent,
`.git/hooks/post-commit` does not push (it only writes MCP memory), and no
script in the repo pushes. Earlier batch closures show the same
owner-push-after-closure pattern (`ea553f2` at 22:10:30, `69b999e` at 18:49:23,
…). So: an external actor published the branch.

Consequences recorded for the next agent:

- The earlier "no push performed" wording in this file, in `SESSION_MEMORY.md`
  and in the hold-state JSON was **true when written** and is now stale. The
  cycle-executed reports were left untouched — they are point-in-time evidence.
- No history rewriting, force-push, or revert was attempted or is authorized.
- The standing rule is unchanged in substance: **do not push again without an
  explicit owner request.**

### 8.2 Plan/matrix reconciliation performed

- Plan §16: added the missing **W6-6 Manufacturing batch-02** and **W6-6 CRM,
  Support & Maintenance** rows (catalog is now recorded as 3,364; before this
  the highest figure in §16 was 3,244).
- Plan §17: added the missing acknowledgments for **W6-5 Setup**, **W6-6
  Assets**, **W6-6 Manufacturing batch-01** and **W6-6 CRM**; removed a stray
  blank line that was breaking the table.
- Plan §18: heading date list now includes the 2026-09-24 and 2026-09-25 cycles;
  added the CRM hold-state summary line and the dated bullets for
  Manufacturing batch-02 and the CRM cycle.
- Plan §14: added the explicit **evidence-lag caveat** — Go/No-Go criteria 1–2
  are not green while the evidence index pins a pre-commit HEAD; the single
  `evidence-index-head` error is the convention, not a defect.
- Plan: removed two stale "current HEAD" claims about `a0f01cb`.
- Workflow matrix: the line-3 banner claiming "PROPOSAL ONLY — no translations
  committed, no runtime import" was false after 20 cycles and has been replaced;
  an agent-maintained "Executed batches" column was added. The owner-decision
  `☐` column was deliberately **not** touched — approvals were granted per batch
  and are recorded in plan §16/§17, not in that table.
- `AGENTS.md` identity block and this file's §1/§2.1/§2.3/§3.1/§3.2 were
  corrected for the push state, the `uat_preflight.py` path, the 1,056-row
  provenance, the batch count, the Stage 7/8 status, and the precise names of
  the untracked leftovers.

### 8.3 W6-01 Accounts — pre-approval verification result

Verified read-only, with an independent audit:

| Check | Result |
|---|---|
| Batch-01 scope CSV SHA `4910a9e4…` / 250 rows | PASS |
| Batch-01 proposal CSV SHA `226ff8b1…` / 250 rows | PASS |
| Batch-02 scope CSV SHA `dc9b6c02…` / 250 rows | PASS |
| Partition 147 preserved + 103 proposed + 0 technical = 250 | PASS (recomputed) |
| 147 preserved rows byte-identical to live site overrides | PASS |
| Batch-01 ∩ Batch-02 = 0; 500 unique rows across both | PASS |
| Cut is a reproducible slice of a 1,056-row fresh gap | PASS |
| Blank translations / whitespace-affix violations / placeholder multiset errors | 0 / 0 / 0 |
| Any W6-01 row already in the catalog or decisions | **0** (nothing imported) |
| Builders import/DRY_RUN/import/commit? | No — offline generators; `site_recon` is a read-only DB query that writes its own JSON |

Open defects in the Batch-01 proposal document (all documentation-level, none
blocking the *scope* itself): wrong batch count ("~4" → 5), unsourced 1,056
figure, whitespace example list incomplete (7 trailing rows, 5 listed), no
mention of the cut-only Batch-02, recon JSON with no `generated_utc` pin, and
both cut scripts no longer re-runnable (their hard-coded `142`/`1056` asserts
now fail because the "prior rows" glob has grown to 392 prior rows).

**W6-01 remains unapproved and unrun.** An approval request for the exact
Batch-01 scope was raised on 2026-09-25 and is the recommended next step.

### 8.4 Read-only gate state at verification time

- `STAGE2_EVIDENCE_BOOTSTRAP=1 python3 scripts/check_localization_gates.py --skip-evidence`
  → exit 0, `errors=0`, `csv_rows=3364`.
- `python3 scripts/check_localization_gates.py` (evidence-inclusive) → exit 1
  with **exactly one** error, `evidence-index-head`; all other checks green.
- Catalog 3,364 / decisions 3,364; `release_version 1.10` = 38 rows;
  freshness `packaged_rows=3364`, `critical_pass=true`; inventory Merkle
  `f1d00e38…c2e4e1`; `EXPECTED_DRYRUN` = 3364; 11 modules summing to 271;
  92 standalone tests.
- Worktree unchanged by the verification (16 untracked entries, nothing staged).

### 8.5 Claims that remain unevidenced

Two assertions in the cycle report and AI-R report are site-side attestations
with **no repo artifact**: the Administrator language restoration to `en` (and
the credential rotation / no-browser-after-teardown sequence), and the
`38 created` import count. The only language observations captured anywhere are
`ar` (pre-teardown). Treat both as recorded testimony.
