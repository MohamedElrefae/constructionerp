# Stage 4 — Review-bundle population guide (session-ready)

Date: 2026-09-10 · HEAD: `e7be48855bde540464ea302e53c9bfca62b7c462` (uncommitted)

For the **independent AI proposal** and **AI-A2 accounting/QS review**
sessions that will populate `account_review_bundle` (`construction-stage4-
account-review-bundle/v1`). Documentation only — no values are pre-filled and
nothing is mutated by following it.

> **Populating and passing validation is NOT owner approval and NOT import
> authorization.** A validated bundle only means the review contract is
> met. Owner approval, dry-run, test-site import, post-import verification,
> and every Account/translation data mutation remain separate, blocked gates.

## 0. Where this sits in the workflow

`independent-proposal -> ai-a2-review -> [this bundle] -> owner-approval ->
dry-run -> authorized import`

The bundle must be bound to the **private Stage 4 export** produced earlier:
- governed manifest: `construction/data/localization/stage4_export_manifest.json`
  (records the absolute private export path + its SHA-256; contains no rows);
- the export itself (81 Elrefae accounts, 55 leaves + 26 groups) lives under
  `<site>/private/stage4/`.

Neither the validator nor the payload builder accepts a caller-supplied
identity set, English map, export path, or SHA — they reload and SHA-verify
the private export themselves.

## 1. Required fields per row

Start from `bundle_template()` (one empty row; repeat it for each exported
account identity). The validator enforces:

| Field | Required | Rule |
|---|---|---|
| `identity` | yes | must be one of the governed export's identities |
| `english` | yes | must equal that identity's English value in the export |
| `is_group` | carried | part of the row (bool) |
| `proposal.arabic` | yes | non-empty; never invented outside the proposal session |
| `proposal.confidence` | yes | non-empty |
| `proposal.provenance.reviewer` | yes | proposal reviewer identity |
| `proposal.provenance.model` | yes | proposal model identifier |
| `proposal.provenance.session` | yes | proposal session id |
| `proposal.provenance.submitted_utc` | yes | strict UTC |
| `a2_review.decision` | yes | `approved` or `exception` |
| `a2_review.confidence` | yes | non-empty |
| `a2_review.rationale` | yes | non-empty |
| `a2_review.reference.status` | yes | `verified` or `absent` |
| `a2_review.reference.value` | when `verified` | the authoritative reference |
| `a2_review.reference.source` | when `verified` | its source |
| `a2_review.provenance.reviewer` | yes | AI-A2 reviewer identity |
| `a2_review.provenance.model` | yes | AI-A2 model identifier |
| `a2_review.provenance.session` | yes | AI-A2 session id |
| `a2_review.provenance.reviewed_utc` | yes | strict UTC |
| `flags` | when `reference.status = absent` | must include `no_verified_reference` |

The bundle must name **exactly** the export's identities: a missing exported
account, an extra/forged identity, a duplicate identity, or an English
mismatch is refused.

## 2. Reviewer/session separation (independence)

`proposal.provenance.session` must differ from `a2_review.provenance.session`,
**and** `proposal.provenance.reviewer` must differ from
`a2_review.provenance.reviewer`. A proposal cannot approve its own output.

Valid separation example (names are illustrative; use real session ids):

```json
"proposal":   {"provenance": {"reviewer": "AI-A1-proposal", "model": "proposal-model-X", "session": "prop-2026-09-11-a", "submitted_utc": "2026-09-11T08:00:00Z"}},
"a2_review":  {"provenance": {"reviewer": "AI-A2-egyptian-accounting", "model": "a2-model-Y", "session": "a2-2026-09-11-b", "reviewed_utc": "2026-09-11T10:00:00Z"}}
```

Refused example (same session and same reviewer):

```json
"proposal":   {"provenance": {"reviewer": "same", "session": "s-1"}},
"a2_review":  {"provenance": {"reviewer": "same", "session": "s-1"}}
```

→ violations: “proposal and AI-A2 provenance must use DISTINCT sessions” and
“…reviewers must be DISTINCT”.

## 3. Reference vs explicit absence

Verified authoritative reference:

```json
"reference": {"status": "verified", "value": "EAS 48 (Egyptian Accounting Standards) clause …", "source": "EAS 48 / ETA publication …"}
```

