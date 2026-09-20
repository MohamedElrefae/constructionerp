# Stage 2 — closure verification against current `develop` (2026-09-20)

## Scope

Independent re-verification of Stage 2 (catalog delta/review pipeline + CI
localization gates) against merged `develop` @ `b081b2e`, per plan §11 row 2
gate: "Current 15,106-row inventory; CI gate blocks hardcoded-string and
missing-translation merges."

## Verification results (all commands executed fresh on 2026-09-20)

| Check (canonical command) | Result | Exit |
|---|---|---|
| Full gate, evidence-structure skip (bootstrap mode): `STAGE2_EVIDENCE_BOOTSTRAP=1 python3 scripts/check_localization_gates.py --skip-evidence` | `errors=0` — PO 805 rows, CSV 34 rows, extraction 260 files / 0 missing / 664 wrapped, raw-text 7 files / 0 missing | **0 (PASS)** |
| Scoped gate on the 4 classified files (login.html, 2 workspace JSONs, PDF template) | `errors=0` (1 documented SKIP: markup blob excluded by policy) | **0 (PASS)** |
| Vendor audit: `--audit-vendor-coverage` | `errors=0` | **0 (PASS)** |
| Standalone gate tests: `construction/tests/test_localization_gates.py` | **91 tests, OK** (includes deliberate fail-closed negative tests: path traversal rejected, BOGUS provenance rejected, absent tree rejected) | **0 (PASS)** |
| `scripts/lint_scope_metadata.py` | PASS | **0** |
| `scripts/lint_translation_writes.py` | PASS | **0** |
| `git diff --check` | clean | **0** |
| CI workflow | `.github/workflows/linter.yml` runs `check_localization_gates.py --ci-source-only` (guarded to `GITHUB_ACTIONS=true`) on sibling-vendor-pinned checkout | operational |

## Catalog inventory crosscheck

The live gate's own extraction/inventory numbers reconcile with the committed
inventory referenced by `scripts/stage2_inventory.sql`
(`construction/locale/ar.po`: 805 rows; runtime override CSV: 34 `Released`
rows; combined catalogs 15,106 total / 7,339 empty per plan §Table). No
hardcoded-string or missing-translation failures exist on the current source
tree.

## The one open re-pin (not a defect)

The recorded Stage-2 evidence bundle
(`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/*`,
all 10/10 files present and trackable) pins candidate HEAD `e7be4885` and
artifact hashes of its collection-time tools (`CHECKER_SHA256`,
`TESTS_SHA256`, `TRANSLATIONLINT_SHA256`). The evidence-inclusive gate run on
today's HEAD correctly reports 7 mismatches:
- script-hash drift (~since `d596929` "Separate CI source gates from historical evidence"), and
- `evidence-index-head` mismatch vs `b081b2e` (today's evidence/doc commits).

This is the designed contract — "any row or evidence edit invalidates;
re-pin under review" — not a catalog or gate defect. CI is unaffected
because CI deliberately uses the source-only mode for exactly this reason.

## Verdict

- Catalog pipeline + CI localization gates: **operationally closed** on
  current `develop` (every fresh run exit-0; suite 91/91 OK).
- Recorded durable evidence envelope: **stale by design contract**, requires
  one deliberate **re-pin under review** (re-collect the 10 envelopes against
  a pinned HEAD, update index + pinned SHA constants) as a separate reviewed
  change, which also advances `FRESHNESS` age (currently 10 days old — inside
  the 30-day limit).

## Recommendation

Treat Stage 2 as **operationally verified** and record the re-pin as the
single remaining Stage-2 housekeeping item. Re-pin when the Stage 6/7 work
next touches catalog rows (one re-pin amortizes both events; re-pinning on
every doc-only commit wastes the evidence budget).
