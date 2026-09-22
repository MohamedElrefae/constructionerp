# Production-readiness AI-R Verification — exact commit `0c8057f`

## Identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — independent evidence/commit verifier (owner-directed sequence step 1) |
| Verified at (UTC) | `2026-09-22` |
| **Exact candidate** | **`0c8057f5580bc3cebf3e956212013a2076698677`** |
| Parent | `c3c83213f661cf077890a48a99e0b0d0b78f114e` |
| Tree | `ec0adec2cad25eaf0ca90b736b6d357bf295e151` |
| Subject | `fix(stage8): preserve preflight fail-closed cleanup` |
| Worktree HEAD at check | `453d193e9d7150a963488b8af5583bd0d6caae38` (plan-doc only vs `0c8057f`) |
| Boundary | Read-only verification of commit tree, governed evidence bundle, tests/gates, and this report. No catalog/payload/runtime mutation, no production touch, no W6-0b. Owner still must supply production data + named-site/window authorization (steps 2–3). |

Superseded candidate: **`0433497` is NOT the AI-R target** — that revision could crash with `UnboundLocalError` on preflight connection-failure cleanup; repaired in `0c8057f`.

## 1. Exact-commit integrity — PASS

- `git rev-parse 0c8057f` → `0c8057f5580bc3cebf3e956212013a2076698677`.
- Every governed code/artifact blob under `0c8057f` matches the live worktree hash:
  `uat_preflight.py`, `tests_offline/test_uat_preflight.py`, checker, permanent tests,
  localization manifest, freshness, vendor baseline, approved CSV, `ar.po`.
- Deltas `0c8057f..HEAD` are **plan markdown only**
  (`ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md`); no code/artifact drift after the target.

## 2. Preflight fail-closed fix at `0c8057f` — PASS

Diff introduces `sid = None` before the `try` so connection-failure cleanup cannot raise `UnboundLocalError`; cleanup remains unconditional in `finally` (logout on success **or** failure).

Offline coverage at this commit (`tests_offline/test_uat_preflight.py`): **5/5 OK**

- `test_connection_exception_records_failure_without_traceback`
- `test_attested_request_uses_configured_port` (`--port` routing, e.g. `8002`)
- `test_main_posts_login_request` (POST login)
- `test_full_process_empty_stdin_exits_1`
- `test_no_password_from_empty_stdin_direct`

Live smoke: simulated drop → `FAIL connection: … RemoteDisconnected` (clean, no traceback); `/ping`, desk boot ar, `__messages` → `UAT PREFLIGHT: PASS`.

## 3. Report / pilot tests — PASS

| Module | Result |
|---|---|
| `construction.tests.test_stage7_bilingual_reports` | **9/9 OK** |
| `construction.tests.test_stage4_report_extension` | **11/11 OK** |
| Offline preflight suite | **5/5 OK** |

## 4. Localization gates & permanent suite — PASS

| Check | Result |
|---|---|
| Bootstrap full gate (`STAGE2_EVIDENCE_BOOTSTRAP=1 --skip-evidence`) | `errors=0` |
| Standalone permanent suite `test_localization_gates.py` | **91/91 OK** |
| Scope lint | PASS |
| Translation-write lint | PASS |
| `git diff --check` | clean |

Evidence-inclusive gate residual (expected, not a bundle defect): `evidence-index-head` only — index `CANDIDATE_HEAD=80787af…` (generation HEAD pre-commit of `0433497`) vs live worktree HEAD `453d193`. Established re-pin pattern; all other evidence checks green when that HEAD row is excluded.

## 5. Governed Stage-2 evidence bundle — PASS

Index: `docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/index.txt`  
SHA-256: `8f9ca5dbe46c5937759ee147889ef219e1d5ab6728ec6734ec97af3d42f7d2ff`  
`CANDIDATE_HEAD`: `80787af65178f21a1205d91542e3025f12045b50`

### Envelopes (all EXIT_CODE 0; hashes match index)

