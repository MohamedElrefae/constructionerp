# F18 — Cost database and draft repricing service-contract design

**Date:** 12 October 2026  
**Baseline:** develop c9e6803c5ac63073aeb0b166c779844d29051d8d  
**State:** Draft design; not implementation, domain acceptance or runtime evidence  
**Audience:** Engineering, estimating, Finance/QS and Mohamed — confidential internal

References: [master plan](construction_foundation_remediation_master_plan_2026-10-12.md), [work register](construction_foundation_work_register_2026-10-12.md), [source evidence](construction_foundation_f18_f19_contract_source_evidence_2026-10-12.json), [F19 design](construction_foundation_f19_service_contract_design_2026-10-12.md), [confirmed financial rules](../customer-release-gap-fixes/FINANCIAL_RULES.md).

## 1. User outcome and scope

An authorized user downloads a supported workbook template, validates a small resource/template library against one company, understands errors, explicitly imports it, then previews and confirms rate changes on eligible Draft cost analyses. The user sees saved outcomes and their permitted records without using an API client or console.

Reuse existing import/rate-selection/pricing services. The new surface is a minimal native Desk page/dialog workflow, linked from the relevant workspace. Do not introduce automatic template application, revised-quantity procurement planning, new FX formulas or changes to approved pricing. Actual page names/routes and final API identifiers are implementation choices; no proposed route here is claimed to exist.

## 2. Current contracts at source

| Existing operation | Input / transport | Output / behavior |
|---|---|---|
| download_cost_database_template | mode blank/sample; existing method decorator uses framework defaults | Binary XLSX; filename/content type supplied; sample is illustrative, not a customer cost benchmark |
| import_cost_database | POST multipart file, company, dry_run, auto_submit, region, price_date | dry_run omitted defaults to **false**; HTTP gate needs Resource Price History create; service also checks Company read and applicable Item/Analysis/UOM/document rights |
| reprice_cost_analyses | POST JSON/form with company/header/item/resource/stream/region/date/dry_run | dry_run omitted defaults to **false**; Analysis write gate; service selects Draft/docstatus0 and defaults atomic=True |

Import result keys: success, dry_run, records_created, records_updated, records_skipped, errors, warnings. Count buckets describe Items, Resource Price History and BOQ Cost Analysis templates; returned dictionaries/lists can be empty, especially preview/early failure. Do not invent proposed record counts or persisted names from a successful dry-run.

Reprice normally returns success, analyses_touched, details_updated, details_unchanged and errors. Preview counters refer to prospective changes, not saved writes. The resource_type no-match branch currently omits success; normalize only a verified empty/no-error result. Unknown/malformed replies remain errors.

## 3. Screens and state transitions

| Step | Screen content / action | Required state transition |
|---|---|---|
| Start | Company, permitted operation, template download; current scope displayed | No mutation on page load |
| Import inputs | File name/size, company, region/date; auto-submit off by default | Changing any input invalidates the previous preview |
| Validate | Explicit dry_run=true; display error/warning list, omitted-message count and supported effects | Preview is marked validation-only; commit disabled on any blocking error |
| Confirm import | Show affected entity types, actual available impact information and whether templates will remain Draft | Fresh successful preview plus explicit confirmation; auto_submit remains an opt-in requiring submit permissions |
| Import result | Persisted created/updated/skipped names/counts, permitted links and warnings | Success only after service commit succeeds; a failed/rolled-back result displays no false “created” records |
| Reprice inputs | Mandatory company; optional header/item/resource/type/stream/region/date; all drafts selection explicit | Scope summary visible; each child selection belongs to its selected parent |
| Reprice preview | Old/new rate, currency/UOM, provenance, exact Draft analyses/rows and aggregate counts | Prospective changes only; no totals or approvals saved |
| Confirm reprice | Revalidate preview and show affected Draft scope/counts | Atomic mutation; no partial-success mode exposed |
| Reprice result | Updated/unchanged counts, skipped no-rate information and permitted links | Reopen analyses to prove persisted changes; submitted history stays unchanged |

