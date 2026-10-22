# Stage 2 Round 9 — Independent AI-R Verification

## Identity, authority, and candidate

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 9 verifier |
| Agent/session | `/root/stage2_ai_r_round9` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-05T10:18:20Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks and disposable temporary fixtures, plus this report. No code, catalog, payload, governed runtime value, Git index/history, or existing evidence was intentionally modified. The dry-run health path may refresh its audit timestamp, but it changed no translation value. |

This verifier was not the Builder or a prior reviewer. It read `AGENTS.md`, the
canonical v4 plan, handoff, implementation record, Stage 2 remediation narrative,
all AI-R reports through Round 8, current checker/tests/CI, vendor baseline and
inventory artifacts, delta producer/consumer, release-decision recorder/objects,
freshness/site policy, retired lifecycle registry, inventory serializer/SQL/
manifest, payload/catalogs, and the ten current Round 9 evidence files. Saved
reports were treated as claims; source and independently executed checks were
treated as authority.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `97c49622647d20e4835747bcadbd4053be4ed7b1e9e8b128d6866ecd33947267` |
| Stage 2 remediation | `3ba560b25ecd86ed138471faed34e89c9243a5d437d26205d078d11daf9fd29d` |
| Prior Round 8 AI-R | `80bbf2bf334a671b4f08b4a17b43780e9f136aa8932f8c90733d832007caa251` |
| Checker / adversarial tests | `35a7f6a5e05e638bc13249833545dbfe2b06ba3027fb02fd7a3dcc2a6d920328` / `3680b51be17297806d173af4ef2c2dce5ee79f730621179f999629fd5f7c0102` |
| Vendor delta tool / baseline | `a7e7fab8b540c867ff7d597ce5c61015aacf34257be555583677d7c589aed530` / `d369e2ed72d9f77d1ed41dda12b8158aa586bd4b5e98c7c22ed22e41db8947d9` |
| Frappe / ERPNext vendor inventories | `53335e7cfeb4433a6fa9c749ea12b0520d77c90b200bd69eac345e8d35924bcb` / `08177b71cc70ee6de9eec1deb4c4df7e9c587ad5bec1f4025d77ac24de514501` |
| Decision recorder / decision objects | `3ed778260103f21ef4675b4fea06dedd5bc782bdc143ae4a8cf1cfc52f6f43cb` / `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` |
| Freshness / site classification | `4ebc0247daddd7d696b7c6a50bbda49a1c25f712fa23fe6f81b9b470cf356b87` / `0182069096821435f995338206b1030043413f14a69a01bd8609bb35e7a05b50` |
| Localization / inventory manifests | `098d7bb5ac585ee46ed647f1e28bc3dd70b90559c33ad227ee6067332b6e9eef` / `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` |
| Inventory serializer / SQL | `117f9129b6b5a0b8591345aced2ba106d73a01e916ff8441ee46b965c0ec6ee1` / `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` |
| Construction PO / released payload | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Retired lifecycle registry | `cad850c823a169ff338b2b8e78cf17d20626d36efd0e27dbd38e214c2d162706` |

## Independently reproduced positives

- Full checker exits `0`: catalog `771`; `248` extracted source files; `631`
  wrapped literals plus `21` JSON labels; missing `0`; raw templates `7/2/0`;
  released payload rows `34`.
- Vendor audit and the requested positive scoped run exit `0`.
- All `68` adversarial tests pass standalone and under Bench. The other five
  requested modules independently pass `13 + 6 + 5 + 3 + 8`, giving `103` total.
- The payload dry-run independently returns `34` skipped, `0` created, `0`
  updated, and `0` drift. Payload SHA remains `037e79c2...`.
- Scope lint, translation-write lint, and `git diff --check` pass. Frappe and
  ERPNext Arabic PO files are Git-clean.
- The committed inventory manifest remains bound to `18,412` rows and Merkle
  `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`;
  its serializer/SQL artifacts are unchanged from the independently reproduced
  Round 8 closure.
- The permanent forged-provenance and omitted-context-shift fixtures refuse the
  supplied deltas and leave their disposable baselines unchanged.

## Round 9 closure matrix

