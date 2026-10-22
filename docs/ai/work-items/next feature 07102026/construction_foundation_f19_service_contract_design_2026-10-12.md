# F19 — Existing estimation reports and integrity-view service contracts

**Date:** 12 October 2026  
**Baseline:** develop c9e6803c5ac63073aeb0b166c779844d29051d8d  
**State:** Draft design; no report/API/UI implementation or runtime qualification  
**Audience:** Engineering, Finance/QS and Mohamed — confidential internal

References: [master plan](construction_foundation_remediation_master_plan_2026-10-12.md), [work register](construction_foundation_work_register_2026-10-12.md), [source contracts](construction_foundation_f18_f19_contract_source_evidence_2026-10-12.json), [F18 design](construction_foundation_f18_service_contract_design_2026-10-12.md), [financial rules](../customer-release-gap-fixes/FINANCIAL_RULES.md).

## 1. Outcome and narrow scope

Expose five existing read-only report services as usable Desk views, plus a separately restricted integrity-exception view using the existing audit. An authorized user selects company/header or price-history filters, sees clearly defined figures, follows permitted document links and exports the same authorized result.

The initial surface can be one native page with report tabs and shared filters; native query-report definitions are acceptable if their execution/export routes enforce the same boundary. Choose actual page/report identifiers during implementation. There are no existing customer query-report definitions promised by this draft.

No new committed-cost, actual-cost, earned-value, cost-to-complete, revised-resource forecast or certificate dashboard is included. Do not aggregate incompatible currencies/UOMs or invent a new financial source of truth while exposing existing calculations.

## 2. Five views: source behavior and display contract

| View / existing function | Current source behavior | Proposed user contract |
|---|---|---|
| Analysis summary / get_boq_cost_analysis_summary(header) | Joins item/analysis; selects docstatus=1, including **Superseded** submitted analyses; direct cost, margins, allowance, pricing-rule and suggested rate | Make status/history explicit. Default current Approved view is a server-side presentation filter; optional submitted history shows superseded rows distinctly. Never label every returned row current approved or sum alternative analysis versions |
| Item cost vs contract / get_boq_item_cost_vs_contract(header) | Current estimated direct cost and contract rate, selling-price/margin inputs, cost basis/active reference; margin_pct=(contract-cost)/cost and zero when cost=0 | “Markup on direct cost %” label, not gross margin %. Zero basis percentage is undefined/blank with explanation. Display manual/Approved Analysis/Legacy Review basis, not a blanket approved-cost claim |
| Resource requirements / get_resource_requirement_summary(header) | Only Approved/docstatus1 analysis rows; contract qty × factor × wastage ÷ analysis_qty; resource totals and weighted avg rate | Label **Contract-quantity resource plan**, not revised procurement or actual usage. Factor/wastage/batch normalization once; preserve invalid-factor/legacy-analysis refusal |
| Active price history / get_resource_price_history(filters) | Active rows only; item/supplier/region/date filters; no company argument, permission-aware selection or result limit at helper boundary | Require authorized Company and row scope before query; show recorded currency/UOM/exchange rate/source. No cross-currency aggregate or claims about cancelled rows; add bounded SQL filter/limit support |
| Missing analysis / get_boq_items_missing_analysis(header) | Items with docstatus<2 and no Approved/docstatus1 analysis | “No current approved analysis” list; manual estimates visible where permitted. No-analysis does not mean zero cost, invalid contract or mandatory new approval |

The existing helper functions are internal and not whitelisted. Their raw SQL/query-builder paths do not establish a safe customer RPC boundary. This is a UI exposure prerequisite, not a reproduced current public leak.

## 3. Filters, scoping and authorization

Header-based views require explicit Company and BOQ Header, with Project available as a selector narrowing the header list. Server resolves header→project→company and refuses mismatch. Do not silently default to all headers on a missing/invalid selector. Price history requires Company and a bounded period; Item, Supplier, Region and Project may narrow it.

