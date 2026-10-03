# Scope Descriptor — bilingual-narrative-sanitizer

**Work item:** `bilingual-narrative-sanitizer`
**Branch:** `feature/bilingual-narrative-sanitizer`
**Status:** `COMPLETE` — implemented service, hooks, templates (5 sites), tests; 20/20 unit tests, 153/153 regression matrix (12 modules), 19/19 reconciliation verified
**Base commit:** `38beb35d31026e0afc70dd43e0ccf8de7dc1a222` (develop clean; `narrative-unicode-policy` design `APPROVED`)
**Date:** 2026-10-03
**Authority:** approved design at `docs/ai/work-items/narrative-unicode-policy/SCOPE.md`,
owner instruction in session
**Scope:** new `construction/services/narrative_sanitizer.py`, a Jinja `bdi_join` filter,
one test module, and the wiring that connects them.

---

## 1. What the approved design commits us to

From `narrative-unicode-policy` (APPROVED at `6e7bb43`):

1. **Tier 1 — Plain Text:** validate with the existing `is_safe_narrative_text`.
   No new predicate. Already implemented and tested; must not be re-litigated.
2. **Tier 2 — Rich Text:** HTML-aware validation that isolates text nodes and
   decodes entities before the Unicode check.
3. **Schema invariant:** narrative columns get no `_ar_norm` and never enter
   `search.fields`.
4. **Print:** `<bdi>` isolation for mixed-direction concatenation.

This work item implements 2, 3 (as an enforced rule) and 4. Item 1 needs only a
call site.

---

## 2. Findings that reshape the original blueprint

### 2.1 Frappe already strips executable HTML — and our hook runs *before* it

`frappe/model/document.py` save/insert order:

```
run_before_save_methods()  → run_method("validate")       ← app hook (this work item)
_validate()                → _sanitize_content()          ← Frappe XSS pass
                            → sanitize_html() → nh3.clean()
```

`base_document.py:1296 _sanitize_content()` runs on **every** save of every string
field, invoking `sanitize_html` (`frappe/utils/html_utils.py:146`) which delegates to
`nh3.clean` against a tag/attribute whitelist (`acceptable_elements`,
`acceptable_attributes`, `ALLOWED_URL_SCHEMES`).

**Consequence:** stripping `<script>`, `on*` handlers and `javascript:` URIs is
**not** our deliverable. Duplicating it would (a) re-do Frappe's work, (b) run before
nh3 sees the value, and (c) drift from Frappe's whitelist on every upgrade.

**Consequence 2:** because our `validate` runs *first*, we observe the value as the
user submitted it. That is the correct place for a fail-closed Unicode gate: a
numeric entity such as `&#x202E;` must be decoded and rejected **before** any later
pass touches the string.

### 2.2 `bleach` is not the engine and is not our dependency

`sanitize_html` uses **`nh3`**, not `bleach`. `bleach` appears only as
`bleach_allowlist.all_styles` (a property list), and it is **not declared in
`construction/pyproject.toml`** — it arrives transitively via Frappe. The design must
not depend on `bleach` or `html5lib` directly.

### 2.3 The real gap: nh3 has no bidi policy

`nh3.clean` removes executables; it has no concept of `U+202E`. A document containing
a right-to-left override passes Frappe's XSS filter unchanged. The contamination
audit in the approved design (31 populated rows across 27 fields, 0 findings) confirms nothing is
currently stored — which is precisely why the gate must be added **now**, before the
first contaminated value is written.

### 2.4 Short-circuit worth knowing

`_sanitize_content` skips any value without `<` or `>` (`base_document.py:1312`).
Plain Tier 1 text therefore never reaches nh3 — our direct `is_safe_narrative_text`
call is its only gate.

---

## 3. Deliverables

### 3.1 `construction/services/narrative_sanitizer.py`

