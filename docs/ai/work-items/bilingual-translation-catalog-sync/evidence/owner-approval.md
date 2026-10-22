# Owner Approval — bilingual-translation-catalog-sync

**Work item:** `bilingual-translation-catalog-sync`
**Date:** 2026-10-05
**Approved by:** Owner (via in-session question tool)
**Base commit at audit time:** `6c721b8` (`develop`)
**Authorized site:** `v16.localhost` — `production_mutation_authorized: false`
**Policy:** `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md` (local-only; no remote push; no public CI)

---

## 1. Proposal sha binding (hard gate)

```
Proposal sha256 (bound to this approval):
a23a7dceb6cf4b794af47155317be63267fbab46a7334618bf05dfbceec9b9a0
```

Private artefact: `sites/v16.localhost/private/translation-catalog-sync/proposal.json`
(8,χχχ bytes; Arabic values held privately per privacy R4).

**Gate condition.** `dry_run_translation_sync.py` and `apply_translation_sync.py` must recompute
the proposal sha256 and **abort fail-closed** unless it equals the value above. Each script
hardcodes `APPROVED_SHA` and asserts it as its first action. Any later proposal edit invalidates
this approval.

## 2. Decision

The audit found **exactly one** rendered divergence among the 47 glossary terms:
source `Add Child` (rendered sha16 `f548ae03f4cdbef0` vs glossary `46dadab0f9e2eacf`).
The released payload `approved_ar_overrides.csv` carries an **owner-directed 2026-09-03** value
(commit `4fede75`, payload `release_version 1.1`) that superseded the glossary v1.0 value one day
after the glossary was last committed (`9011767`, 2026-09-02).

**Owner decision (recorded):** harmonise **the glossary to the released payload** — the glossary
is the stale artefact. Direction re-confirmed in-session as *"Sync glossary to v1.1 (as
recorded)"*.

Approved change set:

| # | Artefact | Change |
|---|----------|--------|
| 1 | `construction/data/glossary/egyptian_construction_glossary.json` | term `Add Child`: `approved_ar` := the released payload value; `usage_notes` + `references` extended to record the 2026-09-03 owner supersession (commit `4fede75`) and the global-tree-action context risk; `version` → `2.1`. `meta`: `version` → `2.1`, `date` → `2026-10-05`, `previous_version` := `2.0`, `previous_checksum` := current glossary sha256 `aefbbf63…46b51b4`, `term_count` unchanged (47). |

Binding digests:

```
glossary sha256 before : aefbbf633d432fb93ac63996960bb58d0bd005e973e0e461f4480d7ae46b51b4
glossary sha256 after  : 7afbef1ab892f466eb14471c99a9e76dde65b4f2e9d4a40a1405e34addc6894d
payload  sha256       : 0a55f3c120cf1ac381c0564407cdc7a9ea975782d68642c6a943807cdd70b421 (MUST remain byte-identical)
site Translation writes: 0
```

## 3. Report-only (explicitly NOT mutated)

- **C-02** — 24 inert rows (`ct_is_catalog_entry = 1`): 3 divergent (`Add Child`, `Subcontract`,
  `Is Subcontracted`) + 21 empty, across 20 sources. Never rendered; Stage-6-owned review state.
- **C-06** — `construction/patches/v8_4/fix_tree_view_arabic_translations.py` hardcodes the
  glossary-side value and is a registered patch; latent pre-existing drift, self-healed by the
  `after_migrate` `import_released_overrides_hook`. Not mutated.
- **C-07** — `construction/public/js/components/TreeView.jsx` hardcodes 10 Arabic labels
  (incl. Add Child variant `0bed7b4494c94ee6`); not registered in `hooks.py` and imported by no
  module, so it never renders. Not mutated.
- **C-04** — `construction/api/translation_tools.py::_load_glossary` reads schema-v1 keys and is
  a dead endpoint against the v2 glossary. App-code fix, out of scope.
- **C-08** — dated Stage-2 evidence (`smoke-test-1.0.md`, `sign-off-1.0.md`, `smoke/README.md`)
  asserts the pre-`4fede75` value; owned by the closed Stage-2 work item. Not edited.

## 4. Rationale for not editing the released payload

Reverting `approved_ar_overrides.csv` would break `scripts/check_localization_gates.py` evidence
validation: the closed work item `erp-arabic-bilingual-data` pins
`CSV_SHA256: 0a55f3c1…` and `DECISIONS_SHA256: bf7a5833…` in its Stage-2 envelopes. Re-opening
that closed system is outside this work item's scope. The glossary is unpinned (no manifest or
envelope references it), so harmonising it is the contained, reversible remediation.

## 5. Out of scope (respected)

- No vendor edits (`apps/frappe`, `apps/erpnext`).
- No `Translation` doctype mutation of any kind.
- No edit to `approved_ar_overrides.csv`, `release_decisions.json`, `TreeView.jsx`,
  `patches/v8_4/*`, `_load_glossary`, or any Stage-2 evidence.
- No remote push, no public CI. Git working tree left unstaged for independent verification and
  commit by the Lead Verifier.

## 6. Independent review

`evidence/review-ai-a2.md` records round 1 (REVISE, 4 changes), round 2 (REVISE, 1 change) and
round 3 (**APPROVE**) by independent non-author sessions. Standing: all checks pass.
