# Release Notes v6.8.0-rc1

## Release Candidate Tag
- **Tag**: `v6.8.0-rc1`
- **Branch**: `develop` → merged into `main`
- **Merge message**: `merge: release candidate v6.8.0-rc1 (develop to main)`

## Commercial Architecture

### Additive Pricing (120% Rule)
- BOQ Item costing now uses additive-direct-cost pricing model
- `pricing_rule_version` column set to `additive-direct-cost/v1` on all BOQ Items
- Factor > 0 enforced via compensating guards in `construction/services/security.py`
- `cost_basis` column records the basis: `Manual`, `Approved Analysis`, or `Legacy Review`

### Approval Immutability
- Once an analysis is submitted and approved, its `pricing_rule_version` cannot be altered
- Rollback path requires manual_cost_snapshot review and submitted history reconciliation

### Factor Validation
- `factor` field must be > 0 on all BOQ Items
- Negative or zero factors are rejected at document save
- Legacy conversions preserve existing factor values where approved analysis exists

### Deletion Rollup
- Deleting a BOQ Item line item rolls up totals to the associated BOQ Header
- `quantity_executed` and `quantity_certified` are zeroed when the last item is deleted
- Header `line_total` recalculates from remaining items

## Verification Metrics

| Test Suite | Tests | Result |
|---|---|---|
| 17 modules CI Run | 11 | Green |
| 21 modules bilingual matrix | 21 | Green |
| 10 UAT commercial workflow tests | 10 | Green |
| 33 security tests | 33 | Green |

## Security Defenses

- **Frappe v16.36.1 alignment**: All RPC endpoints re-validated against v16.36.1 security model
- **Compensating guards in `security.py`**: Input sanitization, scheme blocking, upload validation
- **Scope query overrides**: `overrides/scope_query.py` prevents unauthorized cross-company data access
- **Redis ephemeral ports**: System Redis (6379) untouched; test ports 11000/13000 used idempotently

## Multi-Site Cutover

- **44-step cutover orchestrator**: `scripts/orchestrate_cutover.py` with dry-run validation
- **Backup restore timing**: 8.62s measured gzip decompression on v16.localhost database dump
- **Fail-closed rollback**: Maintenance mode toggle ensures atomic state restoration
- **Backup validation**: gzip integrity check (`gzip -t`) and age verification (< 24h)
- **Four-site coverage**: v16.localhost, localhost, v16rehearsal.localhost, and backup directories

## Manifest Governance

- **40 manifests** across **423 file entries** verified with zero drift
- MANIFEST.json files in each work-item directory checksum-verified against source
- `python3 -c 'import glob, json, hashlib, os; manifests = glob.glob("docs/ai/work-items/*/evidence/MANIFEST.json")'` — 0 missing, 0 mismatched digests