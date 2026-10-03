# Scope & Architectural Blueprint — Narrative Unicode Policy

**Work item:** `narrative-unicode-policy`
**Status:** `APPROVED` — design complete; approved by owner in session. Implementation
opens as a successor work item with its own causal evidence pipeline.
**Base commit:** `46aa201` (develop clean; record defects resolved; 61/61 git-blob digests)
**Date:** 2026-10-03
**Authority:** Programme architectural governance under Plan §3.2; owner instruction in session
**Supersedes:** the `DEFERRED_PENDING_DESIGN` descriptor at `9010731`, which contained three factual errors corrected in §1.

**Outcome:** an empirically measured design for Unicode/HTML/direction handling of narrative
prose fields, with a written schema invariant. **No code is written in this cycle.**

---

## 1. Findings — corrections to the deferred blueprint

The prior descriptor asserted things about the codebase that are not true. Each is
corrected here with measured evidence.

### 1.1 Errors corrected

| Prior claim | Measured reality |
|---|---|
| §2.1 — `_normalize_arabic()` "collapses yaa/alef-maqsura (`ى` → `ي`)" | **False.** `_ALEF_RE = [\u0623\u0625\u0622\u0671]` (`bilingual_registry.py:34`) covers أ إ آ ٱ only. `normalize_arabic("مصطفى") == "مصطفى"` (verified). Diacritic/tatweel stripping is real (`_DIACRITICS_RE` `[\u064b-\u0655\u0670\u0640]`). |
| §2.2 — token policy rejects bidi controls "via `RE_FORBIDDEN_CHARS`" | **Symbol does not exist** anywhere in the repo. The real mechanism is `_BIDI_CONTROL_RE` at `bilingual_registry.py:27`. |
| §1 table — `BOQ Item` defers `description` / `specification` | **Neither field exists.** `boq_item.json` has no narrative field of any kind; `BOQ Item` is purely quantity/cost. |
| §1 table — `Asset Category Account`, `Asset Finance Book` deferrals | Both are pure accounting child tables (Link → `Account`, percentages). **Zero narrative fields.** They were never deferred; they were never in scope. |
| §3.1 deliverable — "Directional Sanitizer Specification" | **Already implemented** (§2 below). |

### 1.2 What already exists — the identity/narrative split is built

The architecture the deferred document asked to design was delivered before the
deferral was written. Exact references:

| Policy | Symbol | Rejects | Allows | Tests |
|---|---|---|---|---|
| **Identity** (names, codes, titles) | `is_safe_identity_text` — `bilingual_registry.py:106` | all bidi controls via `_BIDI_CONTROL_RE` `[\u202a-\u202e\u2066-\u2069\u200e\u200f\u061c]` + `_CONTROL_RE` `[\x00-\x1f\x7f\x80-\x9f]` | — | `test_bilingual_service.py:149-169` |
| **Narrative** (rename reasons, prose) | `is_safe_narrative_text` — `bilingual_registry.py:121` | overrides/isolates `[\u202a-\u202e\u2066-\u2069]` + `_NARRATIVE_CONTROL_RE` `[\x00-\x1f\x7f\x80-\x9f]` | **LRM `U+200E`, RLM `U+200F`, ALM `U+061C`** | same file |

Both are re-exported through `bilingual_service.py:184-191` as
`validate_identity_text` / `validate_narrative_text`.

**Consequence for this cycle:** deliverable 1 of the prior blueprint (the directional
whitelist) is complete and tested. The open work is deliverables 2–4.

### 1.3 Measured narrative surface

Census across the 19 active masters and their children (`Small Text`, `Text`,
`Text Editor`, `Long Text`, `HTML Editor`), with live population:

| DocType | Field | Type | Populated |
|---|---|---|---|
| `Item` | `description` | Text Editor (HTML) | **20 / 43** |
| `Payment Terms Template Detail` | `description` | Small Text | **4 / 4** |
| `Project` | `notes` | Text Editor | 1 / 11 |
| `Project` | `message` | Text | 0 / 11 |
| `BOQ Structure` | `description` | Small Text | 0 / 59 |
| `BOQ Structure` | `description_ar` | Small Text | **0 / 59** |
| `Task` | `description` | Text Editor (HTML) | 0 / 4 |
| `Customer` | `customer_details` | Text | 0 / 12 |
| `Supplier` | `supplier_details` | Text | 0 / 10 |
| `Employee` | `bio` | Text Editor | 0 / 3 |
| `Payment Term` | `description` | Small Text | 4 / 4 |

Two census corrections: `Employee.notes` was listed previously — **the column does not
exist**; and `BOQ Structure.description_ar` was reported as "59 live rows" — it is
**0/59 populated** (59 is the table row count).

Out-of-band surface: `BOQ Cost Analysis` carries a `description_ar` column
(`boq_cost_analysis.json:157`) but has **0 rows**, and it is outside the 19 masters.

Direction-mark survey of `construction/**`: **0 literal bidi characters** in source;
**54 escape occurrences across 13 test files**, all asserting identity rejection.

### 1.4 The print defect

`construction/templates/boq_print_format.html:194`:

```jinja2
{{ node.indent }}{{ node.title | e }} / {{ node.title_ar | e }}
```

