# P00/G0 MariaDB public-source provenance analysis — source-and-document-only, 2026-11-01

Verdict: **public-source chain VERIFIED at the assurance stated below for the recorded references; workstream gate remains BLOCKED.** This document records findings, limitations, unresolved questions and separated decisions from an authorized source-and-document-only provenance analysis. It is not acceptance of any artifact, evidence, custody, qualification or gate; it recommends no acceptance, catalog freeze, or execution grant. It does not verify the current target and does not authorize reliance on the historical baseline for a new operation. Target behavior, prior reviews and the historical runtime string remain unverified as stated.

Scope executed: (1) read-only comparison of `P00_G0_MARIADB_FEASIBILITY_REVIEW_DISPOSITION_REV_05_2026-10-31.md` against REV_04 and the applicable authorization record; (2) document-only inspection of the prior review thread's text as reported; (3) read-only retrieval of named authoritative upstream MariaDB and official distribution artifacts and signed descriptors for the exact recorded references; (4) verification of trust roots, reproducible retrieval records, independently recomputed digests and authenticated archive/descriptor chains; (5) semantic review of the recorded distribution patches and relevant upstream reference-source paths; (6) documentation of findings within this workstream. Exclusions observed in full: no target access of any kind; no target writes including rejected attempts; no identity collection; no incident-derived material; no custody acts; no unofficial mirrors, prebuilt binaries or target-derived artifacts; no provisioning, implementation, testing, qualification or deployment. Retrieval workspace: `/tmp/opencode/p00-g0-mariadb-provenance` (outside the repository). Tooling: curl, gpg/gpgv, sha256sum, tar, xz, python3. Record timestamp (UTC): 2026-10-31T23:09:48Z.

## 1. Evidence inventory (retrieval record)

All items retrieved over HTTPS from named authoritative channels; sizes are local byte counts; digests are local recomputations.

| # | Source (official channel) | Artifact | Bytes | Local SHA256 (prefix) |
|---|---|---|---|---|
| E1 | archive.ubuntu.com/ubuntu/pool/universe/m/mariadb/ | mariadb_10.11.14-0ubuntu0.24.04.1.dsc (PGP clearsigned) | 5,458 | f2812de13770d1bc5146e8fd4657b899fe0ae9e3dbc04171f96fb3bbdd12f837 |
| E2 | same pool | mariadb_10.11.14-0ubuntu0.24.04.1.debian.tar.xz | 263,916 | c6086b72136834b2247fb9a837e03ee2fbfa49615bb0422973d7f8f2384d1bd7 |
| E3 | same pool | mariadb_10.11.14.orig.tar.gz.asc (detached signature) | 833 | 63440758a8b9ced1ef3ec0e0947e6b060cc67c9919cd75a7386493016552b022 |
| E4 | downloads.mariadb.org/rest-api/mariadb/10.11.14/ (REST release record, HTTP 200) | release metadata incl. published checksums + detached PGP signature | ~JSON | — |
| E5 | downloads.mariadb.org/rest-api/…/mariadb-10.11.14.tar.gz (official download endpoint) | mariadb-10.11.14.tar.gz (upstream source tarball) | 112,475,645 | 8a571cb14fb1d4e3663d8e98f3d4200c042fc8b2a4aaaab495860dea8b7d052f |
| E6 | archive.ubuntu.com/ubuntu/dists/noble-updates/InRelease | signed archive metadata | — | signature verified (below) |
| E7 | archive.ubuntu.com/ubuntu/dists/noble-updates/universe/source/Sources.xz | signed source index | 532,712 | (chain-verified below) |
| E8 | archive.mariadb.org/PublicKey and /PublicKey_2010 | MariaDB signing keys (official key endpoints) | 6,575 / 14,928 | key material, fingerprints below |
| E9 | keyserver.ubuntu.com (Ubuntu-operated) | Ubuntu archive keys + .dsc signer key | — | fingerprints below |
| E10 | wiki.ubuntu.com/Security/SigningKeys, mariadb.com/kb/en/signing-keys/ | intended official fingerprint cross-statements (fetches returned no fingerprint text) | — | see limitations |

Workstream documents compared read-only: REV_04 sha256 `47ac07fe0a7addf59885605ebffe3e2cf7695f2d3dd28b29d034d76b3a3e5955`; REV_05 sha256 `9fc006b6fb6faefea74b8aabd025cdd5abc37b7a91f0a4f1ad68e79f43797df0`; diff = 4 changed line regions (1, 3, 18, 48), consistent with the two authorized wording items plus version bookkeeping.