Check native read/report/export permissions, header-parent permissions, User Permissions and selected dimensions before the query; additionally restrict child rows/source records to what that caller can read. Header read alone does not necessarily authorize every Cost Analysis/resource row. Use permission-aware queries or reviewed allowed-record sets integrated into SQL; do not retrieve all private rows and filter them on the client. Company/query filters are not substitutes for document permissions.

New endpoints accept only an allowlisted report identifier, scalar filters and validated pagination/sort. No arbitrary SQL, dynamic module name, user identity, DocType or unrestricted field selection from the client. Unknown identifier/filter and incompatible scope is rejected. Denied source links/exports must fail server-side even if a button is hidden.

Reuse existing scalar financial semantics. If a helper needs company/permission/pagination parameters, extend it compatibly or apply a verified query adapter using its projections; keep calculations in one maintained service. Changing a report result contract requires corresponding tests and documentation, not duplicated financial formulas in JS.

## 4. Result and paging contract — proposed wrapper

| Field | Meaning |
|---|---|
| report / basis / rule_version | Allowlisted view, exact valuation/planning basis and recorded calculation rule where available |
| effective_filters | Authorized company/header/period plus selected narrowing fields |
| columns | Stable allowlisted typed fields with Arabic/English labels; monetary units explicit |
| rows | Bounded result page; identifiers/links only for readable documents |
| page / has_more / row_count | Page information; row_count labelled page count unless an authorized bounded total is actually computed |
| totals | Only valid compatible-unit totals; explicitly label page versus whole-result basis; no sum of alternate/superseded analysis versions |
| warnings / generated_at / snapshot identity | Missing/legacy/zero-basis caveats and reference for displayed/exported values |

Initial proposed bounds: 50 rows/page, maximum 200; export maximum 2,000 rows with rejection/narrow-filter guidance rather than silent truncation. Confirm against F14/F37. No existing report hard limit is claimed. Aggregate/paging design must constrain expensive database work as well as returned rows; fetch-all-then-slice is insufficient.

Rows/columns for current services are taken from their existing source aliases. Add explicit source metadata as needed for provenance and readable links; do not fabricate names absent from the result. Company currency comes from the header/project context but an analysis/history currency may differ. Mixed-currency totals must be refused/separated until a reviewed conversion policy exists.

## 5. Worked acceptance examples

| Scenario | Expected result |
|---|---|
| Cost item qty10, factor0.5, contract100, direct60 | Contract value500 / budget direct300 in separately labelled BOQ totals. Per-unit difference40; cost markup66.666…% using configured display precision, not40% gross margin |
| Sole approved analysis cancelled to captured manual60 | Item cost view shows manual basis60; no current approved analysis; missing-analysis view includes item; current approvals view omits cancelled analysis |
| A superseded by B | Default current view shows B only; submitted-history option can show A/B with statuses; no double counting of approved basis |
| Direct cost0 and contract100 | Unit difference100; percentage-on-cost undefined, not0% as a commercial assertion |
| Resource batch analysis qty10, resource qty20, rate5, wastage10%; BOQ qty10/factor0.5 | Resource demand11 units; total direct resource cost55; weighted rate5. Planning remains contract quantity even after a VO changes revised quantity |
| Cancelled price-history source | Active-history view excludes it; cancellations remain native ledger evidence rather than deleted history |
| Header companyA requested under companyB | Request denied/invalid, with no A data returned |

Use independent Finance/QS worksheets and the source's native monetary precision; do not demand equality beyond configured rounding or disguise a page subtotal as a header total.

## 6. Integrity view: strict existing boundary

`audit_boq_rollups(header)` requires the session to be **Administrator**, not merely System Manager, and returns:

- boq_header;
- header.stored, header.computed, header.mismatched_fields;
- structures[], each with name, stored, computed and mismatched_fields;
- aggregation_limit describing different header/structure inclusion semantics.

