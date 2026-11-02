# T3 Engineering Integration Plan v1.1

## Purpose

This revision converts the T3 integration consultation into an implementation-oriented plan for the Construction ERP repository.

## Core decision

- T3 Code is the owner-facing interaction, model-selection, and remote-access interface.
- The existing Python orchestrator remains the sole engineering authority.
- ERPNext v16 remains the business-system boundary.
- Native worker execution remains the default governed execution path.
- T3-hosted execution is opt-in and must pass qualification.
- A T3 fork is permitted only after extension, MCP, and ACP options are measured and found insufficient.

## Architecture

```text
Owner / Manager
      |
      v
T3 Code UI
  - conversation
  - provider/model selection
  - responsive mobile controls
      |
      v
T3 Integration Adapter
  - Engineering panel
  - approval cards
  - role assignment
  - evidence viewer
      |
      v
Engineering Control Service
  - versioned API
  - authentication and actor provenance
  - idempotent commands
  - projections and events
      |
      v
Existing Python Orchestrator
  - engine.py
  - store.py
  - routing.py
  - candidates.py
  - validation_runner.py
      |
      +--> Native Worker Runtime [default]
      +--> T3 Runtime Adapter [qualified only]
      |
      v
ERPNext v16 Construction ERP
```

## Authority rules

| Concern | Authority |
|---|---|
| Business policy | Owner or explicitly authorized manager |
| Workflow stage and gates | Python orchestrator |
| Plan, scope, role, candidate binding | Python orchestrator |
| T3 conversation state | T3 |
| Provider/model catalog | T3/provider boundary |
| Result acceptance | Python orchestrator |
| Owner approval | Authenticated human principal through dedicated API |
| Deployment | Separate release authority |

## Non-negotiable invariants

1. Only the Engineering Control Service may mutate orchestrator state.
2. T3 must not write orchestrator SQLite databases or exported ledgers.
3. An agent cannot create an owner, business, commit, or deployment approval.
4. Builder and verifier must have separate execution/context lineage.
5. Every result binds to job, role, candidate, environment, and evidence IDs.
6. Duplicate or stale commands return the existing receipt or fail safely.
7. Native execution remains default until T3 execution qualifies.
8. A missing, malformed, or truncated artifact cannot become a PASS.

## Engineering Control Service API skeleton

Base path: `/engineering/v1`

Authentication: authenticated T3 server-to-service request; scoped token; no general shell access.

### Operations

| Method | Path | Purpose |
|---|---|---|
| GET | `/work-items` | List authorized work items |
| GET | `/work-items/{id}` | Read authoritative projection |
| GET | `/work-items/{id}/events` | Read bounded event history |
| POST | `/work-items` | Create governed work item |
| POST | `/work-items/{id}/plan` | Submit or amend plan |
| POST | `/work-items/{id}/assignments` | Submit role/provider/model assignment |
| POST | `/work-items/{id}/execution-requests` | Request eligible execution |
| GET | `/jobs/{id}` | Read job state |
| POST | `/jobs/{id}/observations` | Submit idempotent runtime observation |
| POST | `/jobs/{id}/results` | Submit structured result and evidence |
| POST | `/work-items/{id}/decisions` | Record authenticated owner decision |
| POST | `/work-items/{id}/pause` | Pause future work |
| POST | `/jobs/{id}/cancel` | Request cancellation |
| GET | `/evidence/{id}` | Retrieve evidence metadata/artifacts |

### Example: request execution

```json
POST /engineering/v1/work-items/wi_123/execution-requests
{
  "role": "builder",
  "requested_by": "owner:mohamed",
  "plan_id": "plan_456",
  "plan_revision": 3,
  "scope_id": "scope_789",
  "runtime": "native",
  "idempotency_key": "req_owner_2026_11_02_001"
}
```

Required response:

```json
{
  "job_id": "job_001",
  "state": "reserved",
  "execution_authorization_id": "auth_001",
  "runtime": "native",
  "expires_at": "...",
  "receipt": "..."
}
```

### Example: owner approval

```json
POST /engineering/v1/work-items/wi_123/decisions
{
  "decision": "approve_plan",
  "actor": "owner:mohamed",
  "actor_type": "human",
  "plan_id": "plan_456",
  "plan_revision": 3,
  "scope_id": "scope_789",
  "role_policy_id": "policy_001",
  "idempotency_key": "decision_owner_2026_11_02_001"
}
```

The service must reject the decision if the reviewed plan, scope, role policy, or state revision no longer matches.