- `sanitize_and_validate_html(text) -> str | raises`
  - Decode HTML entities **first** (`html.unescape`), so `&#x202E;` and
    `&rlm;` forms are checked as characters, not as inert text.
  - Parse with **stdlib `html.parser`** (no new dependency; `bs4`/`lxml` are Frappe's,
    not ours to bind to).
  - Walk text nodes; validate each with `is_safe_narrative_text`, imported
    **read-only** from `bilingual_registry`.
  - **Fail closed**: raise `frappe.ValidationError` naming the offending codepoint
    and field. Do not silently strip — silent stripping would let a crafted
    document round-trip into a different meaning.
  - Preserve markup untouched; do not re-serialize unless a node fails.

- Import contract: `from construction.services.bilingual_registry import
  is_safe_narrative_text`. **Read-only.**

### 3.2 Wiring — save-time gate

- Registered through `doc_events` in `construction/hooks.py` under the `validate` hook.
- **Settled coverage: 10 doctypes carrying 27 narrative fields** (parents + children).

**Tiers are assigned per field, not per doctype — every one of these doctypes is
mixed-tier**, so a doctype-level tier label would be wrong:

| Doctype | Narrative fields (field:tier) |
|---|---|
| `Item` | `description`:2 · `customer_code`:1 |
| `Task` | `description`:2 · `Task Depends On.subject`:1 · `Task Depends On.project`:1 |
| `Project` | `notes`:2 · `message`:1 · `Project User.project_status`:1 |
| `Employee` | `bio`:2 · `current_address`, `permanent_address`, `family_background`, `health_details`, `reason_for_leaving`, `feedback`:1 · `Employee Education.school_univ`:1 · `Employee Education.maj_opt_subj`:1 · `Employee External Work History.address`:1 |
| `Customer` | `primary_address`:2 · `customer_details`:1 |
| `Supplier` | `primary_address`:2 · `supplier_details`:1 |
| `BOQ Structure` | `description`:1 · `description_ar`:1 |
| `UOM` | `description`:1 |
| `Payment Term` | `description`:1 |
| `Payment Terms Template` | *(none of its own)* · `Payment Terms Template Detail.description`:1 |

(`1` = Tier 1 plain, `2` = Tier 2 rich text.)

`Payment Terms Template` is listed because it **owns** a child that carries narrative,
not because it has a narrative field itself.

**Child-table coverage mechanism:** Frappe `doc_events` are keyed on `doc.doctype`
(`document.py:1574-1575`), and child rows are not passed through `save()` during a
parent save — they are written by `update_children()`. The handler
(`validate_narrative_fields(doc, method=None)`) therefore validates the parent and
iterates `doc.get_all_children()`, mirroring Frappe's own traversal at
`document.py:801-810`. This covers, without separate registrations:
`Payment Terms Template Detail`, `Employee Education`, `Employee External Work History`,
`Task Depends On`, `Project User`.

**Measured basis (full sweep of all 27 fields across all 19 registry masters plus
`Payment Term`):** 31 populated values, **0** contaminated — no bidi
overrides/isolates, no direction marks, no C0/C1 controls, no numeric entity
encodings. The gate can be added with no backfill or data repair.

(These figures, and the addition of `UOM` as a tenth doctype, supersede both the
11-field / 29-row figures in `narrative-unicode-policy` §1.3 and the 9-doctype /
26-field draft of this section — each corrected against a complete sweep rather
than a sample.)

### 3.3 Print isolation — `bdi_join`

- Registered via Frappe's standard `jinja` hook
  (`frappe/utils/jinja.py:212 get_jinja_hooks()`, `get_hooks("jinja")` at `:239`;
  applied in `get_jenv()` at `:26-28`). `construction/hooks.py` has **no** `jinja`
  hook today, so this is purely additive.
- **Escaping contract (decisive, avoids double-escape):** the filter escapes each
  element itself (`markupsafe.escape`) and wraps it in `<bdi>`. The template then
  **drops** its `| e`:

  ```
  before:  {{ node.title | e }} / {{ node.title_ar | e }}
  after:   {{ [node.title, node.title_ar] | bdi_join(" / ") }}
  ```

  If the template kept `| e` the output would double-escape (`&amp;lt;`).
- First consumer: `construction/templates/boq_print_format.html:194`.

---

## 4. Invariants

