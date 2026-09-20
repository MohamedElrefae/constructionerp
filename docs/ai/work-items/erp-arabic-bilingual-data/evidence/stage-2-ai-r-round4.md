# Stage 2 Round 4 — Independent AI-R Verification

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 4 verifier |
| Agent/session | `/root/stage2_ai_r_round4` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-04T22:33:22Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Vendor commits | Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`; ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5` |
| Independence | This agent was not the Builder or a prior reviewer. It did not edit implementation, catalogs, payload, vendor trees, Git index/history, or existing evidence. This report is its only repository write. |

The verifier read `AGENTS.md`, canonical plan v4, handoff, implementation record,
all Stage 2 remediation and AI-R evidence through Round 3, current checker/tests/CI,
source changes, vendor baseline/delta tooling, decision and legacy artifacts,
freshness policy/evidence, retired-source registry, inventory manifest, catalogs,
payload, and all nine Round 4 raw-log files. Live files and independently executed
checks were treated as authority.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `d661b50a7de3f48dda0ad6bff0ae0126b9c97b9653edaea7266efbe1e45b2140` |
| Round 4 remediation record | `9bf9d723abc703fe7f9e2e11b9e5be0e13fd82a12e1dadfd8c6a64634e857daa` |
| Round 3 AI-R | `7054789fd6c96ffeafb65deff642bb95e9118224b48ad80440802adc608d5b85` |
| Checker | `a48ea9ecd2d6815cbaae6036de8568ffc591690d9b04cbb8892d6384a8c98266` |
| Adversarial tests | `dd34710133efab255f417de4e79ff8acaf2cd1039cff5ef4faf97675f299e7ac` |
| Construction PO | `945dbbc0dd06011b7e80666ae320c29b3fa6dbe08861830e1aa3e5789e7604d1` |
| Released payload | `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Vendor baseline | `89b4178be4ba595d7a293c9d83df2e9adbdefa7f24f202d381a8da94007099d2` |
| Manifest | `b754c6233e4b7147eb45c3321a0a45cf676054fcb16f82f922981db3edab6556` |
| Freshness evidence | `ad1d7023b7251d2875c0aad730236ceba13e650fc3a38edd2846ec81f64f8d63` |
| Inventory manifest | `83ad12bd1d8b0c1919a7d9abc20dc8c09cf1e98a57801399930fe6ecfb8e872c` |
| Legacy decisions | `f9949b06b5d6338a9fcf10adee5c93c497845e511a796c82fb4b8e1f49c0e56e` |

## Independent execution

- Full checker exited 0 and reported: Construction PO identities `767`, payload
  rows `34`, source files `247`, wrapped literals `627`, JSON labels `21`, missing
  `0`; raw-template files `7`, raw texts `2`, missing `0`.
- The 51-test adversarial suite passed standalone and through Bench (`51 OK`).
- Vendor Arabic POs are Git-clean and vendor HEADs match the pinned commits.
- Test-site dry-run returned `total=34`, `created=0`, `updated=0`, `skipped=34`,
  `drift=0`. Health was green for loader, fallback, duplicates, null digests,
  unique constraint, drift, and orphan overrides. Running the health assertion
  refreshed only its audit timestamp; no translation/runtime value changed.
- The inventory records 18,408 Arabic rows and Merkle root
  `f10945e1620f9655d6676d27aa5b155fa86bec490524e3d4c4bf6d7b2b93322d`;
  its three PO hashes match the current catalogs.
- Safe negative fixture: with unchanged mocked vendor commits and changed PO
  hashes/counts, `update_baselines(["check", "--update-baselines"])` returned
  success (`None`) and replaced the baseline with the changed hashes without any
  `--delta-reviewed` artifact. This reproduces the same-commit bypass outside the
  repository in a temporary directory.

## Round 4 closure matrix

| # | Claimed closure | Result | Independent assessment |
|---:|---|---|---|
| 1 | Real Jinja/HTML visible-text gate; print templates wrapped; zero missing | **PARTIAL** | The new text-node scanner catches a simple raw `<p>Visible Label</p>` fixture and the current `construction/templates/**` set reports zero missing. However, scope is hard-coded to `construction/templates`; `construction/print_format/**.json` remains explicitly skipped as a markup/code blob. The claim that all print/template UI surfaces are governed is therefore broader than enforcement. Current checked templates are clean, but excluded embedded print/workspace markup can still bypass this gate. |
| 2 | Python sinks wrapped/governed; service internals not falsely translated | **PARTIAL** | Current direct single-line literal `frappe.throw/msgprint` calls pass and service diagnostics are dispositioned. The scanner is regex/line based and only recognizes a literal immediately inside the call; variable, concatenated, multiline, aliased/imported sinks are not governed. Dispositions contain duplicates and Builder-authored decisions without immutable evidence. This is useful linting, not the claimed complete user-visible sink gate. |
| 3 | `no-underscore-import` rule and actual regression fixed | **CLOSED for the observed defect** | The rule is active, its fixture detects a bare `_()` without `from frappe import _`, and the current full run is green. The cited stabilization import regression is no longer present. Residual: this is a narrow regex rule rather than Python AST/name-resolution analysis. |
| 4 | Recomputed, cryptographically bound vendor delta; same-commit/direct baseline bypass impossible | **NOT CLOSED** | `load_reviewed_delta()` validates only top-level `triage_status`, nonempty `disposition`, app/old/new on commit moves. It neither recomputes nor hashes the add/remove/change/context-shift set and requires no per-item dispositions. More decisively, `update_baselines()` asks for reviewed evidence only when `old_commit != current_commit`. The independent temporary fixture proved that changed PO content at the same commit is directly re-baselined without review. |
| 5 | Hash-pinned legacy migration plus automatic invalidation/content-row-proposal binding | **NOT CLOSED** | The legacy JSON pins the sign-off document hash, but its alleged “28-row roll” is only a list of source strings (no language/app/context/Arabic/proposal/verdict hashes); its own metadata says scope 23 while the list contains 28. `content:` references still check mutable-file existence plus independent source/translation substrings, with no artifact hash, row identity, proposal hash, reviewer verdict, or invalidation record. This does not meet cryptographic row/proposal binding. |
| 6 | Classified-site freshness, future rejection, full health policy | **CLOSED for current evidence** | Site classification is separately recorded as non-production test; site equality, a five-minute future bound, 30-day age, input hashes, critical policy equality, runtime digest/count, and all required health booleans are enforced and currently pass. Residual: the classification is Builder-recorded from an owner statement, not signed, but it is explicit and fail-closed in the checker. |
| 7 | Validated structured retired/renamed/deleted schema and evidence | **NOT CLOSED** | `retired_sources.txt` is empty. The parser accepts only five pipe fields and validates only nonempty fields plus evidence-file existence. It does not validate reviewer identity, date syntax/future date, evidence hash/content, disposition type, uniqueness, rename old/new linkage, or deleted-vs-renamed semantics. The 51 tests do not exercise an actual rename/deletion lifecycle. |
| 8 | 51 tests cover all prior modes; positive scoped run; aggregate/inventory/log durability | **NOT CLOSED** | Both 51-test runs and the positive scoped run are green, but Round 4 tests are mostly presence/shallow assertions: the baseline test never invokes `update_baselines`; legacy test checks only Python set membership; sink test only checks regex matching; site test checks current values; retired tests do not cover rename semantics. The reproduced baseline bypass is untested. The saved aggregate does report 86 tests, but the filename says `all-76-tests.txt`. Current checker counts are `767/627+21`, not the claimed `720/591+21`. Exactly nine files exist, but they are not nine complete envelopes: `freshness.json` has no command/start/end/exit envelope; `lints-diffcheck.txt` has no `EXIT_CODE`; `merkle.txt` contains a truncated `INV4` record and no manifest hash; most logs do not record the relevant artifact hashes. |

## Findings

### P0 — release blockers

1. **Same-commit vendor PO changes can still be blessed without reviewed delta
   evidence.** The bypass was independently reproduced. Reviewed delta contents
   also are not recomputed or cryptographically bound.
2. **Decision evidence is not row/proposal/verdict bound.** Legacy binding pins a
   document but not the released row values; current `content:` binding remains a
   mutable substring check.

### P1 — completeness/evidence blockers

3. Retired/renamed/deleted governance is not implemented beyond a weak empty-list
   schema.
4. Raw template and Python linting improves coverage but still excludes embedded
   print/workspace blobs and several real Python sink forms.
5. The 51 adversarial tests do not cover the critical bypasses; several new tests
   assert symbols/current state rather than fail-closed behavior.
6. The nine saved files are not nine complete evidence envelopes and documented
   counts (`591`, `720`) are stale against live results (`627`, `767`).

## Decision

**BLOCKED — Stage 2 Round 4 is not independently verified.**

Round 4 closes the current freshness policy and the observed missing-underscore
regression, and materially improves template/Python linting. It does not close the
vendor baseline bypass, immutable decision binding, retirement lifecycle, or
adversarial/evidence requirements. Stage 1C remains valid. Stage 3 must not begin.

## Exact next gate

1. Make every baseline content change (including unchanged commit) require a
   reviewed delta whose canonical add/remove/change/context-shift payload is
   recomputed, hashed, compared, and dispositioned per item before any write.
2. Replace substring/source-list decision checks with canonical row identities and
   hashes covering language, app, context, source, Arabic proposal, roles/verdicts,
   decision artifact hash, and invalidation behavior; reconcile the 23/28 legacy
   scope inconsistency.
3. Define and enforce a versioned retired-event schema for deletion and rename,
   including old/new paths, reviewer, parseable timestamp, disposition, evidence
   SHA, uniqueness, and end-to-end routing tests.
4. Expand source/sink tests to excluded embedded print/workspace markup and
   multiline/variable Python user-message paths, or record narrowly scoped,
   independently reviewed and hash-bound dispositions.
5. Add true negative tests for each bypass, regenerate the inventory from a saved
   reproducible command, reconcile live counts, and regenerate exactly nine (or a
   clearly enumerated number of) complete command/UTC/exit/artifact-hash envelopes.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
