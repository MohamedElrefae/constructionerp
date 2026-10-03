# Scope & Architectural Blueprint — Narrative Unicode Policy

**Work item:** `narrative-unicode-policy`
**Status:** `DEFERRED_PENDING_DESIGN`
**Base commit:** `9010731` (from `develop`)
**Date:** 2026-10-03
**Authority:** Programme architectural governance under Plan §3.2
**Outcome:** Formally recorded deferral and technical requirements boundary for rich-text, multi-line prose, and child-table narrative fields across ERPNext / Construction doctypes.

---

## 1. Context: The Cumulative Narrative Deferrals

Throughout Waves 1, 2, and 3, the bilingual enablement programme strictly scoped each master to single-line identity fields (`Item.item_name`, `Account.account_name`, `Customer.customer_name`, `Task.subject`, `Asset Category.asset_category_name`, etc.). Whenever free-text, rich-text, or multi-line tabular descriptions were encountered, they were deferred to protect the sub-millisecond Two-Tier Search SLA and server-authoritative token normalization.

These deferrals have now accumulated across five distinct entities:

| Master / Area | DocType | Field(s) | Field Type | Live Rows / Usage |
|---|---|---|---|---|
| **BOQ** | `BOQ Item` | `description`, `specification` | Small Text / Text | Project bill-of-quantities line specifications |
| **Projects** | `Task` | `description` | Text Editor (HTML) | Operational task breakdowns, progress logs |
| **Assets** | `Asset Category Account`, `Asset Finance Book` | sub-ledger configurations | Child Table | Per-company capitalisation and book accounting |
| **Selling/Buying** | `Payment Terms Template Detail` | `description` | Small Text | 4 live rows (`_Test Net 30 Days`, `_Test Cash on Delivery`) |
| **Selling/Buying** | `Payment Term` | `description` | Small Text | 4 live rows (standalone operational terms clauses) |

Rather than continuing to record piecemeal exclusions in individual master descriptors, this document establishes a single, named architectural work item capturing the technical problem statement, security boundaries, and required design deliverables.

---

## 2. Why Token-Level Bilingual Policy Fails on Narrative Prose

The existing bilingual infrastructure in `construction/services/bilingual_service.py` is purpose-built for **short identity tokens** (names, codes, titles). Applying that engine to narrative prose introduces three fatal architectural conflicts:

### 2.1 Lexical Normalization vs. Typography & Legibility
`_normalize_arabic()` strips diacritics (tashkeel), strips tatweel (kashida), unifies alef variants (`إ`, `أ`, `آ` $\to$ `ا`), and collapses yaa/alef-maqsura (`ى` $\to$ `ي`).
- In a search key (`*_ar_norm`), this enables resilient search matching.
- In long-form Arabic prose, contracts, or specifications, stripping or normalizing these characters corrupts legibility, grammar, and contractual precision. Narrative Arabic must preserve original orthography in storage and display.

### 2.2 Bidi Control Security vs. Mixed-Direction Contractual Formatting
The token policy strictly rejects all Unicode bidirectional controls via `RE_FORBIDDEN_CHARS`:
`[\u202A-\u202E\u2066-\u2069\u200E\u200F\u061C\x00-\x1F\x7F]`
- In single-line identity tokens, banning all bidi controls is essential to prevent CVE-class spoofing (e.g. Trojan Source, visual confusion in ledger codes).
- In narrative paragraphs, legitimate mixed-direction text (e.g. English technical codes, model numbers, DIN standards, or currency amounts embedded inside Arabic contractual sentences) **requires** directional marks (`U+200E` LRM, `U+200F` RLM) or isolates (`U+2066`–`U+2069` LRI/RLI/FSI/PDI) to prevent browser and PDF layout engines from inverting clause numbers or punctuation.
- A blanket ban on `U+200E`/`U+200F` makes correct bidirectional paragraph typesetting mathematically impossible, while unconstrained admission reintroduces Trojan Source spoofing.

### 2.3 HTML & Rich-Text Entity Corruption
`Task.description` and related narrative fields use Frappe's `Text Editor` (Quill.js / HTML).
- Token normalization cannot distinguish between HTML tags (`<p dir="rtl">`, `<span class="mention">`, `<strong>`) and user payload text.
- Running token validation or normalization against HTML either strips tags or generates corrupted search keys containing HTML entity fragments.

### 2.4 SLA Destruction in Dropdown Link Search
Frappe link fields (`searchable_link_search`) are bounded by the Two-Tier SLA ($\le 1.50\text{ ms}$ universal absolute P95, $\le 1.50\times$ relative trade-off band).
- Indexing and substring-matching 500-word contractual paragraphs in link autocompletion destroys database memory buffers, blows through the 1.50 ms ceiling, and delivers an unusable dropdown UX.
- Narrative search belongs to Full-Text Search (FTS / MariaDB `MATCH ... AGAINST`), completely decoupled from link dropdown navigation.

---

## 3. Required Deliverables for the Narrative Design Cycle

When `narrative-unicode-policy` is activated for implementation, it must deliver:

1. **Directional Sanitizer Specification**:
   - Explicit whitelist distinguishing permitted typographic directional marks (`U+200E` LRM, `U+200F` RLM, and isolating formatting pairs `U+2066`–`U+2069` if balanced) from strictly banned visual spoofing overrides (`U+202A`–`U+202E` LRE/RLE/PDF/LRO/RLO).
2. **HTML / Rich-Text Parser & Tag Protection**:
   - An AST-based or `bleach`-based tag/attribute sanitizer that isolates inner text nodes for language validation while preserving HTML markup, `dir="rtl"` attributes, and structured lists.
3. **Decoupled Schema Strategy**:
   - Narrative fields receive physical localized columns (e.g. `description_ar` Small Text / Text Editor) **without** companion `_ar_norm` columns.
   - Exclusion of narrative columns from `bilingual_registry.json:search.fields` to safeguard the link-search SLA.
4. **Print & PDF Layout Conventions**:
   - Standard Jinja template helpers for rendering localized narrative with correct CSS directionality (`dir="rtl"`, `unicode-bidi: isolate; text-align: right;`).

---

## 4. Standing Invariant & Programme Rule

Until the design cycle above is formally approved and implemented:
1. **Zero Narrative Fields in Link Registry**: No child-table description, rich-text editor field, or multi-line narrative column may be registered in `bilingual_registry.json`.
2. **Exclusion Precedent**: `Payment Terms Template Detail.description`, `Task.description`, `BOQ Item.description`, and `Payment Term.description` are certified as deferred under the authority of this document.
