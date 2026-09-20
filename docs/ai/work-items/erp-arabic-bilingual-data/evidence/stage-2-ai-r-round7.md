# Stage 2 Round 7 — Independent AI-R Verification

## Identity, authority, and candidate

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 7 verifier |
| Agent/session | `/root/stage2_ai_r_round7` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-05T09:50:30Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks and disposable temporary fixtures, plus this report. No code, catalog, payload, runtime translation, DB row, Git index/history, or existing evidence was modified. |

The verifier read `AGENTS.md`, canonical plan v4, handoff, implementation record,
all Stage 2 review evidence through Round 6, the current checker/tests/CI and
localization sources, vendor baseline/inventories/delta tooling, release decision
recorder and records, freshness/site policy, retirement lifecycle, inventory
manifest and committed SQL, payload/catalogs, and exactly ten Round 7 log files.
Live source and independently executed checks were treated as authority.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `bbafb6bfe9ce6c6ec8e0692df734350d57e5b7e45f472f687684bf3844ca5487` |
| Stage 2 remediation record | `1db9829e0a092420c457d1705f370c4715871f910f6752bfe9ce83fc0c8c3a47` |
| Prior Round 6 AI-R | `5715bfcfc1fc40aace2130ca2938a154b2fed081b1d1853a37b5d3b6242022b5` |
| Checker | `0230d79b3dcc25341cca96ca2f82f65c6a2654f6b4a3224e51c8001d4c6969aa` |
| Adversarial tests | `c93ee2d91264c5999d6e0da285182439b57ce65238c8ec03707564033507edb4` |
| Vendor delta tool | `a6eddaf110874a1db603d30039d98365eb1bb869755dfd8d237ae7f792bb1efa` |
| Decision recorder | `3ed778260103f21ef4675b4fea06dedd5bc782bdc143ae4a8cf1cfc52f6f43cb` |
| Construction PO | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` |
| Released payload | `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Vendor baseline | `cea31e52cd99005fcca0f76958636935aaf18d237dd99a22632ebeea07e49f85` |
| Localization manifest | `c2506537530e3b1dc47e8031946b21ee1a825a8b48e145e222851129ada220d8` |
| Frappe / ERPNext inventories | `53335e7c…` / `08177b71…` |
| Release decisions | `7a6ac9a10d49f618e630e21b6e8d4862e7ee7fd20f9c773dc77b9a5bdff3afb4` |
| Retired lifecycle | `66a91ed88f9329bf05eda31d3e00c721b9cd4b975cf1b8ad2d5c6bfd341c1f18` |
| Freshness / site classification | `36823ec1…` / `01820690…` |
| Inventory manifest / committed SQL | `4d295e7f…` / `a32e37ba…` |
| CI workflow | `dea0a37bee95a052677efa57767d4245fa7f1a007fa102cfb38d33decedfea2a` |

## Independently reproduced positives

- Full gate exits `0`: catalog `771`; source files `247`; wrapped `631`; JSON
  labels `21`; missing `0`; raw templates `7/2/0`; CSV rows `34`.
- Positive scoped run and vendor coverage audit exit `0`.
- The 63-test adversarial suite passes standalone and through Bench.
- Scope lint, translation-write lint, and `git diff --check` pass.
- Saved aggregate evidence reports `98` passing tests
  (`13+6+5+3+8+63`), and saved dry-run evidence reports `34` skipped with
  `0` create/update/drift.
- Frappe and ERPNext Arabic PO paths remain Git-clean.
- AST fixtures independently confirm detection of `import frappe as f`,
  `from frappe import throw as fail`, and two-level assigned module aliases.
- The standalone and Bench adversarial runs made zero checkout changes: the
  baseline, manifest, both inventories, decisions, retirement registry,
  inventory manifest, SQL, and the full pre-existing diff hash remained exactly
  byte-identical before/after. This closes the checkout-write defect itself.

## Round 7 closure matrix