## 2. Trust roots and signature verifications

- **Ubuntu archive metadata**: `InRelease` (noble-updates) — Good signature, "Ubuntu Archive Automatic Signing Key (2018) <ftpmaster@ubuntu.com>", fingerprint `F6ECB3762474EDA9D21B7022871920D1991BC93C`, key obtained from the Ubuntu-operated keyserver. Keyserver also yielded the 2012 archive key `40976EAF437D05B5`. Validity: good; trust level: `[unknown]` (no ownertrust assigned — validity only, by design).
- **`.dsc` descriptor**: Good signature from "Lena Voytek <lvoytek@ubuntu.com>", fingerprint `63EEFC3DE14D5146CE7F24BF34B8AD7D9529E793` (uids incl. @ubuntu.com/@debian.org), key from the Ubuntu-operated keyserver. Validity good; trust `[unknown]`.
- **Upstream tarball**: detached signature (E4/E3) verifies **Good** from "MariaDB Signing Key <signing-key@mariadb.org>", issuer fingerprint `177F4010FE56CA3336300305F1656F24C74CD1D8`; key material obtained from the official `archive.mariadb.org/PublicKey` endpoint over TLS. Validity good; trust `[unknown]`. The `PublicKey_2010` file additionally yielded "MariaDB Package Signing Key" `199369E5404BD5FC7D2FE43BCBCB082A1BB943DB`.
- **Cross-chain identity**: the `.asc` carried by Ubuntu (E3) is **byte-identical** to the detached signature published by MariaDB's official REST API — the same upstream signature crosses both chains.

## 3. Digest chain results (independently recomputed)

- E5 local SHA256 `8a571cb1…7d052f` == MariaDB REST published SHA256 == Ubuntu `.dsc`/`Sources` recorded SHA256 for `mariadb_10.11.14.orig.tar.gz`. **MATCH (3-way).**
- E5 local MD5 `7fddaba5…119f54` == REST published MD5 == `.dsc` Files MD5. **MATCH.**
- E2 local SHA256 == `.dsc` and `Sources` recorded value. **MATCH.**
- E3 local SHA256 == `.dsc` and `Sources` recorded value. **MATCH.**
- E1 local SHA256 == `Sources` stanza recorded value. **MATCH.**
- Authenticated chain: signed `InRelease` → `Sources.xz` (noble-updates universe) → `.dsc` → orig tarball + signature + debian tarball, all locally digested and matched; upstream side independently published and signed by the MariaDB Signing Key.

## 4. Exact matching against the recorded references

- Numeric core **`10.11.14`**: exact match in upstream release record ("MariaDB Server 10.11.14", release date 2025-08-06), tarball name, and distribution version.
- Distribution `Version:` field is `1:10.11.14-0ubuntu0.24.04.1`. The leading `1:` is a Debian epoch (standard version grammar), not a version change; epoch-stripped value `10.11.14-0ubuntu0.24.04.1` equals the recorded package suffix **exactly** → suffix is **recognized** (the changed/unrecognized-suffix → UNKNOWN rule is untouched and not triggered here).
- Accepted historical full reference `10.11.14-MariaDB-0ubuntu0.24.04.1` is the historically recorded server-reported string; the string's runtime form was **not** compared to anything under this scope (no target access). It is neither re-verified nor altered.

## 5. Distribution patch semantic review (E2 contents)

`debian/patches/series` — exactly 4 patches; each inspected:

