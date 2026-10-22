# Stage 2 Round 8 — Independent AI-R Verification

## Identity, authority, and candidate

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 8 verifier |
| Agent/session | `/root/stage2_ai_r_round8` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-05T10:04:24Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks and disposable temporary fixtures, plus this report. No code, catalog, payload, runtime translation, governed DB row, Git index/history, or existing evidence was intentionally modified. |

The verifier read `AGENTS.md`, canonical plan v4, handoff, implementation record,
Stage 2 remediation and all AI-R reports through Round 7, current checker/tests/CI,
vendor baseline/inventories/delta tool, release-decision recorder and objects,
freshness/site policy, retirement registry, inventory serializer/SQL/manifest,
payload/catalogs, and exactly ten Round 8 raw-log files. Existing prose and saved
logs were treated as claims; current source and independently executed checks were
treated as authority.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `346bf115a31954597acee7380290b00e6a1fc69b5487f44e4a678eb8c0ba4281` |
| Stage 2 remediation record | `e60663cc2b14329af3ce73acb48ef4906a29cff5900dac5726d3b93481004cf2` |
| Prior Round 7 AI-R | `d705514173be02586e3d5c9715469141ad798497ba0a74277af2f880b00a8203` |
| Checker / adversarial tests | `84b5eb5a…` / `7625f53f…` |
| Vendor delta tool | `a6eddaf110874a1db603d30039d98365eb1bb869755dfd8d237ae7f792bb1efa` |
| Decision recorder / decision objects | `3ed77826…` / `7a6ac9a1…` |
| Vendor baseline | `09ff2e0a31c031941635eb03fa165948596d64a6fd992f9dc6de859271055094` |
| Frappe / ERPNext inventories | `53335e7c…` / `08177b71…` |
| Construction PO / released payload | `ef088f7a…` / `037e79c2…` |
| Freshness / site classification | `36823ec1…` / `01820690…` |
| Localization manifest | `c74f1b705d8e64252051d7344ea23f241fd1cf1f61c1ec055e70b9cb8ec5a9ae` |
| Inventory manifest / serializer / SQL | `08ffeb63…` / `117f9129…` / `a32e37ba…` |
| Frappe / ERPNext Arabic PO | `cc353e76…` / `2dfe0a5d…` |

## Independently reproduced positives

- Full gate exits `0`: Construction catalog `771`; extraction files `248`;
  wrapped literals `631`; JSON labels `21`; missing `0`; raw templates `7/2/0`;
  released CSV rows `34`.
- The requested positive scoped run and vendor coverage audit exit `0`.
- All `67` adversarial tests pass standalone and through Bench. The other five
  requested modules pass `13 + 6 + 5 + 3 + 8`; the independently executed total
  is therefore `102`.
- Scope lint, translation-write lint, and `git diff --check` pass. Vendor Frappe
  and ERPNext Arabic PO files remain Git-clean.
- The live dry-run independently returns `34` skipped, `0` created, `0` updated,
  and `0` drift. Payload SHA remains `037e79c2…`.
- Executing the committed five-column query and passing its DB-returned rows to
  `construction.localization_inventory.merkle_root` independently returns exactly
  `18,412` rows and
  `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`.
  The Round 7 inventory-integrity P0 is closed.
- The current consumer recomputes add/remove/change/context-shift sets and rejects
  the permanent forged-omission fixture. Current decision root hashes canonical
  decision objects, and the manifest pins both decision and inventory artifacts.

## Round 8 closure matrix

