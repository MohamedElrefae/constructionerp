# F02 — Isolated environment and baseline recovery: UAT manifest

**Date:** 12 October 2026
**Site:** v16rehearsal.localhost
**URL:** http://v16rehearsal.localhost:8000/
**Program:** [Master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [Work register](construction_foundation_work_register_2026-10-12.md)
**Status:** Baseline backup + tested restore complete; site healthy. F02 **In progress** pending F13 runtime alignment before any app-code installation.

## 1. Environment identity

| Field | Value |
|---|---|
| Site | v16rehearsal.localhost |
| URL | http://v16rehearsal.localhost:8000/ |
| Database | MariaDB 10.11.14, name `_8ea0ca5beb7e4d87` |
| Apps (bench list-apps) | frappe `15.x.x-develop` @ `81aadb9` (develop) · erpnext `16.18.3` (version-16) · construction `0.0.5` (develop) |
| App source | `/home/mohamed/frappe-bench/apps/construction` @ `c9e6803c` (shared checkout) |
| Site files | private 4.2 MB, public 404 KB |
| Web server | gunicorn on :8000; redis_cache :13000, redis_queue :11000 |

**Isolation note:** this site shares the app checkout with `localhost`, `v16.localhost` and two auxiliary sites. No shared-site upgrade will occur implicitly; the site is treated as disposable UAT infrastructure. F13 must resolve the runtime constraint conflict (F25-D001) before any app-code installation or migration.

## 2. Pre-work data inventory (read-only, before any change)

| Table | Count |
|---|---|
| BOQ Header | 23 |
| BOQ Item | 34 |
| BOQ Cost Analysis | 0 |
| BOQ Quantity Revision | 213 |
| Variation Order | 34 |
| User | 31 |
| Company | 21 |

The site carries rehearsal data from the 2026-09/10 upgrade rehearsal, including owner-classified test remnants (orphan approved revisions and test VOs). F04 fixtures must account for or explicitly exclude these; they are not customer data.

## 3. Baseline backup

| Field | Value |
|---|---|
| Backup ID | `20261013_003600-v16rehearsal_localhost` |
| Location | `sites/v16rehearsal.localhost/private/backups/` |
| Contents | database.sql.gz (64.7 MB) + public files.tar (390 KB) + private files.tar (4.1 MB) + site_config_backup.json |
| Taken | 2026-10-13 00:36 UTC |

## 4. Tested restoration path

| Step | Result |
|---|---|
| Restore method | dump piped into site's own database via site DB user (full privileges on own DB; no root required) |
| Tables in dump | 774 (all with DROP TABLE IF EXISTS) |
| Post-restore counts | BOQ Header 23 · BOQ Item 34 · Cost Analysis 0 · Revisions 213 · VO 34 · User 31 · Company 21 — **all match pre-restore inventory** |
| Site health after restore | HTTP 200 on /; bench services running (redis, gunicorn) |

The restoration path is tested and proven. A full `bench restore` with root credentials remains available as an alternative path.

## 5. Outbound integrations — sandboxed

| Email account | Outgoing | SMTP |
|---|---|---|
| test@example.com | enabled | smtp.example.com (test server) |
| mohamedelrefae81@gmail.com | disabled | — |
| _test@test.com | disabled | smtp.test.com |

No real outbound email is possible from this site. No other outbound integrations (payment gateways, SMS, webhooks) are configured.

## 6. Known constraints

- **F25-D001 runtime conflict:** the app's five dependency ranges are disjoint from the CI-pinned vendor ranges. No `pip install` of the app or its dependencies may occur until F13 resolves this. The site currently runs the existing installed environment.
- **Shared checkout:** app-code changes made during foundation work will be visible to this site (it runs from the working tree). This is acceptable for UAT but means the site always reflects the current `develop` checkout state.
- **Rehearsal remnants:** the 213 revisions and 34 VOs include owner-classified test records. F04 must document which fixtures are net-new vs pre-existing.

## 7. F02 completion status

- [x] Isolated UAT target selected and recorded
- [x] All sites sharing code inventoried
- [x] Baseline backup with files
- [x] Tested restoration path (counts verified)
- [x] Outbound integrations sandboxed
- [x] Actual site/schema/assets recorded
- [ ] F13 runtime alignment before any app installation
- [ ] Ordinary-user login verification (site responds; formal login test with F04 roles)

F02 is **In progress**; the remaining items depend on F13 and F04 respectively.

## 8. Environment-change addendum (2026-10-13) — re-baseline required

**What changed:** the bench vendor moved under this site (frappe `81aadb9`/16.18.1 → `2871914`/16.51.1; erpnext `2807c9f`/16.18.3 → `7474d9e`/16.50.0), the bench environment was reinstalled, and `v16rehearsal.localhost` was migrated — all outside F02's change control ("no shared-site upgrade occurs implicitly", §1). Construction moved `c9e6803c` → `1e46488`. The `§3` backup (`20261013_003600`) and `§4` restore test now describe the **pre-upgrade, pre-migration** state.

**What still holds:** site alive (pong); BOQ counts unchanged after migration (23/34/213/34) — the upgrade did not alter financial data; outbound integrations still sandboxed (not re-audited post-change — re-check on re-baseline).

**What is invalidated and owed:** the tested restoration path no longer matches the live site state. Before any foundation mutation on this site: take a **new baseline backup**, re-run the **restore test** against it, re-audit outbound integrations, and record the new vendor/app versions. F02 remains In progress and this manifest's §1–§7 stand as the pre-upgrade baseline, superseded for restore purposes. F13's runtime alignment (F25-D001) must now qualify the *installed* 16.51.1/16.50.0 runtime, not the CI-pinned 16.18.1/16.18.3.