The view must be read-only, show stored/computed values side by side, explain aggregation_limit and link to technical reconciliation instructions. No “repair totals,” approval rewrite, factor normalization or SQL update action is included.

Preserve literal Administrator restriction for the initial technical view; ordinary role sessions receive refusal. Do not elevate a System Manager session to call it. The owner should test business views with ordinary roles, and engineering supplies the restricted audit evidence separately. If a non-Administrator integrity view is required, that is an explicit permission-design decision with a narrowly reviewed scope/field contract before extending the service. No approval is inferred here.

Audit discrepancies are investigation inputs, not proof that every mismatched value should be overwritten; the service deliberately mirrors current controller inclusion rules. Display missing/invalid legacy context rather than recalculating guessed commercial history.

## 7. Screen and export behavior

Use one validated filter state per request. When report/company/header changes, clear old rows/totals and show loading; ignore late responses for a previous request. Empty data is a real empty state; denied/failed queries never leave old totals labelled as new results. Show the source/basis/status labels where they affect interpretation.

Exports use the same server-side report identifier, authorization, normalized filters, basis and row bounds as display. They include filters, generation time, units/rule/basis and whether output is a page or full selected result. If displayed data changed before export, show a fresh timestamp/snapshot or ask the user to refresh rather than promise an unchanged snapshot unsupported by the service. Use private authorized download handling and bounds; do not save public files containing restricted business data.

Arabic/English labels and mixed-direction identifiers use established localization/narrative conventions. Links open permitted source forms; long descriptions must wrap without truncating critical rate/quantity figures. Keyboard and supported laptop widths must retain filter and export actions.

## 8. Acceptance additions through F43

| Design case | Required owner/engineering outcome |
|---|---|
| F19-U01 | Each of five views has an actual usable route and correct columns/filter states; no console assistance |
| F19-U02 | Allowed/denied company, header, child cost/resource and source-file/export routes; no client-only filtering |
| F19-U03 | Approved/history/Manual/Legacy Review/cancelled status semantics visible; no duplicate-basis aggregate |
| F19-U04 | Zero basis, fractional factor, wastage and batch quantities match independent worksheet |
| F19-U05 | Resource contract plan remains labelled contract basis after VO; no revised forecast implication |
| F19-U06 | Active price history includes company/currency/UOM/source and bounded period; excludes cancelled sources |
| F19-U07 | Limits/paging/export are explicit; totals use same authorized filters and supported units |
| F19-U08 | Rapid filter changes, empty results and denied/errors clear stale values and retain latest request only |
| F19-U09 | Arabic/English display and exports preserve values, units and readable identifiers |
| F19-U10 | Restricted audit: Administrator can view stored/computed mismatch and semantics; ordinary/System Manager callers cannot bypass literal guard; no mutation |
| F19-U11 | Missing analysis includes legitimate manual-cost items; current approval default/history option behave correctly |
| F19-U12 | Runtime route/assets/report definitions and source helper extensions match final candidate; meaningful regressions pass |

Design IDs are not executed tests or final global UI IDs. F43 integrates them with OS-05, actual roles and example fixtures; F11 adds HTTP/query/export denials and F14 verifies bounds. Do not use an admin audit session as ordinary-role acceptance proof.

## 9. Prerequisites and open contract issues

F19 closure depends on F03 installed inventory, F07 correct cost basis and F11 complete access boundaries; F02/F13/F14/F37 are required for safe runtime/bounds qualification. Source findings F19-SC01–05 are recorded in shared evidence: raw service authorization, summary history selection, history company/paging, Administrator-only audit and zero-cost markup display. They require narrow adapter/service corrections before exposing routes; no new financial engine is needed.

Confirm whether the intended Owner/PM/Finance grants permit each cost/resource field through the F11 matrix. Actual page/report identifiers and implementation details are engineering decisions; a wider audit audience or new conversion/business definition needs an explicit owner/domain decision. This design does not choose a delivery route or grant deployment authority.
