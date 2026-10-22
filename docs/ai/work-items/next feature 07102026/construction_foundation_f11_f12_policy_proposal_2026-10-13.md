# F11/F12 — Access policy proposal and remaining qualification

Date: 2026-10-13. Local candidate: `1e464889465554a62ee87074bd7bdf9ac7ab2204`, with uncommitted authorization/file changes. Status: recommendations awaiting Mohamed's workflow/access-policy answers; no grants or site mutations performed by this review.

References: [matrix evidence](construction_foundation_f11_matrix_evidence_2026-10-13.md), [F19 design](construction_foundation_f19_service_contract_design_2026-10-12.md), [work register](construction_foundation_work_register_2026-10-12.md).

## Proposed decisions

| Finding | Recommendation | Implementation boundary and required evidence |
| --- | --- | --- |
| F11-D002 | With enforcement ON, selected scope constrains direct reads as well as lists; no active scope denies ordinary construction-data access | Native permissions and User Permissions remain required independently. Apply one reviewed server predicate consistently to direct documents, children, custom APIs, attachments, queries and exports. Test valid/missing/changed scope, company/project mismatches, and explicitly documented administrative exceptions. Existing source describes selected scope as a list filter, so this is a proposed policy change, not an already established invariant or implemented fix |
| F11-D003 | Site Engineers record unapproved measurement stages; PM/Owner retain certification authority | Confirm with Mohamed before changing the gate. Do not copy the VO parent-read exception to every stage mutation: review create/edit/delete/submit/cancel separately, relationship validation, aggregate effects, planned-versus-measured fields, certification transitions and certified-record immutability. Existing certification guard must remain. Broader planning/correction privileges are not implied |
| F12-D001 | Keep ERPNext accounting reports finance-only; authorize F19 construction views separately by source data and field rights | Use an ordinary finance test account with deliberately assigned native report roles and scoped Company read. Do not grant finance roles to all construction roles or extend a blanket bypass. Record disposition and ON/OFF behavior for all 15 protected reports. If PM/Owner need particular accounting reports, obtain an explicit per-report requirement before granting access |

F19's five proposed views expose cost-analysis summary, item cost versus contract, resource requirements, active price history and missing analyses. They are not ERPNext accounting ledgers. Finance-only ledger access therefore does not by itself remove the PM/Owner construction views; those views still require verified native read/report/export permissions and authorized child/source fields. Administrator-only integrity audit remains unchanged.

## File-fix verification still required before closure

The submitted matrix reports a real leak, a fix and 13 successful checks; this review inspected source but did not independently repeat those HTTP checks. Keep F11-D001 Fixed awaiting full qualification and owner UI retest, rather than treating it as closed.

- Exercise direct `/private/files/` serving as allowed, forbidden and guest users, in addition to both download methods and File document reads.
- Verify each migrated public URL no longer serves bytes, including URL aliases/shared File references. Retain before/after migration evidence and recovery instructions.
- Verify an unauthorized user cannot detach, reattach or change a protected File's storage/privacy fields to evade the parent guard. Test both stored and requested attachment identities.
- Recheck approval-PDF access after scope policy is applied: the file hook delegates to parent read, so any parent direct-read gap propagates to files.
- Retain non-BOQ upload/download regression coverage and explain remaining unprotected attachment categories rather than implying a site-wide file-security fix.

## Next execution

Keep F11/F12 In progress. Resolve the access-policy answers, implement the bounded corrections with meaningful regressions, rerun the complete matrix, and attach candidate-bound evidence. Do not replace denied cases with privileged accounts merely to obtain a green matrix. Independent F14 bounds work can proceed while policy answers are pending; final owner UI testing remains the consolidated block after F43.

## Review evidence

Read matrix evidence, F19 design §§1–3/6/9, master plan F11/F12, G08 release-gap policy, and current BOQ parent/file permission/download source. Local schema check passed (21 owners + 1 override); context check passed (11/0). No suite, site, migration, commit or push executed by this review. Unrelated working-tree modifications preserved.