| Envelope | SHA-256 |
|---|---|
| `all-tests.txt` | `ee17123c633457e47f64af08258689ce105aa38564d735ad485e43908f4f8a1d` |
| `final-dryrun.txt` | `74fd206007a6fe3b221015acb618aa7aa41a92fff1ded76599c119b71a54fa6e` |
| `freshness-envelope.txt` | `19d35cf8b961849f64f89f034d8420e2e23da7f52c69d32f583b4c7106205037` |
| `full-gate.txt` | `f4e894decd15fb91f599ad1009b6461a491c1af86b37645f12001f6941ce91a1` |
| `gate-tests-standalone.txt` | `190c42d929d1e0e960515c82f2122021f913e8caf09f79944bd6655bdd079038` |
| `lints-diffcheck.txt` | `96f8ede2627f8a500780984187e434b793aa8c7584503767fe002f34e225701f` |
| `merkle.txt` | `6c6f7999c7f9d8a5692ac4de174fe6337659e037336317bfedcdc3cb15a9f891` |
| `scoped-gate.txt` | `b424d74465d3c176d45f8c61dd1f9dfba471531ee29c4dc6050f96c812f9dee8` |
| `sync.txt` | `0051c2ff0cb2fa3941d2a87cc5dbeb1d8623f73cbebf52303cbf263005abfeea` |
| `vendor-audit.txt` | `f55b8f07acf12ea5763e6e377125b27c50b6cbd1242d487568e11fc4063eefe5` |

### Governed artifact hashes (index ↔ live — all OK)

| Marker | SHA-256 |
|---|---|
| `CHECKER_SHA256` | `3c308577fb3ad64e40cde4e6f2481d2945b9db6d81e48dee29c732c8c0d79de6` |
| `TESTS_SHA256` | `ad0c96f8eb61bc77d495eb034ccbac417aeb87129aca382d6da9d953a90d0753` |
| `PO_SHA256` | `28362a98f1e1d4e9f5dee0a04945abe88154b29ff12d9e57ba738c98427d3812` |
| `CSV_SHA256` | `4b3f0c9f98bb36a4c93407f8778ba952309369d3a41b57b419ff385168fe55d5` |
| `MANIFEST_SHA256` | `665d649a27fe92ec727db2de8e51d7bb23796f67ee147069d7941036ff58c997` |
| `BASELINE_SHA256` | `4d2d1cdda101ac059925dec698623c871d1d0e83e59d0428fe369f4c038441e3` |
| `DECISIONS_SHA256` | `73e1ec947246c5832aadfcac4a05a98d20f0baeb51d2866b20bda3767e5d4209` |
| `INVENTORY_MANIFEST_SHA256` | `5300fe41a8b6ff6bef82215edfddc3e99164b727d38283bed6d2f1e783c7e2a9` |
| `FRESHNESS_SHA256` | `b9c900ef1d82225ebb835f9ac6d4898faa755f6b6f74373832862b6223acc834` |
| `SQL_SHA256` | `a32e37ba09d292c74071965dfedd01680ee62582717e27012703665adc6b7d3f` |
| `SCOPELINT_SHA256` | `8436fed02c0dc5bc0c9f1f3abcf716cdbcbad68e28eb0db575535ad3e0e068c9` |
| `TRANSLATIONLINT_SHA256` | `c81321a0d35e42cfbb56b2e724c7a782555e0fc1e545b0631022ed15efe79031` |

### Migration / release set (recorded envelope facts)

- Module sum **270** tests, 11× `OK` (`all-tests.txt`); standalone **91 OK**.
- DRY: `total=450 created=0 updated=0 skipped=450 drift=0`.
- SYNC: `created=0 updated=0 dry_run=False`.
- Full gate / scoped / vendor: `errors=0`; scoped SKIPs only for governed markup blobs.
- Freshness: `critical_pass=true`, `packaged_rows=450`, `runtime_digest=67669439a898…`, `inputs.payload_csv_sha` = live CSV `4b3f0c9f…`, `inputs.construction_po_sha` = live PO `28362a98…`, merkle root `2e284695…` rows `18446`.

## 6. Rollback / restore rehearsal evidence — PASS

- File: `docs/ai/work-items/scope-context-portability/evidence/stage8-restore-rehearsal-drill-2026-09-22.md`
- SHA-256: `8d5f06d992545ca33c28386611e7e755e22ea4f440618dab85d5c62d3cf48a3a`
- Scope: isolated restore to `v16rehearsal.localhost` only; source `v16.localhost` not overwritten; preflight PASS; ar-Desk browser drill PASS (AR 5 / GL 14). Production untouched.

## AI-R verdict

**PASS — production-readiness evidence for exact commit `0c8057f`.**

This is **evidence/commit sign-off only**. It does **not** authorize production mutation.

## Remaining sequence (owner)

| Step | Requirement | Status |
|---|---|---|
| 1 | **AI-R verifies exact commit `0c8057f`** | ✅ **PASS (this record)** |
| 2 | Real production master/ledger data provided | ⛔ outstanding |
| 3 | Explicit authorization naming **production site** + **rollout window** | ⛔ outstanding |

Until steps 2 and 3: **production untouched; W6-0b deferred.**
