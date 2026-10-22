# Stage 2 — AI-A1 Source-Equal Exception Triage

**Review role:** AI-A1 Arabic linguistic reviewer  
**Reviewer identity:** Codex sub-agent `/root/stage2_ai_a1`  
**Session:** independent Stage 2 source-equal triage requested by the root agent  
**Model:** Codex, GPT-5 family (exact deployment identifier is not exposed to this session)  
**Reviewed at (UTC):** 2026-09-04T21:21:15Z  
**Repository commit:** `e7be48855bde540464ea302e53c9bfca62b7c462`  
**Scope:** only the three source-equal strings flagged in `stage-2-inventory.md`. This record does not review, populate, or approve the 7,322 empty catalog entries.

## Governing inputs

| Artifact | SHA-256 |
|---|---|
| `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| `docs/ai/work-items/erp-arabic-bilingual-data/BUILD_HANDOFF.md` | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| `docs/ai/work-items/erp-arabic-bilingual-data/IMPLEMENTATION.md` | `c0283cabfb961dd6f726296b0d6160269a271d958225f9038ec153abe7a790d4` |
| `docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-2-inventory.md` | `7f2f4e0a048f438f82f792ea652593eece19c0aaa417e848ed9a87302050b3e4` |
| `../erpnext/erpnext/locale/ar.po` | `2dfe0a5d07b091d1d34563fa53aac9f4665519aa9672303b4cd6fe3b2d705275` |
| `../frappe/frappe/locale/ar.po` | `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` |

The worktree was already dirty with Builder-owned Stage 1/2 changes. This review made no code, catalog, database, or Git-state change; only this evidence file was added.

## Decisions

### 1. `Produced`

- **Catalog:** `../erpnext/erpnext/locale/ar.po:36346`, currently `msgstr "Produced"`.
- **Source context:** `../erpnext/erpnext/subcontracting/doctype/subcontracting_inward_order/subcontracting_inward_order.json:184`; a read-only `Status` Select option in `Subcontracting Inward Order`, alongside `Draft`, `Open`, `Ongoing`, `Delivered`, `Returned`, `Cancelled`, and `Closed`.
- **Source SHA-256:** `2a0144dff96673069f72ffc50f6a120fa609436260028c2fcbdab49ec723c4d7`.
- **Decision:** requires Arabic translation; the source-equal value is an untranslated legacy fallback, not an intentional technical token.
- **Proposed Arabic:** `تم الإنتاج`
- **Confidence:** high.
- **Rationale:** the source is a completed workflow status, so the concise Arabic status phrase “تم الإنتاج” is clearer and more idiomatic than leaving English or using an ambiguous noun. This decision is context-specific to the `Produced` status; it does not automatically prescribe translations for longer strings such as `Produced Qty`.
- **Placeholder/structure:** no placeholders; no structural constraint beyond preserving the status meaning.

### 2. `Prevdoc DocType`

- **Catalog:** `../erpnext/erpnext/locale/ar.po:35531`, currently `msgstr "Prevdoc DOCTYPE"`.
- **Source context:** `../erpnext/erpnext/stock/doctype/packed_item/packed_item.json:193`; label of hidden, read-only, print-hidden Data field `prevdoc_doctype` in `Packed Item`.
- **Source SHA-256:** `4d0133ba51ef5c6e53c569c66bf40af98ebae73a2baf122ee6f3c37ca4c944b0`.
- **Decision:** requires Arabic translation if surfaced through metadata/customization; it is not a proper noun or code token. Its hidden technical nature lowers UI priority but does not justify an English source-equal Arabic value.
- **Proposed Arabic:** `نوع المستند السابق`
- **Confidence:** high.
- **Rationale:** `Prevdoc` abbreviates “previous document,” while Frappe `DocType` denotes the document type. The proposed phrase preserves that precise metadata meaning without exposing internal English jargon. The fieldname `prevdoc_doctype` and stored value must remain unchanged; this decision concerns the visible label only.
- **Placeholder/structure:** no placeholders; do not translate or rename the database fieldname or its stored DocType identifiers.

### 3. `Fw: {0}`

- **Catalog:** `../frappe/frappe/locale/ar.po:11092`, currently `msgstr "FW: {0}"`.
- **Source context:** `../frappe/frappe/core/doctype/communication/communication.js:294`; translated subject template passed to the Communication Composer when forwarding mail.
- **Source SHA-256:** `980f23fa2201133ce78307b54b5e0e53198e1955220799d375c937b21f791b25`.
- **Decision:** requires Arabic translation; `FW` is an English mail abbreviation, not a language-neutral technical token in an Arabic subject template.
- **Proposed Arabic:** `إعادة توجيه: {0}`
- **Confidence:** high.
- **Rationale:** “إعادة توجيه” is the clear Modern Standard Arabic action used for forwarding a message. The colon and following space are retained, and the original subject is interpolated at the same position.
- **Placeholder/structure:** **exactly preserved:** source `{0}` → proposal `{0}` (one occurrence, unchanged spelling and index).

## Triage outcome and gates

| Source | Classification | AI-A1 result |
|---|---|---|
| `Produced` | Untranslated user-visible workflow status | Translate as `تم الإنتاج` |
| `Prevdoc DocType` | Hidden technical label, potentially surfaced through metadata | Translate label as `نوع المستند السابق`; never alter identifier/value |
| `Fw: {0}` | Untranslated user-visible mail subject template | Translate as `إعادة توجيه: {0}`; placeholder preserved exactly |

**AI-A1 verdict:** all three flagged values are untranslated legacy source-equal entries. None qualifies for the intentional technical/proper-token allowlist, and none appears invalid or stale in the inspected source checkout.

**Blockers to this linguistic triage:** none.

**Remaining release gates:** these proposals are AI-A1 decisions only. They must not be marked `Released` or imported into runtime solely from this record. Apply the plan's independent AI-A2 applicability decision, AI-A3 structural review, exact-artifact AI-R verification, and owner operational authorization where required. Vendor catalogs were not edited by this review.