| # | Required closure | Result | Independent assessment |
|---:|---|---|---|
| 1 | Hermetic explicit roots, refusal reasons, byte-identical checkout | **NOT CLOSED (P0)** | Several functions accept `root`, but `check_vendor_baseline()` reads `p = ROOT / BASELINE`; `update_baselines()` reads/hashes `po = ROOT.parent / app / ...`; and `vendor_upgrade_delta.blob()` is hard-wired to its module `ROOT`. In a disposable true-bench tree, `update_baselines(root=temp_root)` parsed the temporary candidate but recorded the live checkout Frappe PO SHA. This crosses the declared root boundary. Existing test fixtures did not detect it. Governed checkout artifacts remained byte-identical during this review, but that does not establish isolation correctness. |
| 2 | Canonical delta independently recomputed from candidate bytes; forged omission, same-commit, dirty, direct overwrite refused | **NOT CLOSED (P0)** | Omitted context shifts are now rejected and set equality is recomputed. However, the consumer never validates the reviewed artifact's `old`, `new`, `old_po_sha`, or `new_po_sha`. A disposable correct-set context-shift artifact with deliberately bogus commits and PO hashes was accepted (`code=0`, no errors). Combined with the root leak, the temporary candidate SHA was `0eb29ac0…` while the new baseline recorded live-checkout SHA `cc353e76…`. Thus candidate-byte/provenance binding and direct-root isolation remain bypassable. |
| 3 | Full AST aliases/module chains | **CLOSED for claimed fixtures** | Direct imports, import aliases, `from frappe import throw/msgprint`, and assigned Frappe module chains are handled; wrapped calls are skipped and the documented wrapper-alias case is conservatively flagged rather than silently missed. |
| 4 | Strict versioned retired delete/rename/replacement lifecycle and pinned evidence | **PARTIAL** | Pinned evidence, old-path uniqueness, delete absence/`-`, rename absence/live-or-retired target, and two-pass ordering are enforced. The active schema still has only `delete|rename`, no schema-version field or explicit replacement/terminal transition, and dates up to one day in the future are accepted. The broader “strict versioned ... replacement lifecycle” claim is therefore not implemented. |
| 5 | Decision recorder binds canonical row/proposal/verdict, object/manifest/inventory roots; mutations invalidate | **CLOSED for current 34 rows** | `decision_root()` now hashes canonical decision objects; row identity/proposal/verdict/artifact fields are validated; the localization manifest pins decision SHA/root and inventory manifest SHA/Merkle. Current rows pass. Residual governance risk: the recorder transcribes hard-coded session verdicts and is itself a reviewed operation, so its execution still requires independent evidence review. |
| 6 | Strict freshness on every listed axis | **PARTIAL** | Current evidence passes strict non-future collection time, 30-day age, classified non-production site, authorization false, source hashes, digest/criticals/released count, required booleans, constraint identity, decision/inventory bindings, and drift timestamp. The checker does not require `last_catalog_sync_at` or `last_release_import_at`, despite the claimed “all ... timestamps” contract. The adversarial future test only compares two Python datetimes; it does not mutate a temporary freshness artifact and invoke the actual gate. |
| 7 | Deterministic SQL/serializer gives 18,412 and `973b8faccbc1…` | **CLOSED** | Independently reproduced exactly. Minor documentation defect: `stage2_inventory.sql` still says `sha256(repr(rows))`, while the actual governed serializer correctly uses JSON over sorted string-normalized tuples. |
| 8 | Exactly ten complete hash envelopes | **NOT CLOSED** | Exactly ten `.txt` files exist and each records command/start/end/exit. They are not ten complete content/result-hash envelopes: `all-tests`, standalone tests, lints, scoped gate, sync, and vendor audit do not bind their relevant input/result artifacts; `merkle.txt` truncates the `INV8` JSON mid-record. External `sha256sum` can hash each file, but those hashes are not recorded in a governed envelope/index. |

## Active negative-fixture result

The disposable fixture used `tmp/bench/apps/{construction,frappe,erpnext}` and
never addressed a checkout write target. It created a committed temporary vendor
inventory, changed Frappe `A` from context `old` to `new`, and supplied the exact
recomputed add/remove/context-shift sets and dispositions while deliberately setting
both commit identifiers to `BOGUS` and PO hashes to all-zero/all-one values.
`update_baselines(..., root=temp_root)` returned `0` with no errors. The candidate
SHA was `0eb29ac0a2ce26dba44d13176e4d09a6d5eaaaf8efec8189301580a07f26007f`,
but the temporary baseline recorded the live checkout SHA
`cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502`.
This independently proves both provenance acceptance and root leakage.

## Decision

**BLOCKED — Stage 2 Round 8 is not independently verified.**

Round 8 closes the deterministic inventory P0 and the omitted-context-shift defect,
and the live gates, counts, tests, runtime dry-run, decision-object binding, lints,
and vendor cleanliness are green. It does not close the vendor root/provenance
boundary: reviewed metadata may be falsified and the update path may combine a
temporary candidate inventory with the live vendor PO hash. Stage 1C remains valid;
Stage 3 must not begin under the locked sequence.

## Exact next gate

1. Thread one explicit `root` through every vendor path, including baseline reads,
   candidate PO reads/hashes, `vendor_upgrade_delta.blob`, audit/update writes, and
   imported helper resolution. Remove all `ROOT` uses from explicit-root operations.
2. Define one versioned reviewed-delta schema and validate app, old/new commits,
   full old/new PO SHA-256 values, canonical recomputed sets, dispositions, and the
   reviewed artifact hash. Reject absent, extra, malformed, duplicate, or mismatched
   values before any write.
3. Add the exact successful negative fixture above as a permanent hermetic test.
   Assert temp baseline SHA equals the temp candidate bytes, bogus provenance fails,
   the precise refusal reason is returned, and all checkout governed hashes remain
   byte-identical.
4. Make the retired schema genuinely versioned and either model explicit replacement/
   terminal transitions or narrow the contract. Reject every future retirement date.
5. Require all governed health timestamps claimed by policy and replace shallow
   timestamp assertions with end-to-end temporary-artifact gate tests.
6. Regenerate exactly ten evidence logs with complete untruncated results and create
   a governed index/envelope that binds each file SHA-256 plus the relevant command,
   inputs, outputs, start/end, and exit status. Correct the stale `repr(rows)` SQL
   comment. Then rerun AI-R.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