Keep a single in-flight action; disable repeated submission buttons until a definitive result. A timeout means outcome unknown, not failed or successfully committed. Query saved operation evidence/revalidate before retrying; never blindly repeat a mutation. Existing deduplication is useful, but it is not a general idempotency key for every action.

## 4. Server-side boundary and role contract

The caller must be authenticated. Use native DocType permissions plus Company read and explicit Header/Project scope checks; do not rely on top-bar filtering. Resolve current role grants on the actual F03/F11 site. A Construction Owner/PM role name alone does not establish import permission. Site Engineer and unassigned-company users receive denial without previewing existing private record names.

- Import validation and commit enforce the same rights: target Company, resource/master creates, writes to existing Item/templates, UOM creation where required and optional Analysis submission. Retain the service's preflight checks.
- Repricing needs read/write access to **every selected Draft analysis** and permitted linked resources/rate sources. A revoked permission between preview and commit invalidates the operation.
- Scope parameters are normalized scalars; reject invalid parent chains rather than silently widen selection. Company is required in the UI boundary even though the current internal repricing service accepts None.
- Read-only template download uses existing permission policy and contains no site business data; no guest mutation or broad administrative grants are introduced.
- Never impersonate Administrator, add ignore_permissions to make the UI work, or let client-supplied user/role determine authorization.

Resource Item and UOM are shared native masters. Selecting a company scopes price/history/template context, but does not turn an Item-name/type update into a company-private change. Preview/confirmation must disclose shared master writes and retain their native permissions; do not conceal them as price-only imports.

## 5. Preview and mutation binding — proposed contract additions

The current APIs provide no preview token/state binding. Before connecting a confirmation button, introduce a narrow adapter contract that binds actor, file digest or normalized selection, all option values, candidate/pricing-rule version, affected record states and a short expiry. Proposed expiry: ten minutes, subject to implementation review.

A server-generated opaque token/nonce identifies the successful preview. Import uses the same workbook bytes and options; reprice uses the same selected Draft records, source rates and modifiers. Any change in bytes, scope, permissions, docstatus, analysis/rate state or options invalidates the preview and requires refresh. Store no credentials or full private workbook contents in a client-readable token. Re-run validation on commit; authorization is never cached as a grant.

Do not make the token a new commercial document/approval. Use a bounded temporary server mechanism or equivalent reviewed request fingerprint. Final token storage and race-safe compare/lock implementation belongs to engineering; it must preserve existing transaction/savepoint behavior and receive failure/concurrency tests.

### Proposed adapter envelope

| Field | Meaning |
|---|---|
| operation / phase | import or reprice; preview or commit; validated enum |
| success / outcome | validated / committed / no_change / rejected / stale / outcome_unknown |
| preview_token / expires_at | Only on a successful bound preview; proposed, not in current API |
| effective_scope | Authorized company/header/item/filter summary |
| persisted counts / proposed counts | Clearly different; include only evidence-backed values |
| changes | Bounded affected-row/provenance preview where supported by adapter; not fabricated from current counters |
| warnings / errors | Structured display with omitted-message count; safe document references only |
| links / request reference | Permitted saved records and a traceable retry/outcome reference |

Retain the existing APIs for compatibility; new adapter identifiers must be chosen, registered and guarded explicitly. Normalize inconsistent existing return shapes at the boundary, without swallowing permission errors or turning exceptions into a successful empty result.

## 6. Numeric, currency, UOM and rate provenance

Owner rules remain additive on direct cost, positive factors, positive analysis_qty and safe restoration. Import/reprice must not alter contract selling rates or submitted analysis history. No automatic FX or UOM conversion is designed here.

The current bulk lookup reads history rate/company/supplier/region/date/source but **does not load currency, exchange_rate or UOM**; Item Price fallback also lacks that context. Therefore the UI cannot claim currency/UOM-safe repricing from its current payload. F18-SC03 requires additional provenance validation before commit: identify source row and unit/currency, compare with target analysis/resource unit, and block unsupported mismatch. A separate confirmed conversion policy is required if a real workflow needs conversion; never copy a differently denominated number silently.

