# Stage 6 — W6-0b short-UI exact CSV (2026-09-22)

**Status: exact proposal delivered for owner review — no translation import authorized by this note.**

Basis: Owner Annotation 1 (2026-09-22) — prepare the exact bounded W6-0b CSV
scope and this review package on `v16.localhost` as a **non-production test
batch**; **no import and no batch expansion** until the owner approves this
exact scope. Plan §18 hold (`production_mutation_authorized: false`, commit
`e669102`) still applies to production, Stage-8 rollout, and unrelated W6
batches.

W6-0b definition (proposal line 16): *Short UI strings ≤40 chars (labels,
tooltips, menu captions)* — P2; a bounded cut of the frappe gap ledger after
a1/a2 dictionary dedup.

## Contents

Regenerate with the deterministic cut (byte-stable on re-run):

```bash
python3 docs/translation/stage6_w60b_cut_2026-09-22.py
```

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_short_ui_rows_2026-09-22.csv` | 1,915 | `5d87a57abb2a5aadc4e8623d6a03a2e078efe41c6e706a6db56e4c2720cf6b6d` |
| `docs/translation/stage6_w60b_dedup_exclusions_2026-09-22.csv` | 302 | `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b` |

Columns on the scope CSV mirror W6-0a plus two review aids:
`source_text,classification,location,suppression_rationale,ai_r_ref,length,app,suggested_ar`.

## Exact cut funnel (machine-checkable)

| Step | Count | Rule |
|---|---|---|
| Frappe gap ledger rows | 2,861 | `app == frappe` in `docs/arabic_coverage_gap_report_2026-08-22.csv` |
| Short nonempty unique | 2,217 | `len(source_text.strip()) <= 40`, unique by stripped text |
| Prior-approved exclusions | 302 | `source_text ∈ construction/data/translations/approved_ar_overrides.csv` → exclusions CSV, reason `prior_approved_a1a2` |
| **W6-0b scope** | **1,915** | 2,217 − 302 (partition is exact: scope ∪ exclusions = unique short, scope ∩ exclusions = ∅) |

**Delta vs proposal estimate:** proposal said “subset of 2,140”; live short
unique is **2,217 (+77)** — the 2,140 figure was a pre-cut estimate, not a
ledger count. Final scope after a1/a2 dedup is **1,915 (−225 vs 2,140)**.

Dedup cross-checks against this scope (all zero additional removals beyond the
302 a1/a2 rows): W6-0a CSV ∩ scope = 0; W6-1 CSV ∩ scope = 0; Stage-1C
`critical_labels.json` ∩ scope = 0 (5/6 already inside the 302);
`egyptian_construction_glossary.json` terms ∩ scope = 0 (`Add Child`,
`Child Item` already inside the 302). No W6-0b row was removed for
w60a/w61/critical/glossary reasons — **only** `prior_approved_a1a2`.

## Classification inside the scope (this cut)

| Classification | Count | Meaning |
|---|---|---|
| `translation-candidate` | 1,894 | natural-language short UI strings (labels, tooltips, menu captions), including single- and multi-placeholder messages such as `Page {0} of {1}`; eligible for AI-proposal → quorum (A1/A2/A3) → AI-R → DRY_RUN → IMPORT **only after this CSV is approved as the batch scope** |
| `EXCEPTION-technical` | 21 | no A–Z/a–z, embedded HTML tag, embedded newline, or JS `${…}` template — proposed as **scope exceptions: keep vendor rendering, no translation**; recorded for AI-R suppress-check |

Classifier is intentionally narrow (W6-0a-aligned): ordinary English containing
`Select`/`Insert`/`Python`/`{0}` stays a **translation-candidate**; only
symbol-only, HTML-bearing, multiline, or `${` fragments are technical. Four
rows carry a ledger `suggested_ar` hint (`City`, `Country`, `Phone`,
`Postal Code`) — still candidates for quorum, not pre-approved translations.

`location` is the documented fallback `in-ledger (no vendor PO location match)`
for **all 1,915 rows**: this cut did not resolve vendor PO file paths for short
UI msgids (unlike W6-0a, which mostly carried real file locations). DEFERRED
is **not** used in W6-0b (short UI labels without a path remain candidates).

## Boundary honored

- The broad ledger remains the warden: these two CSVs are the **candidate
  scope for owner/quorum review**, not an authorization to import.
- No catalog change, no runtime import, no production mutation, no Stage-8
  work, no other W6 batch is started by this package.
- After owner approval of *this exact scope*, the governed cycle is unchanged:
  AI proposal → quorum A1/A2/A3 → AI-R → DRY_RUN → IMPORT → browser evidence →
  re-pin — executed only on the test site (`v16.localhost`), still never over
  production.

## Owner mark-up requested

- [ ] Approve W6-0b as the next batch **exactly as the 1,915-row scope CSV**
      (sha256 above), with the 21 technical rows as suppress-exceptions.
- [ ] Accept the 302 `prior_approved_a1a2` exclusions as out of scope.
- [ ] Adjust scope/priority (e.g. move rows to W6-0c, change P2) — reply with
      the delta; the cut script will be re-run and sha re-pinned.
- [ ] Confirm terminology overrides (if any) go to the terminology sheet before
      the quorum panel runs.
