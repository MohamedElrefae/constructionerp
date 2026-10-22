# Phase 2 synthetic verification

These tests qualify the frozen Phase 1 engine at commit `4b77803af418cea8459c4cb7d9a0248674845da3`. They live outside its source freeze. No production fixes belong in this directory.

Run from the isolated worktree using its pinned Python:

```sh
orchestrator/.venv/bin/python -m pytest orchestrator/tests docs/ai/work-items/scope-context-portability/verification/phase2 -q --junitxml=/tmp/phase2-full.xml
```

Host namespace support is needed by the existing offline isolation tests. Do not disable their isolation to run them inside a more restrictive outer sandbox.

Every agent response is explicitly SYNTHETIC. The new tests use delayed stub sessions and the actual LangGraph/SQLite engine. The malformed-result case invokes the real Codex output parser against synthetic bytes; it never invokes the Codex provider. The existing process-restart test kills a coordinator while a detached synthetic worker is in flight. This proves process recovery, not live native provider capability or pilot acceptance.

All source changes, snapshots, SQLite restores and test commits occur in pytest-created disposable repositories. Synthetic commits are necessary fixtures for parent/tree binding and post-commit/pre-record recovery. No commit is made in the project worktree. `VACUUM INTO` is executed on the fixture's actual workflow database; rollback detection and explicit owner reconciliation use the shipped engine.

The evidence report records both successful and failing scenarios. Tests require the named failure class in durable workflow state; merely pausing with an unspecified exception does not satisfy canonical §6.2. Keep failing regressions visible until the owner authorizes a frozen-source correction. The report makes no ERP adoption or real-pilot claim.