Preserve existing Last PI → Last PO → other active history → buying Item Price selection semantics after their exact company/supplier/region/date cases pass. No valid positive suggestion currently means no change; that must be labelled skipped/no compatible rate, not “unchanged same rate.” Import price history currencies remain visible as recorded; adding UI must not relabel them as company-currency values.

## 7. Limits and failure policy

Existing cost import limits: 25 MiB, ten worksheets, 2,000 imported rows, 50,000 traversed rows and 100 returned messages. Preserve ZIP/XML/numeric prechecks, native precision and atomic rollback. No harmful oversized owner fixtures; engineering supplies safe bounded rejection samples.

Reprice source uses limit_page_length=0 for several selections; comments about bounded queries do not establish a hard workload ceiling. Proposed UI boundary: maximum 200 analyses / 2,000 detail rows per operation, reject rather than silently truncate, then measure in F14/F37. These are proposed engineering bounds, not source constants or capacity claims. Global selection requires an explicit “all eligible drafts in this company” choice, a fresh preview and those limits.

Failure classes: invalid workbook/input; permission denial; stale preview; exceeded limit; no compatible rate; transactional save failure; transport timeout/unknown outcome. Errors must identify corrective action and preserve old business data. For import rollback, records_updated/skipped may describe attempted work; the UI must not present them as persisted changes after success=false.

## 8. Acceptance cases to add through F43

| Design case | Steps / input | Required evidence |
|---|---|---|
| F18-U01 | Download blank/sample, English/Arabic workbook headers | Opens supported template; sample clearly illustrative |
| F18-U02 | Valid import preview | Explicit preview; no created/updated business rows |
| F18-U03 | Commit same valid workbook | Counts/names and reopened Item/history/template match; pricing remains correct |
| F18-U04 | Malformed, ambiguous/invalid numeric, over-limit file | Clear blocking errors; no partial writes; inherited limits enforced |
| F18-U05 | Exact re-import and modified one-price row | Existing dedup/update/skip behavior explained; submitted templates unchanged |
| F18-U06 | Auto-submit off/on with permitted and denied roles | Draft default; authorized explicit submission only |
| F18-U07 | File/filter/docstate/permission change after preview | Commit refused as stale; no silent expanded operation |
| F18-U08 | Reprice Preview → Commit | Exact Draft rows and old/new rates; submitted/Approved/Superseded/Cancelled records unchanged |
| F18-U09 | Invalid company/project/type/stream; foreign currency/UOM source | Rejected or safely skipped with explanation; no copied incompatible numeric rate |
| F18-U10 | Atomic mid-operation failure, double click and timeout/retry | Complete rollback/no duplicates and traceable uncertain outcome |
| F18-U11 | Zero/no matching eligible rows and inconsistent source result shape | Clearly no change, no fabricated success/created records |
| F18-U12 | Arabic UI, keyboard, stale result and download/links | Legible states; latest inputs displayed; private files/links remain authorized |

Design IDs are not execution records or final UI-70+ IDs. F43 maps them into the owner workbook with independent expected values; OS-04 is the dedicated owner session group. Technical allowed/denied/server/concurrency checks accompany the owner cases.

## 9. Delivery prerequisites and open design items

F18 implementation/closure depends on F03 actual routes/permissions, F07 commercial correctness and F14 limits; F13/F02 provide a safe coherent runtime for verification. Additional work is recorded as F18-SC01–04 in the shared source-evidence artifact. Resolve response normalization, preview binding, hard operation caps and currency/UOM provenance before UI commit is enabled. Routine page/layout naming is engineering-owned; unresolved business conversion semantics need Finance/QS/Mohamed decisions.

This draft does not broaden the future-module hold or close any runtime gate. No code, DocType, role grant, upload, source file, site or tests were changed/run by this design task.
