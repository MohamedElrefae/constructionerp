# Stage 1C — Independent AI-R Rerun

## Verification identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — independent final evidence re-verifier |
| Agent/model | OpenAI Codex, GPT-5 model family (no more-specific model identifier exposed to this session) |
| Canonical task/session | `/root/ai_r_rerun` |
| Verified at (UTC) | `2026-09-04T21:03:01Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; changes remain uncommitted |
| Authority | Verification and this new evidence record only. No code, payload, catalog, Git history, release, deployment, or production mutation was authorized or performed. Runtime diagnostics were read on the authorized test site. `assert_translation_health()` refreshed its diagnostic timestamp as part of its normal behavior; it did not alter translation values. |

This verifier is not the Builder/proposer and is not AI-A1, AI-A2, or AI-A3.

## Exact artifact hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4, `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Current Builder implementation record | `33470272c1dbaa2d74f9e8d77bc4337c4dd82bb6d8e59ea7bd638fb3187a2e05` |
| Original six-row proposal package | `ceaddc440e27656cdc66f5ec89515233e4d92c3f31c1a387dc76945ada1b68c1` |
| AI-A1 review | `788b5070beffd23fa9f21aceebb869a5cd40708128ef6b63c9c2533d9555972c` |
| AI-A2 review | `b596d2de87da68da4299759fb360cb3d2f91ff8e385d5f50bf66720d783f39d4` |
| AI-A3 review | `2e1d13e2c73276b5368c8d603723f4e69eb6a74f345d0bd2fbc151c606a5bbf7` |
| Prior AI-R verification | `8a17109a9e09a33954928d13d4c3b60d3f2b428b1dbacb95c14fd1ae3bc49dcf` |
| New runtime/render evidence | `2aac454ea5a5634416243d2c451a6bec6c742310bb7caa3f0d72cce1a4157b75` |
| Current released-overrides payload | `e460531ee00f8e85f18c5d8e6889db30e4d4ba346508b7ad2c5649443010b860` |
| Construction Arabic catalog | `e4678987ab3d11d632397de7dfc4a926681e862bdca6c09872e3f211ca85161e` |
| Construction hooks | `629c64a3773d0b82202b9342403200951f85bbc1a73941fd8913be6d64db1fec` |
| Frappe sidebar source | `2f5cf3dd5087ee21e8a170c9fb6588d420c3b280c39551777f1e51ad527c94c9` |
| Frappe menu renderer | `ef13144cd5a7cd2b617c67a1a6bc12ddc19d5f20e037dc953917b4c5bf45d043` |
| Tracked working-tree binary diff before this evidence record | `52b47e320075572da12aa421628afb2f1a15a3e1569f84118824447ed55800b6` |

Screenshot hashes and dimensions:

| Evidence | SHA-256 | Dimensions |
|---|---|---|
| `render-1c/header-menu-1366.png` | `6d8a0671f9e203a282d0026307cca1b6d40dbe9b02bd6daecf9bf0b9bdb15ef4` | 1366 × 768 |
| `render-1c/workspaces-entry-1366.png` | `48e5de312d88ff3f734a0a860e4b1cd5db7eb08d3e4de31fd1e08edcd0136236` | 1366 × 768 |
| `render-1c/display-submenu-1366.png` | `87b2359d4306c28df9202b3b48e77cc8096b32f1edca637313a02454b760eebb` | 1366 × 768 |
| `render-1c/header-menu-390.png` | `cf69e3d3bf90a7a76a60efeabd81bd00f2ccf49e6c080e5a20519a7ac612b7c2` | 390 × 844 |

Vendor repositories were clean for tracked files at verification time: Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`; ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5`.

## Dirty-worktree disclosure

The Construction worktree was intentionally dirty and consistent with the Builder disclosure:

- modified: `construction/data/translations/approved_ar_overrides.csv`, `construction/locale/ar.po`, `construction/patches.txt`, `construction/searchable_dropdown/api/search.py`, and `construction/searchable_dropdown/tests/test_search_api.py`;
- untracked: `construction/patches/v8_8/`, `construction/tests/test_bilingual_account_schema.py`, `docs/ai/work-items/`, and `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md`.

No `stage1c_sidebar_labels.js` file is tracked or untracked, and `construction/hooks.py` has no diff. No tracked Frappe or ERPNext source/catalog edit was present.

## Checks and findings

### 1. Governance and review provenance — PASS

The canonical-plan and handoff hashes still match. The immutable proposal package and the three independent AI review records cover the same six exact mappings. AI-A1, AI-A2, and AI-A3 recorded distinct roles/sessions, row-level decisions, rationale, confidence, and timestamps. The stale human-review wording in the original proposal package remains superseded by plan v4 and was already disclosed by the reviewers and prior AI-R.

### 2. `Workspaces` source-to-render call chain — PASS; prior blocker premise was wrong

The source object at `frappe/public/js/frappe/ui/sidebar/sidebar_header.js:18-26` does use raw `label: "Workspaces"`. That is a dictionary key, not the final DOM text:

1. `SidebarHeader.setup_app_switcher()` passes `this.dropdown_items` to `frappe.ui.create_menu()` at `sidebar_header.js:328-335`.
2. `frappe.ui.create_menu()` constructs `frappe.ui.menu` at `frappe/public/js/frappe/ui/menu.js:298-301`.
3. `frappe.ui.menu.make()` calls `add_menu_item(item)` for each visible item at `menu.js:44-63`.
4. `add_menu_item()` renders the title through `${__(item.label)}` at `menu.js:109`.