| # | Required closure | Result | Independent assessment |
|---:|---|---|---|
| 1 | Hermetic suite, true bench topology, exact refusal reasons, zero checkout writes | **PARTIAL** | Zero checkout writes is independently proven. The fixture uses the true sibling layout and the refusal is present in returned errors. However, `update_baselines()` still has no explicit `root` parameter and relies on mutating module-global `ROOT`; the broader claim that all baseline functions use explicit roots is inaccurate. |
| 2 | One canonical producer/consumer delta schema; independently recomputed add/remove/change/context shifts; same-commit changes cannot bypass review | **NOT CLOSED (P0)** | The producer calls `canonical_delta_sets`, but the consumer constructs its own schema. Critically, the consumer's `want["context_shift"]` is copied from `reviewed.get("context_shift")`, not from the independently recomputed `shift`. In a disposable true-bench fixture, a same-HEAD dirty PO moved `A` from context `old` to `new`; a reviewed artifact deliberately omitted the context shift but listed the corresponding add/remove and dispositions. `--update-baselines` returned `0`, no errors, and recorded the forged baseline. This is a reproduced governance bypass. |
| 3 | Full import aliases and assigned module-chain AST resolution | **CLOSED for claimed sink cases** | Independent fixtures detect direct import alias, from-import sink alias, and multi-step assigned frappe-module chains. A wrapper assigned as `t = f._` is conservatively flagged rather than bypassed; this is a false-positive residual, not a release bypass. |
| 4 | Strict retired delete/rename/replacement lifecycle with mandatory pinned evidence and transitions | **PARTIAL** | Current code requires pinned evidence, delete old-path absence and `-`, and rename old-path absence with a live or subsequently retired target. Tests cover valid/invalid delete and rename. The format still models only `delete|rename`, not an explicit replacement event/state/version transition; the claimed “versioned retired lifecycle” is not present in the schema. |
| 5 | Canonical row/proposal/verdict/artifact decisions plus manifest/Merkle binding and auto-invalidation | **PARTIAL** | CSV row identity, proposal hash, role verdict fields, artifact hashes, decision-file SHA, and decision-root are checked. But the localization manifest binds the release-decision root, not the Stage 2 inventory Merkle root, and `decision_root()` hashes only decision IDs rather than canonical decision objects. The separate `decisions_sha` mitigates object mutation, but the stated manifest/Merkle-root pin is not implemented. |
| 6 | Strict freshness: classified site, any future/stale time, full health, exact counts/digest/criticals/input hashes | **NOT CLOSED** | Current evidence is internally green, but policy enforcement is incomplete: timestamps up to five minutes in the future are accepted; the site-classification artifact hash is not manifest-bound; `production_mutation_authorized` is not enforced false; `packaged_rows` is not compared with the current CSV Released-row count; and `constraint_name` plus required drift/catalog timestamps are not checked. Existing tests only assert selected current values/manifest keys, not these negative cases. |
| 7 | Deterministic five-column Merkle reproducible from committed SQL with 18,412 rows and `6848f2ed…` | **NOT CLOSED (P0 evidence integrity)** | Running the exact committed five-column SELECT on `v16.localhost` returned `18,412` rows but `sha256(repr(rows)) = 5da1e43d37544d979b3eaca39c90277f41257c6ba745363ea35f9e4a00620044`, not manifest `6848f2edf7132a2d6a3f4a59a70e5d7ddf5a9829c623e30eefe208a5b5510882`. The saved `merkle.txt` output is visibly truncated after `generator: ... con`, so it cannot resolve the normalization mismatch. |
| 8 | Exactly ten complete command/UTC/exit/hash envelopes | **NOT CLOSED** | Exactly ten `.txt` files exist and all have command, start, finish, and exit fields. Most do not include a result/artifact SHA, despite the claim that every envelope does. `merkle.txt` has a manifest hash but truncates the underlying result; therefore the collection is not ten complete independently reproducible hash envelopes. |

## Findings by severity

### P0

1. **Forged/omitted context-shift review is accepted.** The consumer trusts the
   reviewed artifact for its expected context shifts instead of comparing it to
   the recomputed `shift`. The bypass was reproduced safely in a disposable
   bench-shaped tree and includes the same-commit dirty-candidate case.
2. **The committed inventory recipe does not reproduce the recorded Merkle.** The
   row count is correct but the exact documented SQL and `repr(rows)` scheme yields
   `5da1e43d…`, not `6848f2ed…`; saved evidence is truncated.

### P1

3. Freshness is not strictly fail-closed for future time, site-classification
   hash/authorization, CSV Released count, constraint identity, or required audit
   timestamps.
4. The manifest does not pin the inventory Merkle as claimed, and the decision
   root covers identifiers rather than canonical decision objects (with the
   decision-file SHA providing only a parallel whole-file binding).
5. Retired-source validation is materially improved, but no explicit versioned
   replacement lifecycle/state transition exists.
6. The ten logs are structurally present but are not ten complete hash envelopes;
   the Merkle record is insufficient to reproduce its asserted root.

## Decision

**BLOCKED — Stage 2 Round 7 is not independently verified.**

Round 7 closes the dangerous checkout-mutation defect and the advertised tests,
counts, local gates, AST sink cases, vendor cleanliness, and runtime-drift evidence
are green. It does not close the vendor context-shift bypass or deterministic
inventory proof, and several claimed freshness/decision/retirement guarantees are
not implemented. Stage 1C remains valid. Stage 3 must not begin under the locked
sequence.

## Exact next gate

1. Make producer and consumer call the same canonicalization function. Build the
   consumer `want` from recomputed `added`, `removed`, `changed`, and **`shift`**;
   reject missing, forged, or duplicate context shifts and add the exact disposable
   same-commit omission repro as a permanent hermetic test.
2. Add an explicit `root` parameter through `update_baselines`, baseline paths,
   inventory writes, and manifest writes; eliminate module-global-root mutation in
   tests and assert the precise refusal code/reason.
3. Define and commit one inventory serializer (including DB-return type and Unicode/
   null normalization), execute it against the committed SQL, and regenerate the
   manifest/log so an independent run reproduces the exact root.
4. Bind the inventory manifest SHA and Merkle root into the localization manifest
   and decision release envelope. Hash canonical decision objects for the decision
   root, or formally specify and test why ID-root plus whole-file SHA is the locked
   contract.
5. Reject any future freshness timestamp; bind and validate the site-classification
   hash and `production_mutation_authorized=false`; reconcile `packaged_rows` to the
   current Released CSV count; enforce `constraint_name` and required health
   timestamps with adversarial tests.
6. Version the retired lifecycle schema and define explicit replacement/terminal
   transition semantics, or narrow the claim and plan requirement to the enforced
   delete/rename model.
7. Regenerate exactly ten logs with complete command/start/finish/exit and
   input/result hash envelopes; ensure the Merkle log contains the full serializer,
   row count, and result digest. Then rerun all gates/tests from a pre-hashed
   checkout and request a fresh independent AI-R.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
