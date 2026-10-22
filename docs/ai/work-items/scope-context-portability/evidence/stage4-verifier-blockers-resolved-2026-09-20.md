# Stage 4 Verifier Blockers Resolved (2026-09-20)

## Context

The Stage 4 verifier read the frozen artifacts (prior fix) and returned three blocking
findings. All three were valid; each is now addressed.

## 1. Independent panel bindings unverifiable

The composed bundle carried only A2 row decisions, not the A1/A3 panel verdicts or
provenance. `compose_bundle` now accepts and records a `panel` section: role, session id,
verdict, bound `proposal_sha256` and `review_sha256` for every required reviewer. The
verifier can now confirm the exact artifacts were independently reviewed.

## 2. AGENTS.md unavailable

The verifier instruction requires reading AGENTS.md, but it was not mounted. The verifier
packet now mounts the worktree `AGENTS.md` read-only at
`/tmp/workspace/private_inputs/AGENTS.md`.

## 3. Validation command could not execute

The configured command `python3 -m pytest tests_offline -q` resolved `python3` to
`~/.local/bin/python3` (uv Python 3.14, no pytest). The command now uses the pinned
orchestrator venv interpreter:
`orchestrator/.venv/bin/python -m pytest tests_offline -q -p no:cacheprovider`
(67 passed). The instruction also clarifies that the Stage 4 `scope.allowed_paths`
app-layer files belong to a later stage and their absence is expected, not blocking.

## Verification

Full orchestrator suite: **225 passed**. Offline suite: **67 passed**. No ERP mutation,
DRY_RUN, IMPORT, commit, push, or merge.