| # | Claimed closure | Result | Independent assessment |
|---:|---|---|---|
| 1 | Every vendor read/hash/git/provenance path honors explicit isolated roots | **NOT CLOSED (P0)** | Core baseline reads, candidate PO hashes, inventories, and commits now use `root`. However, `audit_vendor_coverage(errors, root=...)` still reads `vendor_covered.txt` from module-global `ROOT`, not the isolated root. A disposable tree with no candidate allowlist nevertheless loaded the live checkout's 47 entries and produced 47 stale-entry errors, proving cross-root read leakage. `vendor_upgrade_delta.main()` also has no `--root` path: it invokes `blob()` without a root, hashes with `ROOT.parent`, and writes under `ROOT`. Thus the claim covering *every* vendor read/hash/git path is false even though the update-baseline P0 from Round 8 is fixed. |
| 2 | Independently recomputed canonical delta rejects forged sets/commits/hashes/contexts, same-commit dirt, direct overwrite | **CLOSED for the update consumer; producer boundary remains under #1** | `update_baselines` checks recorded-to-live commit and PO hashes before comparing canonical recomputed sets, refuses the permanent forged provenance/omission fixtures, requires dispositions, and writes only after validation. Same-commit dirty bytes differ from inventory and require a reviewed exact delta. The canonical set representation is shared for set construction. |
| 3 | Full AST alias chains | **CLOSED for claimed fixtures** | Direct/import aliases, assigned Frappe module chains, multiline sinks, wrapped calls, and the conservative wrapper-alias behavior remain covered and green. |
| 4 | Strict versioned retired lifecycle; replacement explicitly out of scope | **NOT CLOSED (high)** | The v3 marker and delete/rename rules are enforced, and the canonical Stage 2/F3 contract does not require a distinct `replacement` event; modelling an actual replacement as explicit governed events is an acceptable narrowing. But the file promises dates are “never future” while code accepts any date through `now + 1 day`. A disposable entry dated `2026-09-06` was accepted on `2026-09-05` with zero errors. The lifecycle is therefore not strict as claimed. |
| 5 | Decisions bind rows/proposals/verdicts/object root/manifest and invalidate | **CLOSED for current 34 rows** | Canonical row identity, proposal hash, role verdict fields, referenced artifact hashes, decision-object SHA/root, and manifest pins are validated. Mutation fixtures remain green. Residual operational risk: the recorder transcribes configured verdict metadata and must remain a separately reviewed operation. |
| 6 | Freshness enforces every prior axis | **PARTIAL** | Current artifacts pass input hashes, collection time, age, classified site, authorization false, runtime digest, released count, critical map, health booleans, constraint identity, three required audit timestamps, and decision/inventory bindings. Audit timestamps are checked only for presence/parseability—not for future time, age, ordering, or agreement with the separate top-level `audit_timestamps` map. Standalone tests emitted an unclosed-CSV `ResourceWarning`, and the “strict future” unit test tests datetime arithmetic rather than invoking `check_manifest` on a mutated disposable artifact. |
| 7 | Deterministic serializer/Merkle | **CLOSED** | The canonical serializer string-normalizes, full-tuple sorts, and JSON-serializes five-column rows. The governed result remains 18,412 / `973b8faccbc1...`, with manifest bindings intact. |
| 8 | Exactly ten complete, non-truncated hash envelopes | **NOT CLOSED (high)** | Exactly ten `.txt` files exist and each has command/start/end/exit. They are not complete content-hash envelopes: `all-tests`, `lints-diffcheck`, and several other files contain no artifact/result hash; there is no governed index binding all ten file SHA-256 values; `merkle.txt` still contains a visibly truncated `INV8` JSON line; and every displayed log repeats its entire block. External `sha256sum` values exist but are not recorded in a governed envelope. This is the same evidence-integrity condition identified in Round 8, not a closure. |

## Active adversarial evidence

1. **Cross-root audit read:** a disposable true-bench candidate contained only
   temporary vendor POs and no candidate `vendor_covered.txt`. Calling
   `audit_vendor_coverage(errors, root=temp_root)` did not fail for the missing
   candidate artifact. It silently consumed the live checkout's 47 governed
   entries and returned 47 `vendor-covered-stale` findings. This directly proves
   module-global leakage during an explicit-root operation.
2. **Future retirement acceptance:** a disposable v3 registry with correctly
   hash-pinned evidence and a delete event dated `2026-09-06` was accepted at
   `2026-09-05`, returning the retired path and no error. This contradicts the
   registry's “never future” policy.
3. **Checkout integrity:** vendor PO files remained clean and current governed
   artifact hashes matched the Round 9 values after standalone and Bench tests.

## Decision

**BLOCKED — Stage 2 Round 9 is not independently verified.**

Round 9 closes the prior update-baseline provenance bypass and preserves all
headline green counts/tests/runtime results. It does not close the broader
explicit-root boundary, strict retirement-date policy, or complete evidence
envelope requirement. The freshness implementation is also not as strict as the
claim. Stage 1C remains valid; Stage 3 must remain blocked under the locked
sequence.

## Exact next gate

1. Make `audit_vendor_coverage`, the vendor delta CLI/producer, and every helper
   resolve governed inputs, git repositories, hashes, temporary parse files, and
   outputs solely from the supplied root. Add permanent missing-candidate-file and
   cross-root-conflict fixtures that assert no live bytes are read or written.
2. Reject retired lifecycle dates strictly greater than the current UTC date; add
   an end-to-end tomorrow-date fixture. Keep replacement explicitly narrowed to
   governed delete/rename semantics unless the canonical plan is amended.
3. Apply age/future/consistency validation to all governed audit timestamps and
   exercise the actual manifest gate with disposable mutated artifacts. Close the
   CSV file handle to remove the `ResourceWarning`.
4. Regenerate exactly ten non-duplicated, non-truncated evidence files. Add a
   governed index that records each file's SHA-256 and the relevant input/output
   artifact hashes; include complete inventory JSON or bind it by full artifact
   hash without embedding a truncated fragment.
5. Rerun a fresh independent AI-R. Owner authorization remains separately required
   for commit, push, merge, deployment, or production mutation.