Explicit documented absence (never invent an MOF/EAS/ETA reference):

```json
"reference": {"status": "absent", "value": null, "source": null},
"flags": ["no_verified_reference"]
```

Rules: `verified` requires both `value` and `source` (references must never be
invented); `absent` requires the row to carry the explicit
`no_verified_reference` flag. Any other `status` is refused.

## 4. UTC timestamps

- Format is strict: `YYYY-MM-DDTHH:MM:SSZ` (literal `T` and `Z`, no offset,
  no fractional seconds).
- Order: `proposal.provenance.submitted_utc <= a2_review.provenance.reviewed_utc`.
- If a `now_utc` bound is supplied to validation, neither timestamp may be in
  the future; a **malformed** non-empty `now_utc` is itself an error (it never
  silently disables the future check).

## 5. Exception rows

`decision: "exception"` is a first-class, reviewable outcome — it is **not**
silently dropped:

- An exception row must still carry `arabic`, `confidence`, `rationale`,
  a `reference` (`verified` or explicit `absent`), and full AI-A2 provenance.
- Exceptions appear in `summary["reviewable_exceptions"]` and in the built
  payload's manifest (`exception_count`, `reviewable_exceptions`).
- The payload includes exception rows (the value is imported with the
  recorded exception); approved and exception rows are validated identically.

## 6. Exact validation and payload-build commands

Authoritative build check (raises `BundleError` on any violation; does NOT
write anything):

```bash
bench --site v16.localhost console <<'EOF'
import json
from construction.services import account_review_bundle as rb
bundle = json.load(open("/path/to/populated-bundle.json", encoding="utf-8"))
result = rb.build_import_payload(bundle, now_utc="2026-09-11T12:00:00Z")
print("PAYLOAD_ROWS:", len(result["payload"]))
print("MANIFEST:", json.dumps({k: v for k, v in result["manifest"].items() if k != "reviewable_exceptions"}, sort_keys=True))
exit()
EOF
```

Violation report (non-raising; shows every problem for a reviewer to fix):

```bash
bench --site v16.localhost console <<'EOF'
import json
from construction.services import account_review_bundle as rb
bundle = json.load(open("/path/to/populated-bundle.json", encoding="utf-8"))
m = rb._load_governed_manifest(rb._governed_manifest_path())
identities, sha = rb._reload_verified_export(m)
summary = rb.validate_bundle(bundle, expected_identities=set(identities),
                             expected_english=identities, now_utc="2026-09-11T12:00:00Z")
print("VIOLATIONS:", len(summary["violations"]))
for v in summary["violations"][:20]:
    print(" -", v)
exit()
EOF
```

(`_load_governed_manifest`, `_reload_verified_export`, `_governed_manifest_path`
are internal helpers used here read-only for diagnostics; the production entry
point exposes no such parameters.)

Demonstration on the EMPTY template (real captured output, non-mutating):

```
IDENTITIES: 81 EXPORT_SHA: 206ecfae017b
VIOLATIONS: 97
FIRST: row[0]: identity is required
REFUSED: review bundle is not eligible for an import payload (97 violation(s)): row[0]: identity is required
```

Run the bundle tests:

```bash
python3 construction/tests/test_stage4_review_bundle.py
bench --site v16.localhost run-tests --module construction.tests.test_stage4_review_bundle
```

## 7. Value-empty template

```bash
bench --site v16.localhost console <<'EOF'
import json
from construction.services.account_review_bundle import bundle_template
print(json.dumps(bundle_template(), indent=1, ensure_ascii=False))
exit()
EOF
```

This emits `rows: [ { identity: null, english: null, is_group: null,
proposal: { arabic: null, confidence: null, flags: [], provenance: { … nulls } },
a2_review: { decision: null, confidence: null, rationale: null,
reference: { status: null, value: null, source: null },
provenance: { … nulls } }, flags: [] } ]` — all values empty, ready for the
independent sessions to fill.

## 8. Authorization statement

Passing `validate_bundle`/`build_import_payload` is a **contract check only**.
It is **not** owner approval and **not** authorization to import. The
independent proposal/AI-A2 sessions may populate the bundle; owner approval
of the reviewed payload, the zero-mutation dry-run, the explicitly authorized
test-site import, post-import verification/rollback, and any Account or
translation data mutation remain **blocked** until separately authorized.