English and Arabic are joined by ` / ` with no `<bdi>` isolate and no direction mark.
The repository contains **zero** `<bdi>` occurrences (`.html`/`.js`/`.py`). In web and
PDF layout, trailing digits/parentheses/codes in the English half cross the slash and
invert punctuation.

---

## 2. Design decisions

### 2.1 Content tiering

**Tier 1 — Plain Text** (`Small Text`, `Text`): validate with the existing
`is_safe_narrative_text`. No new predicate. The whitelist question is already settled
by §1.2 and must not be re-litigated.

**Tier 2 — Rich Text** (`Text Editor`): requires an HTML-aware sanitizer that this
cycle must specify but not implement. Requirements:

- Preserve structural markup (`<p>`, `<strong>`, `<em>`, `<ul>/<li>`, `<br>`, `<a>`)
  and the `dir` attribute (`<p dir="rtl">`).
- Strip executable surfaces (script/style/iframe, `on*` handlers, `javascript:` URIs).
- Isolate **text nodes** for the Unicode check — tags are not prose and must not be
  passed to `is_safe_narrative_text` as-is, which would reject any document containing
  a literal `<` payload or entity.
- Entities must be decoded before the control-character check, otherwise
  `&#x202E;` (RLO) bypasses it while the literal character is caught.

**Decision (§2.1, approved): both — defense in depth, split by responsibility.**

1. **Save-time (`validate` hook)** is the authoritative security gate. It strips
   executable surfaces, decodes entities, then validates the extracted text nodes with
   `is_safe_narrative_text` and fails closed on Trojan Source overrides.
2. **Render-time (Jinja filters / print helpers)** is the layout isolation layer. It
   wraps mixed LTR/RTL runs in `<bdi>` so trailing punctuation and digits cannot bleed
   across a boundary. It performs **no security validation** — that is already settled
   at save time.

Save-time alone would leave legacy rows unvalidated; render-time alone would trust the
database. The split assigns exactly one responsibility to each layer.

**Audit basis:** all **29 populated narrative rows** across 11 fields were scanned for
bidi overrides/isolates (`[\u202a-\u202e\u2066-\u2069]`), direction marks
(`U+200E`/`U+200F`/`U+061C`), C0/C1 controls, and numeric entity encodings
(`&#x202E;`): **0 findings**. There is no legacy contamination to migrate, so
save-time validation can be added without a backfill or a data-repair pass.

### 2.2 Schema invariant (ratified, currently satisfied)

1. Narrative columns receive physical localized columns (`description_ar`) with **no**
   companion `_ar_norm` column.
2. Narrative columns are permanently excluded from
   `bilingual_registry.json:search.fields`, preserving the Two-Tier SLA
   (universal P95 ≤ 1.50 ms).
3. Narrative columns are **not** registry `arabic_field` values. Confirmed:
   `BOQ Structure.arabic_field == "title_ar"`, not `description_ar` — so the existing
   narrative columns are already outside the identity layer and derive no norm key.

This is a written ratification of current behaviour, not a migration. **Population is
0/59 for `BOQ Structure.description_ar` and 0/4 for `Task.description`, so no data
backfill, no schema patch, and no norm derivation is required.**

### 2.3 Print & layout standard

- Wrap mixed-direction concatenations in `<bdi>` at minimum; specify where a bare
  `&lrm;` is insufficient.
- Specify Jinja helpers (e.g. a `bdi_join` filter) so `boq_print_format.html:194` and
  its siblings stop hand-assembling direction-sensitive strings.
- CSS contract: `dir="rtl"` + `unicode-bidi: isolate; text-align: right;` on the
  Arabic cell.

---

## 3. Cycle boundary

**In scope (this cycle):** this document. Measured facts, corrected claims, ratified
invariants, and a specified-but-unimplemented Tier 2 + print design.

**Out of scope:** any code, schema patch, hook, template edit, or test. Those belong to
a successor work item that will carry its own causal evidence pipeline
(test run → log → digests → manifest → commit).

**Explicitly not re-opened:** the identity/narrative whitelist (§1.2), the
`search.fields` exclusion (§2.2), and the two-tier SLA thresholds.

---

## 4. Standing invariant

Until a successor work item is approved and merged:

1. **No narrative column** may be registered in `bilingual_registry.json`.
2. **No `_ar_norm` column** may be added to a narrative field.
3. **No narrative column** may enter any `search.fields` list.
4. Certified deferred under this document: `Payment Terms Template Detail.description`,
   `Payment Term.description`, `Task.description`, `BOQ Structure.description`,
   `BOQ Structure.description_ar`, `Item.description`, `Customer.customer_details`,
   `Supplier.supplier_details`, `Project.message`, `Project.notes`, `Employee.bio`.

---

## 5. Evidence

| Artefact | Finding |
|---|---|
| `bilingual_registry.py:27,29,34,106,121` | real symbol names and character classes |
| `bilingual_service.py:184-191` | identity/narrative re-exports |
| `test_bilingual_service.py:149-169` | narrative whitelist asserted |
| `boq_print_format.html:194` | mixed join without `<bdi>` |
| `boq_item.json`, `boq_structure.json:132`, `boq_cost_analysis.json:157` | schema census |
| live population probe | §1.3 counts |
| narrative contamination audit | 29 populated rows / 11 fields, 0 bidi, 0 marks, 0 controls, 0 entities |
| source bidi sweep | 0 literals, 54 escapes / 13 files, 0 `<bdi>` |
