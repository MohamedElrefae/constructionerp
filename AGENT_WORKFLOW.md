# Independent-agent engineering workflow

Phase 0 is complete under the [owner-supplied directive](docs/ai/work-items/scope-context-portability/CONSULTANT_DIRECTIVE_2026-09-11.md). Phase 1 code and its local checks are recorded in [IMPLEMENTATION.md](docs/ai/work-items/scope-context-portability/IMPLEMENTATION.md). Phase 2 qualification, the real offline pilot and ERP adoption remain gated.

Current native sequence: **Codex architect → separate Codex plan reviewer (authorized Antigravity substitute) → owner PLAN grant → OpenCode builder and captured offline tests → independent Codex verifier → owner commit authorization and execution.** No Antigravity execution is claimed. Each role starts its own process/session. Files carry dependent context; SQLite governs transitions.

Code defects return to the builder with all unresolved findings. Design defects return through architecture and plan review. Optional improvements enter backlog without blocking. Disagreements pause for the owner. Three unsuccessful review cycles or two unchanged normalized blocker snapshots escalate, including across restarts and architecture returns.

The approved role prompts remain unchanged:

- [Architect](docs/ai/roles/architect.md)
- [Plan reviewer](docs/ai/roles/reviewer.md)
- [Builder](docs/ai/roles/builder.md)
- [Independent verifier](docs/ai/roles/verifier.md)
- [Proposer and independent panel](docs/ai/roles/ai-reviewer.md)

Native jobs cannot write the mounted control store or Git metadata, and receive selected dependency artifacts without peer-review outputs. Owner terminal conventions alone are not an isolation mechanism. Same-account unsandboxed processes remain trusted owner processes.

See [operator commands and recovery procedures](orchestrator/README.md). The engine never executes project commits, releases or imports. Completed ERP services and evidence remain untouched historical records. A transport probe or synthetic result does not count as the real pilot.
