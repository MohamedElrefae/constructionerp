# Stage 2 — Independent AI-A3 Structural Review

## Review identity

| Field | Value |
|---|---|
| Role | AI-A3 — structural/localization QA reviewer |
| Agent/session | `/root/stage2_ai_a3` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed to this session) |
| Reviewed at (UTC) | 2026-09-04T21:21:36Z |
| Repository | `/home/mohamed/frappe-bench/apps/construction` |
| Branch / HEAD | `feature/erp-arabic-bilingual-data` / `e7be48855bde540464ea302e53c9bfca62b7c462` |
| Independence | Read-only review of Builder work. No code, catalog, runtime, Git, or existing evidence was modified. |

## Exact reviewed inputs

| Artifact | SHA-256 |
|---|---|
| `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| `docs/ai/work-items/erp-arabic-bilingual-data/BUILD_HANDOFF.md` | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| `docs/ai/work-items/erp-arabic-bilingual-data/IMPLEMENTATION.md` | `c0283cabfb961dd6f726296b0d6160269a271d958225f9038ec153abe7a790d4` |
| `docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-2-inventory.md` | `7f2f4e0a048f438f82f792ea652593eece19c0aaa417e848ed9a87302050b3e4` |
| `scripts/check_localization_gates.py` | `da40bc8b47fb5958d9b59a43d62004286f240cdb74e053337915a069f5c5b697` |
| `.github/workflows/linter.yml` | `adea11bd9f27b27fd9977a3c4a4f96a7313f034da61fe1fcf0013b3bc2b5c0d8` |
| `construction/locale/ar.po` | `e4678987ab3d11d632397de7dfc4a926681e862bdca6c09872e3f211ca85161e` |
| `construction/data/translations/approved_ar_overrides.csv` | `7ba7902c201e4010ffc30cad068490917b1cea1452faf859eb3020ff101badc0` |
| `construction/data/translations/qa-report.json` | `abd85f3eeef6ebd0d769a754f395949f037864234365e35eba326d0cc027bda2` |
| `construction/data/glossary/egyptian_construction_glossary.json` | `aefbbf633d432fb93ac63996960bb58d0bd005e973e0e461f4480d7ae46b51b4` |

The reviewer also inspected the Stage 0/1 durable evidence directory, current worktree status, the PO header and representative HTML entry, CSV schema, plan §§B1–B5/F2–F3/10.1, and handoff Stage 2. Direct execution of `python3 scripts/check_localization_gates.py` reported four files and zero errors; `python3 -m py_compile scripts/check_localization_gates.py` and `git diff --check` exited zero. Those green results establish only what the current implementation actually checks.

## Structural coverage assessment

| Required control | Result | Evidence / limitation |
|---|---|---|
| NUL and hidden bidi controls | **Partial pass** | PO source/target, populated payload rows, and raw JSON text are scanned for the enumerated controls. Empty CSV values are skipped entirely, malformed Unicode is not independently validated, and JSON is not structurally parsed. |
| Placeholder parity | **Partial pass** | Basic `{...}`, `%s/%d/%f`, and named `%(...)[sdf]` patterns are compared. The regex does not robustly model full Python/JS formatting syntax (for example positional/width/precision printf variants), and no adversarial tests demonstrate the intended grammar. |
| Whitespace/affix parity | **Pass for parsed singular values** | Leading/trailing whitespace is compared for non-empty PO and payload targets. It inherits the PO parser omissions below. |
| PO duplicates | **Partial pass** | Duplicate singular `msgid` values are rejected globally, but context is ignored; valid identical msgids in distinct `msgctxt` values would be treated as duplicates, while plural/context identity is not represented. |
| HTML/markup parity and safety | **Missing** | The script contains no tag/entity parser or comparison despite the plan and inventory claiming an HTML gate. The catalog currently contains HTML (`<span class='h4'><b>...`), so this is an active format, not a theoretical case. |
| Plural integrity | **Missing** | `msgid_plural` and indexed `msgstr[n]` are not parsed or checked. The Arabic PO declares six plural forms; the gate cannot validate completeness or placeholder/markup parity across them. |
| PO correctness | **Blocker** | The hand-written parser does not decode PO escapes, model `msgctxt`, fuzzy/obsolete entries, plural forms, or indexed translations. Unused `pending_id`/`pending_str` variables do not provide continuation-state handling. Use a proven PO parser or add a complete, adversarially tested parser before this can be a gate. |
| Released quorum | **Fail** | Released rows require A1/A2/A3 identities and A1/A3 timestamps, but `a2_approved_at` is omitted from the required-column loop. A Released row with no A2 approval timestamp therefore passes. There is also no timestamp validation, role/session validation, proposal-hash binding, or release-version validation. |
| Source-equal allowlist | **Fail** | The referenced `construction/data/translations/allowlisted_source_equal.txt` does not exist. PO source-equal values are always rejected with no allowlist support, while CSV allowlisting silently degrades to an empty set. The inventory's eight legitimate tokens and three A1-triage values are not represented in a checked artifact. |
| Extraction / hardcoded visible strings | **Missing** | No extraction comparison or source scan exists. A Python/JS/JSON/workspace/report/template change can add an unwrapped or untriaged visible string while this CI command remains green. |
| MO freshness / runtime provenance | **Missing** | There is no declared source-to-runtime hash, compilation artifact, or freshness check. Treating absent on-disk `.mo` files as N/A does not meet the canonical plan's separate freshness/runtime requirement; the chosen v16 runtime mechanism must have an equivalent declared-input hash check. |
| Vendor upgrade delta | **Missing** | The script explicitly checks only Construction-owned sources and has no old/new Frappe or ERPNext inventory, add/change/remove/context-shift delta, deferral register, or orphan-override check. Vendor changes can bypass triage. |
| Payload/live drift and duplicate identity | **Missing from this CI gate** | Existing service checks may cover these at runtime, but this Stage 2 CI workflow neither invokes them nor verifies a saved current result. |
| Changed-file routing | **Unsafe if used** | `--files` silently ignores unsupported relevant source files and exits zero even when it checks zero targets. Any `.csv` is incorrectly remapped to the one canonical payload rather than checking the supplied file. Deleted/renamed files and paths outside the narrow patterns are not handled. |
| CI invocation | **Partial** | Pull-request CI invokes full mode, so it does not currently suffer the `--files` zero-target omission for the four hard-coded artifacts. However, full mode still cannot detect source extraction or vendor deltas. The linter job is additionally disabled for `workflow_dispatch` by its job-level condition even though that event is declared. |
| Durable Stage 2 evidence | **Fail** | Only a narrative inventory is filed. There is no checked-in 15,172/current row-level inventory, reproducible inventory command/query, raw output, gate log, CI simulation, or hashes for the purported two-row vendor drift. Counts are internally unclear: per-app `Total` does not consistently equal `Empty + Populated`, and review-state totals sum to 17,848 while the stated app plus untagged populations sum to 17,850. Overlap/exclusions are not defined. |

## Findings and required fixes

### A3-01 — P0: The Stage 2 gate does not implement its mandatory structural scope

Add real HTML/entity parity, Arabic six-form plural validation, robust placeholder parsing, context-aware duplicate identity, and malformed-PO handling. Prefer a maintained PO parser available in the project toolchain; otherwise provide focused tests containing multiline escapes, `msgctxt`, `msgid_plural`, all `msgstr[n]`, fuzzy/obsolete entries, HTML attributes/entities, and representative Python/JS placeholders. CI must prove each defect fails and valid Arabic catalog structures pass.

### A3-02 — P0: New visible strings and vendor upgrade deltas can bypass CI

Implement deterministic extraction/source-diff checks for Construction-visible Python, JavaScript, JSON, workspace, report, print, email, and template strings, including unwrapped-string detection or a reviewed equivalent. Add a versioned old/new Frappe+ERPNext catalog delta artifact covering added, changed, removed, and context-shifted keys, with triage/defer status. CI must fail when either artifact is stale relative to its declared source commits.

### A3-03 — P0: MO/runtime freshness is absent

Define the v16 runtime artifact actually used. If `.mo` is intentionally absent, replace the file-age concept with an explicit source/release payload hash → compiled/boot/runtime dictionary hash contract and test it in CI or an authenticated integration gate. Record critical-key coverage separately. “No `.mo` on disk” is a deviation to solve, not grounds to drop freshness.

### A3-04 — P0: Released quorum validation is incomplete

Require and validate `a2_approved_at` in addition to every reviewer identity/timestamp, ensure timestamps parse and are temporally valid, bind approvals to the exact proposal/payload content hash, validate allowed review/release states, and test that omission or stale approval fails. Reuse the stabilization service's authoritative quorum validator where feasible rather than implementing a weaker CSV approximation.

### A3-05 — P1: Changed-file mode can return a false green

Reject unknown relevant paths, reject an empty target set when `--files` was supplied, check the actual supplied CSV instead of remapping every CSV to the approved payload, handle deletion/rename deliberately, and add routing tests. Either wire this corrected mode to CI using the PR base diff or remove the “changed-file-aware” claim; full mode should remain as a defense-in-depth run.

### A3-06 — P1: Source-equal decisions have no governed artifact

Create the referenced allowlist with exact key/context/app identity, rationale, owner/reviewer provenance, and expiry/review behavior. Route the three flagged natural-language values to AI-A1. Apply the same allowlist semantics to PO and payload checks. Missing allowlist must fail closed, not silently mean empty.

### A3-07 — P1: Inventory is not reproducible or internally reconciled

File a machine-readable row-level inventory or deterministic private-data-safe manifest, the command/query that generated it, exact app/catalog commits and hashes, category definitions (including overlap), and raw exit-coded output. Reconcile the two-row discrepancy and explain why per-app totals differ from `Empty + Populated`. Preserve the two vendor-drift rows as an exact delta, not only a prose count.

### A3-08 — P1: Add test and evidence coverage for the gate itself

Add unit/adversarial tests for every rule and durable `.txt` logs with command, UTC start/end, exit code, HEAD, and input hashes. Include both expected-pass fixtures and expected-fail mutations. A green run over the current happy-path artifacts is insufficient evidence that a CI gate fails closed.

## Decision

**BLOCKED — Stage 2 structural gate is not accepted.**

The current script is a useful initial scanner and its present-data run is green, but the mandatory Stage 2 acceptance statement (“new Construction visible strings and vendor upgrade deltas cannot bypass triage”) is not proven and is currently false. Linguistic waves may prepare proposals independently, but Stage 3 should not rely on Stage 2 as closed until A3-01 through A3-04 are fixed and independently rerun; A3-05 through A3-08 must be closed before Stage 2 receives final AI-R verification.

No opinion is issued here on Arabic linguistic quality or Egyptian accounting terminology; those belong to AI-A1 and AI-A2.
