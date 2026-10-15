# F13 — Dependency and security remediation: runtime manifest (installed 16.51.1/16.50.0)

**Date:** 12–13 October 2026
**Candidate:** construction `1e46488` · frappe `2871914` (16.51.1) · erpnext `7474d9e` (16.50.0)
**Program:** [Master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [Work register](construction_foundation_work_register_2026-10-12.md) · [F25 review](construction_foundation_runtime_asset_consistency_review_2026-10-12.md)
**Status:** F13 **Engineering verified** (advisory review + compatible upgrades + functional proof on the installed runtime). Remaining: recurring advisory monitoring; CI realignment to the new vendor (F35).
**Classification:** Confidential — internal

## 1. Supported runtime matrix (this is the qualified set)

| Component | Version | Source |
|---|---|---|
| Python | 3.14.5 | bench venv |
| Frappe | 16.51.1 (`2871914`, clean checkout, vendor edit reverted) | `bench version` + `git log` |
| ERPNext | 16.50.0 (`7474d9e`, clean) | `bench version` + `git log` |
| Construction | `1e46488` (develop) | `bench version` + `git log` |
| MariaDB | 10.11.14 | dump header |
| Redis | cache :13000, queue :11000 (running) | common config + process list |
| Node | per CI Node 24 (assets built 2026-10-13) | CI config + build log |

Construction's five dependency ranges are all satisfied in the installed env: cryptography 50.0.2, pyOpenSSL 26.4.0, Pillow 12.3.0, sqlparse 0.6.0, sql_metadata 3.0.1 (F25-D001 resolved in the update-vendor direction).

## 2. Advisory review (pip-audit, isolated tooling, 2026-10-13)

Initial scan flagged 17 packages. Disposition:

| Package | Was → Now | Basis |
|---|---|---|
| gitpython 3.1.50 → **3.1.60** | ~30 advisories incl. RCE/file-read chains | Bench-tooling-only route (no customer endpoint forwards git options); upgraded anyway (patch-level) |
| bleach 6.3.0 → **6.4.0** | HTML sanitizer advisories | **Customer-reachable** (rich-text sanitization); upgraded |
| werkzeug 3.1.6 → **3.1.9** | WSGI advisories | **Customer-reachable** (every request); upgraded — **deviates from Frappe `==3.1.6` pin** (see §3) |
| starlette 1.2.0 → **1.3.1** | ASGI advisories | Realtime stack; upgraded |
| python-multipart 0.0.29 → **0.0.31** | upload parsing advisories | **Customer-reachable** (file uploads incl. BOQ Excel); upgraded |
| pyjwt 2.13.0 → **2.15.0** | JWT advisories | Auth-token path; upgraded |
| pypdf 6.15.0 → **6.19.0** | PDF advisories | Upgraded — **deviates from Frappe `==6.15.0` pin** (see §3) |
| weasyprint 68.0 → **70.0** | PDF advisories | **Customer-reachable** (print/PDF); upgraded — **deviates from Frappe `==68.0` pin** (see §3) |
| httplib2, anyio, mcp, pydantic-settings, pyasn1, soupsieve, virtualenv | patch/minor bumps | Transitive/bench-tooling; upgraded |
| oauthlib 3.3.1 | **CONTAINED, not upgraded** | Frappe pins `oauthlib~=3.3.1`; 4.0.0 is a major bump that would break Frappe. No OAuth/social-login route is configured on the UAT site (no keys); production enablement requires re-review. |
| pdfkit 1.0.0 | **CONTAINED, no fix exists** | pip-audit lists no fixed version. Compensating control verified in source: Frappe's `FrappePDFKit` (`frappe/utils/pdf.py:40-52`) strips meta-tag option injection (the PYSEC-2026-2860 vector); only explicitly-passed options reach wkhtmltopdf. |

Post-remediation pip-audit: clean except the two contained items above.

## 3. Pin deviations (must be re-applied after any Frappe reinstall)

Frappe 16.51.1 declares exact pins that conflict with the remediated set. The following are **intentionally held above Frappe's pins**, with functional proof on this exact runtime:

| Package | Frappe pin | Held version | Proof |
|---|---|---|---|
| Werkzeug | `==3.1.6` | **3.1.9** | Real HTTP serving verified (200 + login page + auth-boundary denial) |
| pypdf | `==6.15.0` | **6.19.0** | Direct PDF parse verified (1 page from weasyprint output) |
| WeasyPrint | `==68.0` | **70.0** | Direct PDF generation verified (5,065 bytes, valid `%PDF-1.7`) |

**Warning:** running `pip install -e apps/frappe` will silently downgrade these three to Frappe's pins. Any environment rebuild must re-apply the held versions and re-verify. F35's CI mapping must record this set, not Frappe's pins alone.

Metadata note (F25-D003 family): installed `construction` egg-info reports 0.0.1 while the app declares 0.0.5 — stale install metadata from an older `pip install -e`; harmless for runtime, to be reconciled under the canonical build policy.

## 4. Functional verification on the remediated runtime

- `bench version`: all three apps report expected versions.
- Site `v16rehearsal.localhost`: pong; HTTP 200 with login title; unauthenticated API correctly denied (PermissionError).
- PDF path: weasyprint + pypdf direct test passes.
- `pip check`: clean except unrelated virtualenv/filelock nit.
- BOQ data unchanged through upgrade + sidebar fix + remediation (23/34/213/34).

## 5. Remaining F13/F35 obligations

- Recurring advisory monitoring (no schedule established by this task — propose monthly or per vendor bump).
- CI realignment: business CI still pins frappe `81aadb9`/erpnext `2807c9f` (16.18.x); F35 must map the new 16.51.1/16.50.0 runtime and re-run.
- oauthlib/pdfkit containment holds only while their conditions hold (no OAuth route; Frappe wrapper intact) — re-check on every vendor bump.
- Vendor must stay clean (`git diff` empty on all three apps — verified 2026-10-13); any future vendor edit repeats the ENV-D001 disposition.

No site data was modified by this task beyond the F02 re-baseline restore test. No commit or push.
