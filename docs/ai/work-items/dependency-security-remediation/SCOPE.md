# Scope Descriptor — dependency-security-remediation (G10)

**Work item:** `dependency-security-remediation`
**Branch:** `opencode/session-3a-security`
**Worktree:** `/home/mohamed/frappe-bench/worktrees/session-3a-security`
**Date:** 2026-10-06
**Authority:** Session 3A per `OPENCODE_PARALLEL_EXECUTION_MASTER.md` + `BRIEFING_DEPENDENCY_SECURITY_REMEDIATION.md`

## 1. Objective

Remediate solvable dependency security advisories within official Frappe/ERPNext
version-16 compatibility constraints and add application-level compensating
controls for unfixable upstream packages (PDF rendering, SVG uploads, SSRF
boundaries, Bleach/HTML sanitization).

## 2. Dependency matrix (before → target)

| Package | Live env (before) | Target (Frappe v16.36.1) | Advisory outcome |
|---|---|---|---|
| cryptography | 46.0.7 | ~=50.0.0 | Clears 4 GHSA ranges |
| pyOpenSSL | 26.0.0 | ~=26.4.0 | Coordinated with cryptography 50 |
| Pillow | 12.2.0 | ~=12.3.0 | Clears 13 reviewed advisories |
| sqlparse | 0.5.5 | ~=0.6.0 | Clears 5 advisories |
| sql_metadata | 2.19.0 | ~=3.0.1 | Paired with sqlparse 0.6 |
| PyJWT | 2.12.1 | ~=2.13.0 partial | 9 later fixes remain blocked |
| pypdf | 6.10.2 | ==6.15.0 partial | 11 fixes require upstream change |
| WeasyPrint | 68.0 | ==68.0 (SSRF fix 70.0 blocked) | Compensating controls |
| pdfkit | 1.0.0 | ~=1.0.0 (no patch) | Compensating controls |
| bleach | 6.3.0 | 6.4.0 not pinned by Frappe | Verification via sanitize_rich_text |
| oauthlib | 3.3.1 | fix 4.0.0 blocked | Documented residual |

## 3. Reconciliation against the 70/108 GHSA identities

Full per-identity listing in `evidence/dependency-reconciliation.log`
(generated from `ADVISORY_INVENTORY.json`, 108 scanner entries across 9
packages; the 70 unique GHSA identities are the deduped subset). Cryptography,
pyOpenSSL, Pillow and sqlparse/sql_metadata targets are metadata-permitted;
pdfkit, WeasyPrint, pdfkit SSRF, oauthlib 4.0 and 9 later PyJWT/pypdf fixes are
residual and covered by compensating controls or documented as blocked upstream.

## 4. Compensating controls implemented

`construction/construction/utils/security.py` (shim re-export at
`construction/utils/security.py`):

- `validate_upload`: extension allowlist, 10 MiB cap, magic-byte sniffing (PDF/PNG/JPEG/SVG).
- `validate_pdf_page_limit`: 20 MiB cap, 200-page ceiling via pypdf before parsing.
- `sanitize_svg`: rejects `<script>`, event handler attributes, `javascript:`/`data:`
  URIs, external `href`/`src`, `<foreignObject>` and embed tags.
- `guard_ssrf`: blocks `file:`/`ftp:`/`gopher:`/`data:`/`javascript:` schemes,
  embedded credentials, loopback/private/link-local/reserved IPs, localhost/.local/.internal hosts.
- `enforce_local_asset_protocol`: blocks remote/file/data protocol-relative asset URLs and path traversal in print formats.
- `sanitize_rich_text` / `is_safe_rich_text`: Bleach allowlist verification for bilingual notes and print-format HTML.

## 5. Gate results

- `bench --site v16.localhost run-tests --module construction.tests.test_dependency_security_guards`: 33 tests, OK (`evidence/security-guards.log`).
- `lint_scope_metadata.py`, `ai_context_check.py`, `schema_drift_checker.py`, `lint_translation_writes.py`: all PASS (`evidence/gates.log`).
- `pip check`: 2 pre-existing frappe 16.18.1 metadata warnings (filelock, requests), unrelated to this change.

## 6. Residuals & follow-ups

- PyJWT 9 later fixes, pypdf 11 later fixes, oauthlib 4.0, WeasyPrint SSRF fix require coordinated upstream Frappe release upgrade; not force-overridden.
- Live bench env remains on Frappe 16.18.1 pins; target alignment recorded in `requirements.txt` for the next candidate build only.

## 7. Invariants honored

Zero push, hooks bypassed per-commit, zero edits to `apps/frappe`/`apps/erpnext`,
system Redis 6379 untouched, ephemeral Redis 11000/13000 used and torn down after
testing, no DB mutations (unit tests only), no `dump.rdb` committed.