1. `env-perl-usr-bin-perl.patch` — perl shebang paths in test scripts and `mytop.sh` (packaging portability; forwarded to upstream PR #1718).
2. `install-files-into-usr.patch` — cmake install layout for PAM modules/systemd units into `/usr`.
3. `MDEV-37411-suppress-new-warning-about-native-aio.patch` — one-line change in `storage/innobase/os/os0file.cc:3091` downgrading `sql_print_warning` → `sql_print_information` for the native-AIO fallback notice (log severity only; forwarded to JIRA).
4. `mroonga-mrn-lib-dirs-path-reproducible-build.patch` — mroonga `CMakeLists.txt` reproducible-build paths.

`debian/changelog` head: `1:10.11.14-0ubuntu0.24.04.1` in `noble` — "New upstream maintenance release 10.11.14" (LP #2120204), routine update; prior entry `1:10.11.13-0ubuntu0.24.04.1` was the noble-security update. **Finding: the distribution delta alters no read-only, transaction-visibility, privilege or status semantics; the only engine-source touch is a log-severity downgrade.**

## 6. Upstream reference-source review (E5 members; paths are within the 10.11.14 tarball)

- **D3 predicate (statement-level denial)**: `sql/sql_parse.cc:3696-3703` calls `deny_updates_if_read_only_option(thd, all_tables)` and raises `ER_OPTION_PREVENTS_STATEMENT "--read-only"`. Helper at `sql/sql_parse.cc:1473-1512`: denial requires `opt_readonly`; applies only to commands with `CF_CHANGES_DATA`; exempts `PRIV_IGNORE_READ_ONLY`; special-cases `CREATE`/`DROP` temporary and database changes; final gate is `some_non_temp_table_to_be_updated`. Second guard at `sql/sql_parse.cc:4541-4547` (same pattern). Read-only enforcement is therefore a **server-side, statement+table-scope error path** — rejected attempts still execute server logic, consistent with the disposition's rule that rejected attempts are prohibited events, not evidence.
- **D4 predicate (temporary-table exemption)**: `sql/sql_parse.cc:406-414` — `some_non_temp_table_to_be_updated` skips tables with a temporary share (`!thd->find_tmp_table_share(table)`); `sql/sys_vars.cc:3167-3174` — `read_only` doc: "Make all non-temporary tables read-only, with the exception for replication (slave) threads and users with the 'READ ONLY ADMIN' privilege"; `sql/privilege.h:393` — `PRIV_IGNORE_READ_ONLY = READ_ONLY_ADMIN_ACL`. Source-confirmed: temporary-table DML is exempt by design.
- **D5 predicate (cache skips not-started transactions; own-transaction timing)**: `storage/innobase/trx/trx0i_s.cc:1046-1062` — `fetch_data_into_cache` clears and refills the cache by iterating `trx_sys.trx_list` while **skipping `TRX_STATE_NOT_STARTED` transactions** (and the purge query's trx); `storage/innobase/handler/i_s.cc:363-396` — `fill_innodb_trx_from_cache` reads from `trx_i_s_cache`, populated at a point in time. Source-confirmed: the witness candidate `INNODB_TRX` never shows not-started transactions and its view of the calling session's own transaction depends on cache refresh timing.
- **D6 predicate (InnoDB flag ≠ SQL READ ONLY)**: `storage/innobase/handler/ha_innodb.cc:19795-19798` — `innodb_read_only` is `MYSQL_SYSVAR_BOOL(read_only, srv_read_only_mode, PLUGIN_VAR_OPCMDARG | PLUGIN_VAR_READONLY, "Start InnoDB in read only mode (off by default)")`: a **startup-only engine mode flag** bound to `srv_read_only_mode`, distinct from the server `read_only` system variable (`sql/sys_vars.cc:3167`, global with check/update hooks). `super_read_only` does not exist anywhere under `sql/` (0 occurrences). Source-confirmed: the two flags are separate mechanisms; neither is a per-transaction session witness.
- **D7 predicate (global PROCESS check)**: `sql/sql_parse.cc:4226-4231` — `SQLCOM_SHOW_ENGINE_STATUS` performs `check_global_access(thd, PRIV_STMT_SHOW_ENGINE_STATUS)`; `sql/privilege.h:643` — `PRIV_STMT_SHOW_ENGINE_STATUS = PROCESS_ACL`. Source-confirmed: a **global** privilege gate exists upstream (no grant was sought, held or used here; a separate `PROCESS_ACL` hit at `sql_parse.cc:9464` belongs to the KILL path and is recorded only to prevent misattribution).

These are source-level observations about upstream 10.11.14 code only. They are not runtime findings, not target evidence, and do not establish that any candidate witness qualifies.

## 7. Document-only items

- **REV_05 vs REV_04 vs authorization record**: 4 changed line regions (title; revision record; D8 term; conjunct term) — matches the two authorized wording items plus bookkeeping (digests §1). Conformance noted: REV_05's "minimum next authorization" describes provenance analysis within the disposition's scope boundary; the executed scope here is that description as granted by the present authorization record (in-thread), not a broader one.
- **Prior review thread text (as reported only)**: the in-thread records report a DeepSeek V4.1 Flash document-only review of `P00_G0_MARIADB_101114_SOURCE_FEASIBILITY_REV_01_2026-10-31.md`, first run interrupted after D1–D7, continuation supplying D8–D14, followed by document-only rechecks of dispositions. Inspection was limited to this reported text; the transcripts, reviewer identity and qualifications were **not** independently obtained or verified in this round.

## 8. Verified items

1. Existence, exact version and digest identity of the public artifacts for numeric core `10.11.14` and package version `1:10.11.14-0ubuntu0.24.04.1` (suffix recognized, epoch explained).
2. Three-way digest agreement (local recompute ↔ MariaDB official published ↔ Ubuntu signed `.dsc`/`Sources`) for the source tarball; local↔signed-record agreement for `.dsc`, `debian.tar.xz`, `.asc`.
3. Signature validity: upstream tarball signature Good (MariaDB Signing Key via official key endpoint); `.dsc` Good (Ubuntu developer key); Ubuntu `InRelease` Good (Ubuntu Archive key). Validity good; no trust-owner flags assigned.
4. Byte-identity of the upstream detached signature with the copy carried in the Ubuntu source package.
5. Distribution patch set: 4 patches, semantics as classified; no read-only/transaction/privilege/status semantics altered.
6. Source predicates for D3, D4, D5, D6 and D7 as itemized in §6, at the cited paths in upstream 10.11.14.
7. REV_05↔REV_04 difference scope (4 regions) as recorded.

## 9. Unverified items

- Prior review transcripts, reviewer identity/qualifications, and any claim from the reported thread runs (reported only).
- The current target: identity, build, runtime server string, and any comparison of the historical full reference against a live server (excluded by authorization).
- The owner handoff record of the historical baseline acceptance (reported, not independently obtained).
- Source links and citations inside the earlier feasibility document (not followed).
- Any statement about incident-exclusion completeness or contamination (excluded material).
- Trust-owner assignment for all keys (validity only, by design of this round).
- Build provenance of the Ubuntu binary packages (not in scope; source chain only).

## 10. Unresolved questions

1. **Key fingerprint cross-publication**: no second official statement page carrying the MariaDB signing-key fingerprint was located this round (fetched KB/wiki pages returned no fingerprint text). Assurance currently rests on the official endpoint + TLS + uid binding. Required evidence: an official page or project key-transparency statement publishing `177F4010FE56CA3336300305F1656F24C74CD1D8`, or a documented second-channel confirmation.
2. **Witness design**: source review confirms the timing/visibility limitations of `INNODB_TRX` (D5) and the disjointness of `read_only` vs `innodb_read_only` (D6); whether any compliant non-mutating, per-transaction witness exists remains open and would require further authorized source analysis before any candidate is proposed.
3. **Fingerprint cross-statement for the Ubuntu archive keys** via wiki (page content not machine-readable as fetched) — same class as (1), lower materiality given InRelease verification passed with the Ubuntu-operated keyserver key.
4. **Point-in-time nature**: pool/index contents and patch sets can change; this record fixes state only as of its timestamp.
5. Whether upstream publishes signed build-provenance material for 10.11.14 sufficient for the disposition's build-provenance plan requirement.

## 11. Separated decisions (none decided here)

**Business/owner decisions**: designation of the acceptance authority and protected evidence destination; any compatible custody-acceptance process and external-human-acceptor selection; any change to the no-independent-human-adjudicator rule; any amendment to retention or the owner-approved historical weaker-assurance baseline (restating requires no new decision; changing does); whether this analysis is accepted as an input to further work (no recommendation made).

**Authorization decisions (none granted here)**: any second-channel fingerprint-confirmation retrieval beyond channels already named; any deeper/extended upstream source review scope; any sanitized incident-manifest review scope; any named-environment disposable-control scope; any target, credential, custody, administrative, privilege, provisioning, testing, qualification or deployment scope; any acceptance, catalog-freeze or execution authority.

## 12. Minimum next authorization

A source-and-document-only continuation limited to: (a) confirming the MariaDB signing-key fingerprint from one further named official statement channel of the upstream project, and (b) extended semantic review of additional upstream 10.11.14 reference-source paths bearing on a non-mutating per-transaction witness (statement visibility, binlog/read-only interactions), plus (c) documentation of findings in this workstream — under the same exclusions as this round (no target access of any kind, no target writes, no identity collection, no incident-derived material, no custody acts, no unofficial mirrors/prebuilt binaries/target-derived artifacts, no provisioning, implementation, testing, qualification or deployment). This is a scope description only: it grants nothing, recommends no acceptance, catalog freeze, or execution grant, and does not authorize reliance on the historical baseline for any new operation.

P00/G0, H01 and H02 remain open; P1 deferred; P2 implementation, disposable-lab provisioning and native testing paused.