Therefore the governed runtime key `Workspaces` is applied to the actual visible menu item. The separate legacy `populate_dropdown_menu()` / `add_app_item()` path appends to `this.wrapper.find(".sidebar-header-menu")`, but the current template supplies no such element; the supplied live DOM evidence also records it absent. The screenshot at hash `48e5de31…` visibly shows `مساحات العمل` on the route where the sibling-workspace condition is true. No Construction extension or vendor edit is required.

### 3. Six-row payload and test-site runtime — PASS for values, provenance, and drift

The current CSV adds exactly six v1.0 Released rows with AI-A1/AI-A2/AI-A3 session provenance and the proposal-package hash. Five rows are owned by `frappe`; `Typography Settings` is owned by `construction`. The current dry-run result was:

```text
total 34; created 0; updated 0; skipped 34; drift 0; preview []; dry_run true
```

Read-only diagnostics on `v16.localhost` returned `verdict: translated` and the exact approved effective value for all six keys. Each has a canonical `origin: Packaged Release`, `release_status: Released`, and correct `ct_app`. Translation health reported loader installed, unique digest constraint present, no duplicate/null digest, no drift, and no orphan site overrides. The runtime/render record documents the earlier test-site-only import as six created, 28 skipped, zero drift. Nothing inspected indicates a production import.

### 4. Fresh Arabic session and render evidence — PASS with evidentiary limitation recorded

The runtime/render record identifies a fresh Chromium user/session, `htmlLang=ar`, `frappe.boot.lang=ar`, target `v16.localhost`, and route conditions. The four hash-matching screenshots visibly show the six Arabic labels across the header menu, conditional Workspaces entry, and Display submenu. The 390 × 844 screenshot visibly shows the Arabic sidebar label without clipping. The record also reports the direct DOM measurement `scrollWidth == clientWidth == 127px`, no viewport overflow, and no active ellipsis truncation. This closes AI-A3's narrow-width exception.

The screenshots themselves do not embed a machine-readable session identifier, DOM dump, or measurement log. The conclusion therefore relies on the hashed contemporaneous runtime/render record plus visual consistency, rather than an independently replayable browser trace.

### 5. Tests, lint, syntax, and build — PARTIAL EVIDENCE

The Builder reports passing groups of 13 + 6 + 5 + 3 + 8 tests and a clean build, but no raw test or build logs with commands, exit codes, environment, and hashes were added under this work item. Those claims cannot be independently reproduced from the evidence bundle without mutating the shared test database or regenerating build outputs, both prohibited for this review session.

This verifier independently ran `scripts/lint_translation_writes.py` (PASS), Python compilation for the changed/new Python modules (PASS), and `git diff --check` (PASS before this evidence file was added). These checks do not substitute for the missing durable test/build logs required by handoff §§2 and 9.

### 6. Payload metadata accuracy — CONDITION

The `Workspaces` row's current release note still says:

```text
visible instance needs Construction extension stage1c_sidebar_labels.js
```

That statement is now known to be false: the real `frappe.ui.menu` path translates the key, the draft extension was removed, and no such asset/hook remains. It does not change row identity, Arabic value, runtime behavior, quorum, or drift, so it does not reopen the resolved runtime blocker. It is nevertheless inaccurate governed release metadata and must not be carried into a release candidate as provenance truth.

### 7. Status-document consistency — CONDITION

The Builder record correctly says AI-R rerun is required and describes the resolved call chain. Its deviation row 7 still narrates the prior AI-R blocker without an explicit “superseded by rerun” disposition, and canonical plan §16 remains a pre-rerun progress snapshot. These are status-document synchronization issues, not code/runtime failures, but must be corrected after this decision without rewriting immutable prior review evidence.

## Decision

**CONDITIONALLY VERIFIED — the three prior Stage 1C runtime/render blockers are closed, but the exact release/evidence bundle is not yet final.**

The original AI-R blocker 1 was based on stopping at the raw label definition and failing to follow the actual `frappe.ui.menu` rendering call chain. The live runtime and screenshots support the corrected conclusion. All six translations are effective on the authorized test site with zero drift, and the narrow-width exception is closed.

The condition is evidence integrity, not translation behavior: the current released payload contains a known-false extension requirement, and durable raw logs for the claimed test groups and asset build are absent.

## Residual risks and precise next gate

1. Correct only the stale `Workspaces` release note so it records the verified `frappe.ui.menu` dictionary path and removal of the unnecessary draft extension. Do not change the source key, Arabic value, ownership, version, or AI reviewer decisions.
2. Save durable raw logs for the 13 + 6 + 5 + 3 + 8 targeted tests, translation-write lint, `git diff --check`, and Construction asset build, including exact commands, exit codes, site/environment, timestamps, and artifact hashes.
3. Update the mutable Builder/status records to cite this rerun and mark the prior `Workspaces` premise as superseded. Preserve the original proposal/reviews and prior AI-R as immutable historical evidence.
4. Re-run the governed import in dry-run mode after the metadata-only payload correction and prove zero create/update/drift. If the importer treats the note as runtime-significant, use the governed test-site path and record the exact result; do not mutate production.
5. Submit the corrected exact hashes and raw logs for a short final AI-R check. That check may issue `VERIFIED` for Stage 1C. Owner authorization remains separately required for commit, push, merge, deployment, or any production mutation.

Stages 2–8 must not claim Stage 1C final completion until this evidence-integrity condition is closed. Read-only/design work may continue, but no release or production action is authorized by this record.
