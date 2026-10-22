# Stage 8 — isolated backup/restore rehearsal drill (2026-09-22)

Rehearsal target: **`v16rehearsal.localhost`** (isolated site; no mutation of
`v16.localhost`; no production touched). Backup set under test:
`sites/v16.localhost/private/backups/20260922_011803-v16_localhost-*`
(database.sql.gz, files.tgz, private-files.tgz, site_config_backup.json).

## Restore completeness (console, read-only)

| Check | Result |
|---|---|
| GL Entry rows | **4** (matches source) |
| Posted JVs | `ACC-JV-2026-00001`, `ACC-JV-2026-00002` `docstatus=1` |
| AR outstanding Prestiga-Biz | **EGP 6,000** |
| Invoice draft untouched | `ACC-SINV-2026-00001` `docstatus=0` |
| Private files | **30** under `sites/v16rehearsal.localhost/private/files/` |
| Public files | **15** under `sites/v16rehearsal.localhost/public/files/` |
| Site encryption_key | injected from source `site_config_backup.json` |
| Language / country | `ar` / Egypt |
| Site marker | `Website Settings.app_name = REHEARSAL-SITE-MARKER` (restored as needed) |

## Routing isolation (root cause + fix)

Unpinned `bench serve` resolves every request through
`common_site_config.default_site` → always `v16.localhost`. Fix applied for
the drill: `dns_multitenant: true` in `sites/common_site_config.json`, and the
rehearsal server is **pinned**: `bench --site v16rehearsal.localhost serve
--port 8002`. Login/API evidence below was obtained only against that pinned
listener (never against owner `:8000`).

## Hard preflight (standing Stage-8 gate)

```
PASS redis-cache: port 13000 PING ok
PASS redis-queue: port 11000 PING ok
PASS site-http: /ping 200
PASS desk-boot: boot lang=ar
PASS desk-boot: __messages entries=10752
PASS desk-boot-key: 'Add / Remove Columns' present in boot
PASS desk-boot: UAT session logged out
UAT PREFLIGHT: PASS
```

Command: `scripts/uat_preflight.py --site=v16rehearsal.localhost --port=8002`
(password on stdin; `--port` is a hard requirement — without it the preflight
silently targets `:8000`).

`scripts/uat_preflight.py` fixes landed with this drill:
1. login is **POST** (GET returned 401 with no cookie);
2. parsed `--port=` is assigned to `UAT_PORT` (was parsed and dropped);
3. `http_req_attested` no longer defaults `port=8000` over `UAT_PORT`.

## Browser drill (Playwright, ar Desk session, pinned `:8002`)

- Desk boot: `lang=ar`, user `Administrator`.
- **Accounts Receivable**, mode `both`: **5 rows** — Arabic headers
  (`تاريخ القيد`, `المبلغ المستحق`, aging buckets …), `Prestiga-Biz` /
  `1310 - Debtors - E` lines including the restored 2026-09-21 JVs and the
  customer summary (outstanding 6,000).
- **General Ledger**, mode `both`: **14 rows** — bilingual account lines
  `1310 - Debtors - E — المدينون`, Arabic column headers
  (`مدين (EGP)`, `الائتمان (EGP)`, `الرصيد (EGP)`, `نوع السند` …), including
  opening-balance rows and the owner-posted JVs.

## Boundary

- Proves **backup → isolated restore → preflight → bilingual UAT** only.
- Source site `v16.localhost` was not restored over; no production mutation.
- Does **not** satisfy the remaining Stage-8 production gates (real production
  masters/ledger, explicit production authorization).
- No catalog / `_()` msgid change from this drill; Stage-2 evidence re-pin is
  the separate HEAD-drift fix on `80787af`.
