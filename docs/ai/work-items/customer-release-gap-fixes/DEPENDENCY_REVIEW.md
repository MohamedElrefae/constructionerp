# Candidate dependency review

2026-10-05. The candidate runtime is private to the disposable release bench. The shared Bench environment and vendor source were preserved. This review does not approve a deployment or declare the app secure.

## Reproducibility and constraints

Frappe source: `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0` (16.18.1); ERPNext: `2807c9f08fff3f161c0a2e10745a26aa6331ffd5`. Runtime: Python 3.14.5, Node 24.15.0, MariaDB 10.11.14, Redis 7.0.15, wkhtmltopdf 0.12.6. These are observed versions, not an approved customer matrix.

A separate `candidate-env` was created and populated by copying the shared installed packages, without hardlinks. Shared filelock/requests constraint conflicts were corrected there. Development-only virtualenv/pre-commit were removed from this copied runtime because their newer filelock requirement conflicted with Frappe; build tools need a separate environment. Candidate `pip check` passes. The source app version is 0.0.5; stale installed construction distribution metadata 0.0.1 is not the release version.

[CANDIDATE_PYTHON_INVENTORY.json](CANDIDATE_PYTHON_INVENTORY.json) records the installed graph. [CANDIDATE_PUBLIC_REQUIREMENTS.txt](CANDIDATE_PUBLIC_REQUIREMENTS.txt) pins 177 public distributions for inventory/audit, excluding the three local source apps. **Neither file is a clean rebuild lock**: artifact hashes, platform/native packages and a fresh resolver/build/asset/install run still need qualification. CI's moving vendor branches and tool/image tags also remain reproducibility work.

## Security audit result

The scanner received public names/versions only. Its initial run reported 180 advisory entries in 22 packages. Thirteen updates compatible with the installed constraints were applied in the isolated runtime: anyio 4.14.2, filelock 3.20.3, GitPython 3.1.60, httplib2 0.32.0, mcp 1.28.1, pip 26.2, pyasn1 0.6.4, pydantic-settings 2.14.2, python-multipart 0.0.31, RestrictedPython 8.4, soupsieve 2.9, starlette 1.3.1 and urllib3 2.8.0. The final selected 219 Python tests and native HTTP checks ran in that updated environment.

The repeated scanner exited 1 because findings remain: **108 advisory entries across nine packages**. Some identifiers/aliases occur more than once. This is an installed-package signal, not 108 distinct exploitable Construction defects. An empty reported fix list means this scanner supplied no fix for that entry, even if another entry for the same package has one. [Machine-readable identifiers and fixes](ADVISORY_INVENTORY.json).

| Package | Installed | Entries | Highest reported fix | Why not blindly upgraded |
| --- | --- | ---: | --- | --- |
| bleach | 6.3.0 | 3 | 6.4.0 | Frappe requires `~=6.3.0`; some entries have no fix. |
| cryptography | 46.0.7 | 7 | 50.0.0 | Frappe `~=46.0.3`; pyOpenSSL also requires `<47`. |
| oauthlib | 3.3.1 | 1 | 4.0.0 | Frappe requires `~=3.3.1`. |
| pdfkit | 1.0.0 | 2 | None reported | Requires advisory applicability/mitigation and vendor PDF-path review. |
| pillow | 12.2.0 | 25 | 12.3.0 | Frappe requires `~=12.2.0`. |
| pyjwt | 2.12.1 | 17 | 2.15.0 | Frappe requires `~=2.12.1`; some entries have no fix. |
| pypdf | 6.10.2 | 41 | 6.19.0 | Frappe pins `==6.10.2`. |
| sqlparse | 0.5.5 | 9 | 0.6.0 | Frappe `~=0.5.5`; sql-metadata requires `<0.6.0`. |
| weasyprint | 68.0 | 3 | 70.0 | Frappe pins `==68.0`; some entries have no fix. |

No framework requirement was bypassed to produce a cosmetic zero-findings scan. Qualification must inspect each relevant advisory's affected behavior, deduplicate aliases, assess enabled routes/untrusted inputs, then select a compatible supported Frappe/ERPNext/dependency candidate or explicit effective mitigation. Rebuild in isolation, run affected security/business/import/PDF/authentication checks, and rescan. Changing financial app code cannot close a vendor constraint blocker by itself.

The JavaScript test lockfile audit reports zero advisories. That covers the **test tooling graph only**. Production framework/ERPNext/Construction assets, OS/native packages, actual deployments, global overrides, browser/role coverage and independent qualified review remain outside this result. Do not advertise dependency security clearance or customer readiness until those gates are met.

Raw scanner logs/results and the local constraint triage remain in the private release bench logs. TESTED_FILES.json binds their hashes and the public summaries; private site configuration, backups, credentials and customer records are excluded.
