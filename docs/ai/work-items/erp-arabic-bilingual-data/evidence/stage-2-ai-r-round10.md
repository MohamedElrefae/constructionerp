# Stage 2 Round 10 — Independent AI-R Verification

## Identity, authority, and candidate

| Field | Value |
|---|---|
| Role | AI-R — fresh independent Stage 2 Round 10 verifier |
| Agent/session | `/root/stage2_ai_r_round10` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-05` |
| Candidate | `feature/erp-arabic-bilingual-data`; Construction `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; uncommitted worktree |
| Boundary | Read-only repository/site checks, disposable fixtures, and this report only. No code, catalog, payload, governed evidence, Git index/history, or runtime translation value was intentionally changed. |

This verifier was not the Builder or a prior reviewer. The canonical v4 plan,
handoff, implementation record, Stage 2 evidence through Round 9, current source,
tests, CI, vendor controls, freshness and retirement controls, inventory/Merkle,
payload/catalogs, ten evidence envelopes, and governed index were reviewed.

## Exact reviewed hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `b7964e01d9028ecb859cf1a25a43e8c9146eeaf92e33e9dc5537a64ed69b8d55` |
| Checker / tests | `c3629978a4b8653ef16abd4edd7339b25bdae3a9c7ad3efa93aae83b7b34d926` / `38f1b14a56aaa7eeb68a6b16cfc668318ed84bafc5a8a2145675e5524dd7298d` |
| Vendor delta tool / baseline | `624aba05e84f0cbaeee23f374411a0c18483e4ce8e0a9561778a1ee482041e6c` / `4e8a7152eb5af053b3d654796d1c8792d95fd96161ce9b6bc696320928773b2a` |
| Freshness collector / evidence | `6bf96dbdc1664496bf6a4bb6c6f96260598914fb978115962a0d160eb5fbd34d` / `09c1d9c614ae830c82db3e8812fbe9f1150f42af95c11e072651468b5023c79c` |
| Localization / inventory manifests | `2f75f8bbe85741a7a8ca743c4267b55848be4c0e2ea46f0518606cf18dae4d2e` / `08ffeb63037dc26281b3e0401889afd5a6f7a296d7d9c9552b32f94cb1effb05` |
| Construction PO / payload | `ef088f7a6be5b358faed3f1c7a28af101d15a65d2277c752105e822274f1b02a` / `037e79c22248481e0ad56ad749d6210f56f038fe5f0efb1d045cc830444a1e8c` |
| Retired lifecycle | `cad850c823a169ff338b2b8e78cf17d20626d36efd0e27dbd38e214c2d162706` |
| Evidence index | `acb506c6275450376562a2444c15a212a1f98800754f2519678609409b44ca57` |

## Independently reproduced positives

- Standalone adversarial suite: `70` tests, all pass.
- Full localization gate: catalog `771`; `248` files; `631` wrapped literals;
  `21` JSON labels; missing `0`; errors `0`.
- Vendor audit and requested positive scoped gate exit `0`.
- Bench independently passed the `70 + 13 + 6 + 5` modules executed before the
  local Redis service became unavailable. The saved governed aggregate envelope
  records `105` tests (`70 + 13 + 6 + 5 + 3 + 8`) with exit `0` and is correctly
  hash-bound by the index; the last two modules could not be independently
  repeated in this session because Redis at `127.0.0.1:13000` refused connection.
- The ten envelope file SHA-256 values match their governed index entries.
- Payload remains `34` Released rows; the governed dry-run records `34` skipped,
  `0` created/updated/drift. Vendor PO files remained Git-clean.
- Inventory manifest remains `18,412` rows with recorded Merkle
  `973b8faccbc12927c48c1605cfbd4a0604388e9e3f6acaaaca8819f9121559b5`.

## Round 10 closure matrix

| # | Round 9 finding | Result | Independent assessment |
|---:|---|---|---|
| 1 | Every vendor path honors explicit isolated root | **NOT CLOSED (P0)** | Most checker paths now honor `root`, but `scripts/vendor_upgrade_delta.py:main()` still computes both `old_po_sha` and `new_po_sha` using `git -C ROOT.parent/app`, not `root.parent/app`. Its dynamic import path also uses `ROOT/scripts`. Therefore an explicit-root CLI run can parse the isolated blobs but stamp hashes sourced from the live checkout. No permanent test invokes the delta CLI under conflicting live/isolated roots; the claimed cross-root fixture is absent. |
| 2 | Delta provenance validation | **PARTIAL** | The update consumer independently checks commit/PO hashes and recomputed canonical sets/context shifts, and forged consumer fixtures pass. The producer's cross-root hash defect above means producer provenance is not trustworthy under the claimed boundary. |
| 3 | Tomorrow retirement rejected in actual gate | **CLOSED** | `load_retired()` rejects dates strictly greater than current UTC date and validates schema, event semantics, path state, and pinned evidence. |
| 4 | Freshness bounds/consistency, E2E mutation tests, closed handles | **CLOSED for implemented policy** | Actual `check_manifest()` mutation tests reject future audit timestamps and critical-map tampering; audit-map agreement, collection age/site/health/count bindings are checked; CSV uses a context manager. Residual policy risk: a documented 24-hour DB/app skew allowance is deliberately retained. |
| 5 | Exactly ten complete envelopes plus governed index | **NOT CLOSED (high)** | Exactly ten envelopes exist, each has one command/start/end/exit block, and every SHA matches the index. However `merkle.txt` still embeds a visibly truncated `INV8` JSON fragment ending mid-category. There is no gate/test that rejects truncated, missing, extra, or tampered evidence/index content, so the Round 9 requirement “truncated/tampered/missing/extra evidence rejected” is not implemented. The index binds the truncated file faithfully; hashing does not make it complete. |

## Active findings

1. **P0 — explicit-root provenance leakage.** In
   `scripts/vendor_upgrade_delta.py`, `blob()` correctly uses `root.parent`, but
   the later hash loop calls Git with `ROOT.parent`. This creates mixed-origin
   evidence and violates the all-path explicit-root contract.
2. **High — evidence completeness is asserted, not gated.** The Merkle envelope
   remains truncated. Current tests contain no governed evidence-index verifier,
   so omission, addition, truncation, or index tampering is not fail-closed.
3. **Environment note.** A fresh Bench aggregate rerun was interrupted after 94
   passing tests by Redis connection refusal. This does not negate the correctly
   indexed prior 105-pass envelope, but prevents a complete independent live
   rerun in this session.

## Decision

**BLOCKED — Stage 2 Round 10 is not independently verified.**

Round 10 closes retirement-date handling and materially improves freshness and
evidence indexing. It does not close the explicit-root producer boundary or the
required fail-closed evidence completeness contract. Stage 1C remains valid;
Stage 3 must remain blocked.

## Exact next gate

1. Replace every remaining `ROOT` use in vendor delta execution with the supplied
   root where it resolves scripts, Git trees, blobs, hashes, temporary files, or
   outputs. Add a true conflicting cross-root CLI fixture asserting hashes and
   output originate only from the isolated root and that the live checkout is
   byte-identical.
2. Add a governed evidence-index validator and adversarial tests for truncated,
   altered, missing, extra, duplicate, and path-traversal envelopes. Regenerate
   `merkle.txt` without the incomplete embedded JSON, or omit the JSON and bind
   the complete inventory manifest by exact SHA and reproducible Merkle command.
3. Restore Redis, rerun the full 105-test aggregate, regenerate the affected
   evidence/index atomically, then request a fresh AI-R rerun.

Owner authorization remains separately required for commit, push, merge,
deployment, or production mutation.
