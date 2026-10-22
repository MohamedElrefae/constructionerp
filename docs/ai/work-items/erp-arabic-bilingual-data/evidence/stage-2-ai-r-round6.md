# Stage 2 Round 6 — Independent AI-R Verification

## Identity, authority, and candidate

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 6 verifier |
| Agent/session | `/root/stage2_ai_r_round6` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-05T09:33:26Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only checks and isolated temporary fixtures plus this report. No code/catalog/payload/DB/runtime/Git-index/history changes were authorized. The advertised standalone suite unexpectedly rewrote two checkout artifacts; AI-R restored their timestamp-only changes to their exact pre-run hashes, disclosed below. |

The verifier read `AGENTS.md`, canonical plan v4, handoff, implementation record,
all Stage 2 remediation/review records through Round 5, the current checker/tests/CI,
vendor inventories/baseline/delta tool, decision and legacy records, freshness/site
policy, retired lifecycle, inventory manifest, catalogs/payload, and all ten Round 6
files under `evidence/raw-logs/stage2/`. Live repository and test-site results were
treated as authority. MCP recall was unavailable because its local Python environment
lacks `pydantic_core`; no cached memory was used as evidence.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `3ad30b072c50147f5565454aa4cee8b3169ba3048501b06e3612c68ba78cdfa8` |
| Stage 2 remediation record | `091ab37fcddf293cfe662ddd521d97e396159381203c1f328d0b093c1893df99` |
| Prior Round 5 AI-R | `046365c60d8b94bfcff74e8df36da1355c3e70b1c5aa827cd7350e39608a055d` |
| Checker | `311e1636607a7783cb289f4be71ed88fa18c9c6855653e84212dbb87e09faa4a` |
| Adversarial tests | `43869eaa290a3708a3fefe576305e77e4141fc5a81d5ad74d3b39fb0199b9e36` |
| Construction PO | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` |
| Released payload | `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Vendor baseline (restored/current) | `cc1968fa85704fdbd077f7d40ae21a2e14ef3ba0ef81e919e4f74ba4180fc5c9` |
| Frappe vendor inventory | `53335e7cfeb4433a6fa9c749ea12b0520d77c90b200bd69eac345e8d35924bcb` |
| ERPNext vendor inventory | `08177b71cc70ee6de9eec1deb4c4df7e9c587ad5bec1f4025d77ac24de514501` |
| Localization manifest (restored/current) | `9b43f3d43d39bce7a0abe540d8e597c05cbbc88f66a5837b75b77e43fe52dc2c` |
| Freshness evidence | `36823ec1b7434f9e20d16ba2b06a9776a7fc8927aadf4fb7d7d6a1fe99863a54` |
| Site classification | `0182069096821435f995338206b1030043413f14a69a01bd8609bb35e7a05b50` |
| Release decisions | `b1e0c46a0b56f8b585ef1ff6982f65f239024537a835243bf8e247b1e7ff8638` |
| Legacy decisions | `fbbc5182789813f808476c09600e091beb7c7cdca180d0569d67cb8f84665c64` |
| Retired lifecycle | `52fa8e40a7c8131fc54b01e68805232e37bdd1cc427a26e6080e30e734ba3fb6` |
| Inventory manifest | `8c652a7c87ba70e7acfa9a0c95cc3162b70c229d3970996a5616099c281349d3` |
| CI workflow | `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Vendor delta tool | `1a2fd009894afecb58db0437794e277c6fac5ca2dcf799cab078cbc33d61e2d5` |

## Independently reproduced positives

- Full gate exits `0` with exactly: catalog `771`; source files `247`; wrapped
  `631`; JSON labels `21`; missing `0`; raw-template `7/2/0`; CSV rows `34`.
- Vendor audit exits `0`; Frappe and ERPNext Arabic PO paths are Git-clean and
  match pinned commits.
- Test-site runtime dry-run independently returns `34` skipped, `0` created,
  `0` updated, and `0` drift. Payload hash is `037e79c2…`.
- The 61-test standalone suite reports `OK`; scope lint, translation-write lint,
  and `git diff --check` pass.
- Live inventory category totals reconcile to exactly `18,412` rows.

These positives do not establish the claimed fail-closed or hermetic controls.

## Round 6 closure matrix

| # | Required closure | Result | Independent assessment |
|---:|---|---|---|
| 1 | Inventory-bound vendor baseline rejects dirty/same-commit bytes, requires an exact reviewed delta/dispositions, and tests make zero checkout writes | **NOT CLOSED (P0)** | `test_baseline_refuses_without_delta` still calls `g.main(["check", "--update-baselines"])` against the real checkout. Running the advertised standalone suite printed `baselines recorded` and changed `vendor_catalog_baseline.json` and `localization_manifest.json` from pre-run hashes `cc1968fa…` / `9b43f3d4…` to `8235e59f…` / `5a3c9dce…`. AI-R restored only `recorded_utc` to `2026-09-05T09:27:33Z` and verified the exact original hashes. The alleged isolated same-commit test builds vendors under `<tmp>/apps/...` while the checker resolves siblings at `ROOT.parent/<app>`; moreover `live_msgid_inventory(..., root=ROOT)` and `vendor_commit(..., root=ROOT)` capture the original ROOT in default arguments, so monkey-patching `g.ROOT` does not isolate those calls. Its refusal is therefore for the wrong topology/reason. The update path also cannot consume the delta tool's own emitted list-of-object `added/removed/changed` schema because it compares it to list pairs, and it computes the expected `context_shift` from the reviewed artifact itself rather than the recomputed `shift`; exact transition governance is not proven. |
| 2 | AST sink analysis catches multiline calls and resolves aliases/attribute chains while leaving protected service internals untouched | **PARTIAL / NOT CLOSED** | The multiline Round 5 repro is caught, as are direct `frappe.throw`, direct `frappe.msgprint`, and assignment aliases such as `fail = frappe.throw`. Independent in-memory fixtures returned no finding for `import frappe as f; f.throw("...")`, `from frappe import throw as fail; fail("...")`, or `f = frappe; f.throw("...")`. The explicit alias/chain claim is false-negative. Current protected internals remain unchanged, but that does not close the scanner bypass. |
| 3 | Retired lifecycle strictly validates delete/rename/replacement/evidence/state transitions | **NOT CLOSED** | A safe temporary registry with `delete | construction/locale/ar.po | - | ...` was accepted even though the alleged retired old path still exists. Evidence pins are optional, and the same fixture was accepted with an unpinned evidence path. The current file itself says `pin optional`. Thus delete absence, mandatory evidence SHA/content binding, replacement semantics, and complete state transitions are not enforced. |
| 4 | Release/legacy decisions are immutable canonical row-identity/proposal/verdict/artifact-hash pinned and auto-invalidate | **PARTIAL / NOT CLOSED** | Row values, reviewer strings/timestamps, version, and referenced artifact hashes participate in the decision ID, so several edits invalidate. But `row_decision_id()` omits domain, references, notes, role verdicts, confidence, proposal identity/hash, and decision-record content. `release_decisions.json` objects are not validated back against their keys or a separately pinned decision root. `content:` binding remains source/translation substring presence plus file hash. The Round 5 requirement for canonical proposal/verdict semantics is not closed. |
| 5 | 61 adversarial tests cover prior repros and pass standalone + Bench hermetically | **NOT CLOSED (P0)** | The 61 standalone tests pass, but they are demonstrably non-hermetic because the suite rewrites the real baseline and manifest. The same-commit test does not exercise the intended isolated bench, the AST alias bypasses above are untested, and existing-old-path/unpinned-retirement cases are untested. AI-R did not rerun the Bench variant after observing the known checkout write; its saved green result cannot be called hermetic. |
| 6 | Positive scoped run, 96 aggregate, exact inventory/Merkle, ten complete envelopes, and exact live counts | **PARTIAL / NOT CLOSED** | Saved positive scoped and 96-test summaries exist, and live `771 / 631 + 21 / 0` counts are independently reproduced. Exactly ten files exist, but they are not ten complete envelopes: `freshness.json` is raw JSON with no command/start/finish/exit envelope, and `merkle.txt` contains a visibly truncated `INV6` payload rather than the full reproducible query/result. More importantly, an independent read-only query over the documented tuple `(source_text, context, ct_app, translated_text, ct_review_status)` produced exactly `18,412` rows but Merkle `781262686bf12e1a931e743105fa7084c2c41a1c165780cd890f10176eb14460`, not manifest `b4cda993be8c0b738d90f81ca01dd242e3fadf7a5ea71b315d52f663769c8ee4`. The manifest/log does not preserve the exact executable query/normalization needed to explain or reproduce the claimed root. |

## Additional freshness residuals

Round 5 required strict non-future evidence, a site-classification hash, current
CSV Released-count reconciliation, and complete health identity/timestamps.
The current checker still permits up to five future minutes, does not bind the
site-classification artifact hash into the manifest, does not compare
`packaged_rows` to the current Released CSV count, and does not enforce constraint
name or required health timestamp presence. Current evidence happens to be green,
but the policy is not fully fail-closed.

## Findings by severity

### P0

1. **The adversarial suite writes governed checkout artifacts.** This directly
   disproves the claimed isolated, zero-write, hermetic test guarantee.
2. **Vendor delta acceptance is internally inconsistent and context-shift evidence
   is trusted rather than recomputed.** The generated delta schema and consumer
   schema do not match, while the isolated test does not reach the intended path.

### P1

3. Import aliases, from-import aliases, and frappe-object alias chains bypass the
   AST sink checker.
4. Retired deletes can name existing files and can use unpinned evidence; full
   lifecycle/replacement governance is absent.
5. Decision IDs do not bind proposal/verdict/confidence/reference semantics or
   validate decision objects against their keys.
6. The claimed inventory Merkle is not reproducible from its documented scheme,
   and two of ten evidence artifacts are not complete envelopes.
7. Freshness enforcement retains the listed Round 5 fail-closed gaps.

## Decision

**BLOCKED — Stage 2 Round 6 is not independently verified.**

Round 6 reproduces the correct headline counts and keeps runtime/vendor catalogs
healthy, but four of the six requested closures are materially incomplete and the
test suite itself violates the asserted no-checkout-write guarantee. Stage 1C
remains valid. Stage 3 must not begin under the locked sequence.

## Exact next gate

1. Remove every live `--update-baselines` call from repository tests. Pass an
   explicit `root` through all vendor/baseline/inventory functions (no definition-
   time ROOT defaults), build the actual sibling layout in temporary fixtures,
   and assert exact refusal reason plus before/after hashes for the entire checkout.
2. Define one canonical vendor-delta JSON schema shared by producer and consumer;
   recompute and compare add/remove/change/**context_shift**, candidate PO SHA and
   inventory hashes, require a per-item disposition, and test both accepted exact
   and rejected forged/empty deltas without repository writes.
3. Extend AST resolution to import aliases, from-import sink aliases, assigned
   module aliases, and chained attributes; add each reproduced bypass as a failing
   adversarial fixture.
4. Require old-path absence for delete/rename retirement, mandatory `#sha256`
   evidence pins, explicit replacement/event semantics, order-independent chain
   validation, and end-to-end changed/deleted routing fixtures.
5. Version and validate canonical decision records covering proposal hash, each
   role verdict/confidence, references, exact row identity, artifact hashes, and a
   separately pinned decision-root hash; add mutation tests for every field.
6. Store an executable deterministic inventory command, reconcile its exact
   normalization to the live 18,412-row Merkle, and regenerate exactly ten true
   command/UTC/exit/hash envelopes. Close the residual freshness checks, then run
   the full 61/96 suites from a clean hash snapshot and request a fresh AI-R.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
