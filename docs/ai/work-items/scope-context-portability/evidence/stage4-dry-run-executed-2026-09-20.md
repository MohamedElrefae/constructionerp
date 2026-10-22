# Stage 4 DRY_RUN Executed — IMPORT Authorization Gate (2026-09-20)

**Work item:** erp-arabic-bilingual-data
**Stage:** 4

The owner-authorized read-only dry-run executed successfully against the frozen payload.

```
status                  = VERIFIED_FOR_RELEASE
sub_status              = IMPORT_AUTHORIZATION
gate                    = IMPORT / import-1aaf9d659f97b27fe7f4a19c
dry_run_evidence_digest = 22101965dc317ee2ada82c860ad27bf7e38103a8cf69cbcdf58a1ac2c6bff4e5
```

## Dry-run result (read-only)

| Check | Result |
|---|---|
| identities | 81 |
| live accounts present | 81/81 |
| live total accounts | 2097 |
| duplicate codes | none |
| blank names | none |
| unexpected current values | none |
| stale rows | none |
| approval gaps | none |
| blocking | **false** |

Evidence: `stage4-dry-run-evidence/v1`, `planned_values_sha256 7681602f…`.

## Executor correction

The initial DRY_RUN grant routed to a builder agent, which cannot perform a read-only ERP
check. The grant now sets `sub_status=DRY_RUN` with no agent role; the owner executes
`run --dry-run`, which reads Accounts via a read-only Frappe console and records the
evidence digest. A `dry_run_ready` owner event settled the state left by the earlier
transition.

## Boundary

No ERP data was modified. The write/import path remains a separate owner authorization
(IMPORT token) and is **not** implemented here. `committed=false`, no push or merge.
Full orchestrator suite: **231 passed**.
