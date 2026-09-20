# Controller Amendment and Stage 4 Native Gap — 2026-09-19

**Work item:** erp-arabic-bilingual-data (Stage 4) + scope-context-portability controller
**Owner directive:** "find fix to use cli v 1.18 or above" (opencode 1.14.33 removed; free
models broken)

## Controller amendments (owner-authorized for the opencode 1.18 migration)

1. `orchestrator/engine.py`
   - Added `resolve_opencode_binary()` and `OPENCODE_MIN_VERSION = (1, 18, 0)`.
   - `reconfigure_role` and `role_catalog` no longer hardcode `/usr/bin/opencode-cli`
     / `1.14.33`; they resolve a standalone CLI and require version >= 1.18, recording
     the detected version in the role pin.
2. `orchestrator/adapters.py`
   - When `neutral_mounts` are present, the OpenCode permission config grants
     `external_directory: allow`. Stage 4 private inputs/outputs are neutral-mounted
     under `/tmp/workspace`, outside the execution root, and OpenCode 1.18 gates them
     behind this permission.
3. Role reconfiguration (owner path, `set-role`):
   - `proposer`, `ai-a3`: tool `opencode`, binary `/home/mohamed/.local/bin/opencode-1.18.31`
     (sha256 `f9dab322…`), model `opencode-go/muse-spark-1.3-contributor`.
   - `architect`: prompt pin refreshed to the committed role file `531a2325…` (the adopted
     config predated commit `db7d7b2`).

Verification: full orchestrator suite **225 passed**. `doctor` green.

## OpenCode free-tier finding

`opencode/*-free` models are rejected (HTTP 403 `FreeTierError`) whenever the permission
config denies `*`/`read`/`bash`, which the orchestrator sandbox requires. Paid
`opencode-go/*` models work under the same sandbox with the same permission config. This
is why the roles were pinned to `opencode-go/muse-spark-1.3-contributor`.

## Stage 4 native progress

- Fresh v2 PLAN grant approved; proposer dispatched.
- **Proposer succeeded** (session `ses_f44e1cc06ffe54RbEb44AxKID6`): proposal frozen,
  state advanced to `PROPOSAL_FROZEN`.
- Quorum `ai-a1`, `ai-a2`, `ai-a3` dispatched in parallel; all exited 0.

## Discovered blocker (native reviewer path, not yet repaired)

The three quorum reviewers were not accepted:

1. **No private review blob.** `_prepare` gives the proposer a stage instruction to write
   `/tmp/workspace/private_output/output.json`, but gives quorum reviewers no such
   instruction. `private_out/` was empty for all three, so
   `validate_and_store_review` cannot read a review document.
2. **Session binding is unsatisfiable by a native agent.**
   `validate_and_store_review` requires the review document to declare
   `session_id == observed native session`. OpenCode does not expose the session id to
   the model (verified: the model reports `NONE`; `--session` cannot pre-create an id).
   The synthetic tests fabricate this field, so the gap was never exercised.
3. **Duplicate final wire messages.** `ai-a3` emitted two valid final JSON messages with
   distinct messageIDs; `parse_output` correctly rejects ambiguous result messages
   (`MALFORMED_RESULT: invalid wire envelope`).

State is parked at `PAUSED / PROPOSAL_FROZEN` with the three terminal reviewer jobs
pending owner reconciliation. No ERP mutation, DRY_RUN, IMPORT, commit, push, or merge
occurred. The production checkout and private data are untouched.

## Recommended next step (requires owner decision)

Decide the reviewer session-binding contract before repairing the native path:
- option A: engine stamps the observed native session into the reviewer document and
  continues to enforce cross-job session uniqueness centrally; or
- option B: engine passes a per-job opaque review token in the packet that the reviewer
  declares, bound to the observed native session.

Either option also requires a quorum stage instruction to read the frozen proposal and
write the `stage4-panel-review/v1` blob, plus a deterministic single-final-message rule.