## Evidence schema

```json
{
  "schema_version": "1.0",
  "evidence_id": "ev_...",
  "job_id": "job_...",
  "work_item_id": "wi_...",
  "candidate_id": "cand_...",
  "candidate_digest": "sha256:...",
  "role": "verifier",
  "check_id": "retention_calculation",
  "status": "pass|fail|blocked|not_run|skipped",
  "started_at": "...",
  "finished_at": "...",
  "environment": {
    "host_id": "...",
    "runtime": "native|t3",
    "runtime_version": "...",
    "provider": "...",
    "model": "..."
  },
  "artifacts": [
    {
      "artifact_id": "...",
      "type": "test_report|log|screenshot|database_snapshot|report",
      "uri": "...",
      "sha256": "...",
      "size_bytes": 0,
      "truncated": false
    }
  ],
  "summary": "Human-readable result summary",
  "limitations": []
}
```

## Work packages

### WP0 — T3 seam and baseline audit

Deliverables:

- T3 app/server/CLI/provider version manifest
- Extension point inventory
- ACP/MCP capability assessment
- Fork justification register
- Bypass surface inventory
- Threat model
- Compatibility matrix

Exit: integration approach is selected with evidence.

### WP0.5 — ERPNext v16 impact map

Deliverables:

- Affected DocType matrix
- Permission and role-profile impact
- Fixture and migration impact
- Report/print-format impact
- Client/server script impact
- ERPNext selector and UI regression plan
- Protected test-site and seeded-data strategy
- Production-data protection rules

Exit: ERPNext-specific risks and required regression coverage are documented.

### WP1 — Engineering Control Service contract

Deliverables:

- Versioned API contract
- JSON Schema or OpenAPI definitions
- Authentication and actor-provenance design
- Idempotency and receipt rules
- Contract tests
- Offline fake T3 adapter

Exit: API contract tests pass without a real T3 connection.

### WP2 — T3 advisory integration

Deliverables:

- Read-only Engineering panel
- Work-item status projection
- Findings and evidence viewer
- Conversation mode badge

Exit: owner can inspect governed work in T3 without any mutation capability.

### WP3 — T3 governed owner interface

Deliverables:

- Plan approval/rejection cards
- Role/provider/model assignment view
- Build/verify progress
- Evidence and finding views
- Pause/cancel controls
- Mobile-responsive layout

Exit: owner completes one representative task without terminal commands or manual agent-message copying.

### WP4 — Execution qualification

Deliverables:

- Native execution regression evidence
- T3 execution adapter qualification
- Role isolation tests
- Cancellation and reconciliation tests
- Provider failure tests
- Candidate-binding tests

Exit: only qualified runtimes may execute governed jobs.

### WP5 — Mobile and operations

Deliverables:

- Secure remote route
- Phone-responsive approval and inspection UI
- Reconnect/state-freshness behavior
- Background host behavior
- Support and recovery instructions

Exit: phone can inspect and make authorized decisions safely.

### WP6 — Packaging, upgrade, and rollout

Deliverables:

- Custom build identity and update policy
- Reproducible package
- Backup/recovery procedure
- Upgrade rehearsal
- Canary plan
- Operator handover

Exit: one full upgrade/recovery rehearsal passes before rollout.

## WP1 minimum proof set

| ID | Proof |
|---|---|
| P1 | Owner creates a bounded engineering request in T3 |
| P2 | Engine creates plan/review/build/verify workflow |
| P3 | Builder cannot start without required plan authority |
| P4 | Invalid evidence or candidate binding is rejected |
| P5 | Builder and verifier contexts are separate |
| P6 | Owner approval is a server-side authenticated decision |
| P7 | Duplicate approval does not duplicate the protected action |
| P8 | Phone browser can inspect state and approve/reject safely |

## ERPNext v16 impact checklist

For every governed engineering task, record:

- [ ] Affected DocTypes
- [ ] New or changed fields
- [ ] Fixture changes
- [ ] Migration requirements
- [ ] Permission changes
- [ ] Role profile changes
- [ ] Client scripts
- [ ] Server scripts
- [ ] Report changes
- [ ] Print format changes
- [ ] Workflow/state changes
- [ ] API endpoints
- [ ] Test-site seed data
- [ ] ERPNext v16 UI selector checks
- [ ] Upgrade compatibility
- [ ] Rollback plan

## Decision requested

Approve WP0, WP0.5, and WP1 only, with a defined engineering-time and AI/provider budget. WP2 onward requires review of the API contract and feasibility findings.
