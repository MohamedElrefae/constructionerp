# Stage 2 Round 3 — Independent AI-R Verification

## Verification identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 3 verifier |
| Agent/session | `/root/stage2_ai_r_round3` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-04T22:11:45Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; changes remain uncommitted |
| Vendor commits | Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`; ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5` |
| Independence | This agent was not the Builder or an earlier reviewer. It did not modify implementation, catalogs, payload, database/runtime values, Git index/history, or existing evidence. This report is its only write. |

`AGENTS.md`, the canonical plan v4, handoff, implementation record, all Stage 2
review/remediation evidence, the Round 2 AI-R report, checker, tests, CI workflow,
vendor delta/baseline, freshness collector/manifest, decision references, retired
paths, inventory manifest, payload/catalogs, and Round 3 logs were reviewed. Live
repository/site evidence was treated as authority.

## Exact reviewed artifacts

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `7cec07f999f42ce9f632aa1a61114c7c49dd76e8eff83a58d47993e70fb053be` |
| Stage 2 remediation record | `b22cb8d90362740d5950b6a06e1a5ffa454c8cd7fe60ca85b76b1963af23fb60` |
| Prior Round 2 AI-R report | `1593f0efcf317455284868cb95539ec7b41c145dde67cd09332299851e2712dc` |
| Localization checker | `0b506e84e360ddd90e2f86339946ae753ec1fdd1717e325a06572d85f3074575` |
| Adversarial tests | `e67d7e26daa69aa2e39fb1a08d05199385218962cc8ce7f6448108682d2616e4` |
| CI workflow | `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |
| Vendor delta tool | `1a2fd009894afecb58db0437794e277c6fac5ca2dcf799cab078cbc33d61e2d5` |
| Freshness collector | `3c35a5301d1d8506c943416b7c6919389930ec948e7acf80fa94622b9beac0d4` |
| Construction PO | `3e9f7077b9b5155057b596b37f3d44559f3b8bd90ca58b9dcb5bb6fca7c3eeaf` |
| Released payload | `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Vendor baseline | `2089d2a4900f1d11167bf96a7a8447714db420e9df0cc54d1ae4f1bd45271602` |
| Localization manifest v2 | `4550e3f6ffd87324d8800431825eb4978c193da72ae8c40cd201cb3dac68e42b` |
| Freshness evidence | `15e3a63a421d42a3457183dc70b1aadf1868da9017fad5ad28d60d15947844be` |
| Stage 2 inventory manifest | `38196d6f4c6f06a39b097d38b20e5dd1d88a61ef1f979f57b2fb2af4971d21e9` |
| Stage 2 inventory narrative | `cb46a12c5c84223558380804713096b1a5fe8b1020c8346ca1bbd839da856b6d` |

Round 3 log hashes: full gate `dc9c6635...`, gate tests `ad40ecf8...`,
scoped gate `ce89e87e...`, vendor audit `c8d022d8...`, final dry-run
`365a1039...`, inventory query `16f3890f...`, and Merkle `92ed712b...`.

## Independent execution

- Full checker: exit `0`; 720 Construction PO identities; 34 payload rows;
  247 scanned files; `wrapped=591`, `json_labels=21`, `missing=0`.
- Standalone adversarial suite: 40 tests, `OK`; Bench suite: 40 tests, `OK`.
- Remaining regression modules independently passed: searchable search 13,
  searchable integration 6, bilingual Account schema 5, translation catalog 3,
  stabilization gates 8. Together with the 40 checker tests this is 75 passing
  tests.
- Translation-write lint and scope-metadata lint passed. `git diff --check`
  passed.
- Independent test-site dry-run: `total=34`, `created=0`, `updated=0`,
  `skipped=34`, `drift=0`, `dry_run=true`.
- Frappe and ERPNext Arabic PO paths are clean. Vendor HEADs match the pinned
  commits above.
- Inventory manifest records 18,361 rows and Merkle root
  `8d3701f7d0531f119c6047fa449081640d643abc7e2d7e7146eac5d1c9fc760f`;
  its PO hashes match the current three catalogs.

## Eight-item closure matrix