1. **`bilingual_service.py`, `search.py`, `bilingual_registry.json`: 0 diff lines.**
2. **No narrative column** added to `bilingual_registry.json` or any
   `search.fields` list (ratified in the approved design).
3. **No `_ar_norm`** column for any narrative field.
4. All SQL parameterized (AGENTS.md §4.1).
5. New `hooks.py` entries → bump the relevant `?v=` cache busters (AGENTS.md §4.4).
6. No new Python dependency; stdlib `html.parser` only.

---

## 5. Tests

New module `construction/tests/test_bilingual_narrative_sanitizer.py`:

- Entity-decoded override rejected: `&#x202E;`, `&#8238;`, `&rlm;`-style forms.
- Literal `U+202A`–`U+202E`, `U+2066`–`U+2069` rejected in a text node.
- LRM/RLM/ALM **accepted** (matches `is_safe_narrative_text`).
- Markup preserved: `<p dir="rtl">`, `<strong>`, `<ul>/<li>`, `<br>` survive.
- Text inside a failed node still caught (`<p>bad&#x202E;</p>`).
- `bdi_join` produces `<bdi>…</bdi>` per element, escapes once, no double-escape.
- Read-only import proven (no write to registry).
- `cleanup.leftover == 0`.

---

## 6. Evidence pipeline (causal order, mandatory)

`test run → capture log (2>&1) → git add -f the .log → compute git-blob digests →
MANIFEST.json → commit → merge`

- New module must pass standalone.
- Canonical 133-test matrix must stay green.
- Note `.gitignore:27 *.log` in the **app** repo — directory `git add` silently
  drops logs; always `git add -f`.
- Verify digests against `git ls-files` / `git show HEAD:<path>`, **not** `os.walk` —
  the latter passes for untracked files on disk.

---

## 7. Out of scope

- `Company` (GATED on legal/tax/statutory review).
- Any change to identity-field policy (`is_safe_identity_text`).
- Full-text search over narrative prose (belongs to FTS, not link dropdowns).
- The `search.fields` / SLA thresholds.

---

## 8. Amendments (post-completion)

Two entries in `evidence/MANIFEST.json` pin **living** artefacts rather than
evidence of this work item. Both were correct at completion (`38beb35`) and were
re-pinned on 2026-10-03 so that repository-wide `HEAD` verification passes again.
The immutable evidence of this work item — `test_bilingual_narrative_sanitizer.log`
(20/20), `regression-matrix.log` (12 modules / 153 tests), `reconciliation.log`
(19/19) — is unchanged.

| Artefact | Pin at completion | Re-pinned to | Why it moved |
|---|---|---|---|
| `scripts/run_bilingual_regression_matrix.sh` | `e93ca1434ac5fcef0c5fa7caef1dbb0109c0184deef671da44462ad410d560b4` | current | shared runner expanded to 13 modules / 171 tests by `transactional-link-resolution` (`2e17df5` and successors) |
| `construction/hooks.py` | `6b30efaea1e9f00ae7a677b71b278c03e32b2a1bf0beedbca0be2364147e7d97` | current | living file; modified by `bilingual-boq-title-ar-wiring`, `?v=1` cache buster for `searchable_dropdown.js`, and later work items |

Consequence: this manifest asserts **content that still exists in the repository**,
not the byte state at `38beb35`. Use `git show 38beb35:<path>` to recover the
completion-time bytes.

### 8.1 Re-pin by `bilingual-brand-master` (2026-10-03)

| Artefact | Re-pinned from | Why it moved |
|---|---|---|
| `scripts/run_bilingual_regression_matrix.sh` | `0252438c3342d0093cfbd8c8be6e2c7270203d9569ac936e3b04d1449ca224e4` | shared runner expanded to **14 modules / 181 tests** by `bilingual-brand-master` |
| `construction/hooks.py` | `71e3b32963525a46f7e2e83d42871eb158415e53d51ba4ec523ca760235a5c72` | living file; `Brand` `doc_events` registration added (finding F1) |

New digests are recorded as `amendments[]` entries in `evidence/MANIFEST.json`; this
work item's own evidence logs remain unchanged.
