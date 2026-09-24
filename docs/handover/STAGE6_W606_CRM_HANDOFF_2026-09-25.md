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
| This handoff commit | `f5420a4` — `docs: publish Stage 6 W6-6 CRM handoff report` |
| `origin/develop` | `ea553f2` — **NOT pushed, intentionally**; `git rev-list --count HEAD` shows how far local `develop` has run ahead |
| Last cycle | W6-6 CRM, Support & Maintenance — **CLOSED**, no in-flight work |
| Site | `v16.localhost` only; production and Stage 8 untouched/gated |
| Catalog / decisions | 3,364 / 3,364 rows |
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
- Tests: standalone **92/92**, module suite **271/271**, full evidence-inclusive
  gate `errors=0`, `csv_rows=3364`.
- Admin language restored to `en`, UAT credential rotated, no browser run after
  teardown. Leave `SESSION_MEMORY.md`'s rotated-credential history alone.

## 2. Known non-issues (do not "fix" these)

1. **Evidence index HEAD mismatch is expected.**
   `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt`
   still records `CANDIDATE_HEAD: ea553f2…` while local `develop` has moved to
   `f5420a4` and beyond. Every
   cycle ends this way: envelopes bind the *pre-commit* HEAD and the mismatch is
   cleared by the **next approved catalog event**, not by re-running the gate now.
   Re-running `scripts/check_localization_gates.py` at today's HEAD will fail on
   this by design. Do not re-pin by hand.
2. **Proposal SHA changes on commit.** `.gitattributes` enforces LF. Reviewed
   proposals are captured with CRLF; the committed file is LF with identical
   translation bytes. Record both: reviewed CRLF
   `3d80277b516663b00f2240ed2d9476eef7eeb62803df867dbd029d74f0dcd354`,
   committed LF
   `d8a2a8df2c040434b82d4d813f96e510e454b0f11114a31cf709db62bf60f266`.
3. **Never commit these untracked paths.** They are intentional leftovers:
   - `v16.localhost/` — app-root log directory, permanently excluded.
   - `docs/translation/stage6_w606_crm_support_maintenance_decision_rebind_2026-09-24.py`
     — superseded one-shot payload-binding helper; the *correct* helper is
     `…content_evidence_rebind_2026-09-24.py` (already committed). Delete or
     leave, but do not stage.
   - `docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-{a1,a2,a3,r}-*-2026-09-24.md`
     (the ones **without** `-corrected`/`-final` in the name) — superseded first
     draft reviews. The committed versions are the `…-corrected-…` three plus
     `…-ai-r-…-final-…`.
   - `docs/translation/stage6_w601_accounts_batch01_*` and
     `stage6_w601_accounts_batch02_rows_*` — see §3.

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
Domain: ERPNext Accounts, ~4 batches to cover the 1,056-row fresh-accounts gap
(`docs/translation/stage6_workflow_matrix_proposal_2026-09-21.md` row W6-1).

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
- **Stage 7** — report/print pilot (Trial Balance, General Ledger, ONE aging,
  ONE BOQ print) is approved *in principle* only.
- **Stage 8 / production** — fully gated. Requires production-data, rehearsal,
  and explicit owner authorization controls. Not started.

### 3.3 Standing rule

Propose exact scope (CSV + sha256, ~200–300 rows, **PROPOSAL ONLY**) → owner
approval → only then run. Never big-bang. Always run hardened
`uat_preflight.py` before Stage-8 validations. Sequential site operations only.

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
   plus `merkle.txt`.
10. **Bump gate expectations** — `EXPECTED_DRYRUN` in
    `scripts/check_localization_gates.py:1511` and the `3364` assertion in
    `construction/tests/test_localization_gates.py:520`, plus
    `EXPECTED_MODULES` counts at `scripts/check_localization_gates.py:1497`
    if the module suite total changes. *See gotcha G3.*
11. **UAT preflight** (hardened `uat_preflight.py`) → browser evidence
    `*_browser_evidence_*.py` + JSON + PNG, persisted
    `uat_preflight.raw`. Teardown: restore Administrator language to `en`,
    rotate credential, **no browser afterwards**.
12. **Tests**: `python3 construction/tests/test_localization_gates.py`
    (standalone) and the module suite; capture raw logs into CAP
    (`/tmp/opencode/stage2/` by default; override with
    `STAGE2_EVIDENCE_CAPTURE_DIR`).
13. **Assemble CAP**:
    `python3 construction/tests/tools/stage2_evidence_assemble.py`
    → ten envelopes + `index.txt`. **Re-run it after any raw-log rewrite.**
14. **Gates**: scoped gate, vendor audit, translation/scope lints, `git diff --check`,
    then
    `STAGE2_EVIDENCE_BOOTSTRAP=1 python3 scripts/check_localization_gates.py --skip-evidence`
    and finally the evidence-inclusive
    `python3 scripts/check_localization_gates.py` → must be `errors=0`.
15. **Independent AI-R** on the bundle (live SELECT-only readback; 10/10
    envelopes, 14/14 artifact bindings, payload/preserved/excluded counts,
    DRY drift 0, Administrator `en`) → `…-ai-r-…-final-….md`.
16. **Records**: cycle-executed report under `docs/translation/`, append a
    dated section to `SESSION_MEMORY.md`, update
    `docs/ai/memory_store_fallback/session-hold-state-2026-09-21.json`
    (summary + `hold_directives` entry with exact scope SHA).
17. **Stage, audit, commit locally, do not push** — stage only the intended
    set; verify with `git status --short`, `git diff --cached --name-only`,
    `git diff --cached --check`, `git log --oneline -10`; confirm unrelated
    W6-1 / superseded / `v16.localhost/` paths stay untracked; then
    `git commit -m "feat(localization): close <batch>"`. Message style matches
    `git log` (`feat(localization): close W6-6 …`).

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
2. Decide the next scope: W6-1 Accounts batch 01 (ready for approval) or a
   freshly derived W6-6 EDI remainder. Draft the PROPOSAL ONLY package.
3. **Do not import, do not push, do not touch production/Stage 8** until the
   owner approves the exact rows CSV + sha256.
4. After approval, run §4 verbatim and close with a local commit only.