| # | Round 2 requirement | Result | Independent assessment |
|---:|---|---|---|
| 1 | Remove suffix overwrite and reconcile full/scoped routing at `591 + 21` | **CLOSED** | There is one `SOURCE_SUFFIXES` definition containing Python, JS, HTML, and Vue. Full output separately reports 591 wrapped literals and 21 JSON labels. Scoped HTML and workspace JSON are routed. |
| 2 | Prevent template/JSON/workspace/report/print/email and raw Python/JS/template sinks from bypassing | **NOT CLOSED** | Routing a suffix is not equivalent to inspecting visible raw text. `check_extraction()` extracts only `_()/__()` calls and applies a narrow JS call-sink regex; it has no raw Jinja/HTML/Vue text detector and no Python `frappe.throw/msgprint` sink detector. Existing raw visible strings prove the bypass: `generic_export_list_pdf.html` contains `List View Export` and `Total Records`, `pdf_footer.html` contains `Page ... of ...`, and `boq_header_print.html` contains `Construction ERP - BOQ Management System`. Independent scoped checks of the first two files returned exit 0 with `wrapped=0`, `missing=0`. JSON markup/code blobs are explicitly skipped, including print/workspace artifacts, rather than governed. |
| 3 | Govern add/change/remove/context shifts and require mandatory reviewed dispositions before baseline updates | **NOT CLOSED** | `classify_delta()` now reports context shifts. However, a reviewed delta is accepted using only top-level `triage_status=reviewed`, any nonempty `disposition`, app, old and new commits. It is not hashed, does not require per-item dispositions, and its actual add/remove/change/context-shift content is not recomputed or compared during baseline update. More importantly, when vendor commit is unchanged, `--update-baselines` can overwrite altered PO hashes/counts without any delta at all. Direct overwrite bypass therefore remains. |
| 4 | Bind authenticated freshness hash, runtime digest/count/critical values, site classification and age; fail on tamper/staleness | **PARTIAL** | The manifest binds the freshness file hash, digest, packaged count, exact six mappings, and site string; input hashes and 30-day upper age are checked. But the site has no governed environment classification, the checker accepts whatever site/critical values are copied into a newly generated manifest, future-dated evidence is not rejected, and health validation checks only `has_drift`, not loader/constraint/duplicate/null/fallback invariants. This does not fully implement the claimed authenticated, policy-bound fail-closed contract. |
| 5 | Content/proposal/artifact-hash-bound `decision_ref` with automatic invalidation | **NOT CLOSED** | `content:` checks only that source and Arabic appear somewhere as independent substrings in an existing mutable file. No artifact SHA, row identity/context/app/domain, proposal hash, role-specific verdict, or decision identifier is bound. A decision artifact can change while still containing both substrings and continue to pass. Twenty-eight historical rows use the explicitly weaker `legacy:` existence-only scheme. The 40-test `test_decision_content_binding` only runs the current CSV; it performs no mutation/invalidation adversary. |
| 6 | Structured governed retired/deleted/renamed paths | **PARTIAL** | Five pipe-delimited fields and evidence existence are enforced for absent paths. Reviewer/date contents, evidence hash, disposition decision, rename source/target linkage, uniqueness, and expiry are not validated. `test_retired_valid_entry_accepted` does not call `load_retired()` or `classify_files()` at all; it merely asserts that its temporary evidence file exists. |
| 7 | Forty adversarial tests genuinely cover the claimed gates and pass standalone + Bench | **NOT CLOSED** | All 40 tests pass both ways, but they do not test raw template/Python sinks, JSON excluded blobs, same-commit vendor baseline overwrite, forged/stale delta contents, per-delta dispositions, freshness tamper values/site classification/future date/required health flags, decision artifact hash or mutation invalidation, or a valid retired-path load/rename flow. Several Round 3 tests assert field presence/routing rather than fail-closed behavior. |
| 8 | Regenerated inventory consistency and complete command/UTC/exit/hash evidence envelopes | **NOT CLOSED** | The structured inventory is internally consistent and has the claimed Merkle root. Evidence durability is not complete: `inventory-query.txt` has no command/start/end/exit/hash envelope; `merkle.txt` contains a truncated JSON line rather than the full query/result or manifest hash; `scoped-gate.txt` is an intentional failing run (`docs/random.csv`, exit 1), not positive proof that the valid HTML/JSON scoped set passes. The Stage 2 directory also has no durable Round 3 75-test aggregate or two-lint/diff-check logs. |

## Findings by severity

### P0 — release blockers

1. **Raw visible UI strings still bypass the extraction gate.** This is directly
   reproduced on existing templates: scoped checks return green with zero wrapped
   literals despite obvious English output text. Python raw sinks and skipped JSON
   markup/print content have the same governance gap.
2. **Decision evidence is not immutable or row-bound.** Substring presence is not
   artifact-hash/proposal/decision binding and does not guarantee automatic
   invalidation after evidence edits.
3. **Vendor baseline replacement is not fail-closed.** Same-commit catalog changes
   can be blessed without a delta, and moved-commit delta contents/dispositions are
   trusted rather than recomputed and bound.

### P1 — contract and evidence blockers

4. Freshness binding is improved but lacks site classification, future-date
   rejection, a separately governed expected critical mapping, and all mandatory
   health invariants.
5. Structured retired paths remain weakly validated and renamed-path governance is
   not implemented or tested.
6. The 40 tests pass but do not adversarially cover the above guarantees.
7. Round 3 evidence envelopes are incomplete; the only saved scoped run fails by
   design and the inventory/Merkle records are not fully durable/reproducible.

### P2 — residual observations

8. The current local/runtime facts are healthy: 75 tests pass, both lints and diff
   check pass, the payload is runtime-inert at 34 skipped/0 drift, the inventory
   hashes reconcile, and vendor POs are clean. These positives do not exercise the
   missing fail-closed paths.

## Decision

**BLOCKED — Stage 2 Round 3 is not verified.**

Round 3 closes the suffix overwrite and count reconciliation, and materially
improves the manifest and structured artifacts. It does not close five of the
eight required controls. Stage 1C remains valid. Stage 3 must not begin under the
locked sequence.

## Exact next gate

1. Add and adversarially test real visible-text/sink extraction for Jinja/HTML/Vue,
   Python and JS; govern or explicitly disposition JSON markup/code blobs. Existing
   raw template literals must be cataloged/wrapped or reviewed as language-neutral.
2. Generate a cryptographic row-decision identity from language/app/context/source/
   proposed Arabic/role/verdict and bind each `content:` reference to an immutable
   artifact SHA. Remove or formally migrate the existence-only legacy exception.
3. Recompute the vendor delta during baseline update, hash the reviewed artifact,
   require disposition for every add/remove/change/context-shift, and require a
   reviewed delta for any catalog hash change even when the commit is unchanged.
4. Bind freshness to a governed test/non-production site classification, reject
   future timestamps, validate all required health flags, and validate critical
   mappings against a policy source independent of the generated freshness file.
5. Validate retired reviewer/date/evidence hash and rename old/new linkage; add
   true positive and negative end-to-end routing tests.
6. Add adversarial tests for every item above and regenerate durable positive
   full/scoped/vendor/dry-run/inventory/Merkle/75-test/lint/diff logs, each with
   command, UTC start/end, exit code, and relevant artifact hashes.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
