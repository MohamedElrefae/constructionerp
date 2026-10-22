# Session 3A Briefing — Dependency Security Remediation & Python Upgrade (G10)

## Authority & Operational Posture
- **Standing Policy:** Local execution only under `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`. Zero push to public remotes.
- **Transmitting Hooks:** Disabled per command (`git -c core.hooksPath=/dev/null ...`).
- **Vendor Code Invariant:** Strictly ZERO modifications to `apps/frappe` or `apps/erpnext`.
- **Role Division:** OpenCode implements and captures evidence in its isolated work-item directory; Antigravity verifies, audits, and commits.
- **Port Invariant:** Ephemeral Redis (11000/13000) started on-demand, torn down immediately after testing. Never touch port 6379 (system Redis). Never commit `dump.rdb`.

---

## 1. Objective & Scope
Remediate solvable dependency security advisories within official Frappe/ERPNext version-16 compatibility constraints (as detailed in `docs/ai/work-items/customer-release-gap-fixes/SECURITY_UPGRADE_PATH.md`), and add input sanitization / boundary guards in the Construction app for unfixable upstream packages (PDF rendering and SVG uploads).

### Target Upstream Package Alignment
1. **Cryptography & pyOpenSSL:** Align with Frappe v16.36.1 (`cryptography~=50.0.0`, `pyOpenSSL~=26.4.0`) to resolve 4 GHSA advisories.
2. **Pillow:** Align with `Pillow~=12.3.0` to resolve all 13 reviewed image-processing advisories.
3. **SQL Parser:** Align `sqlparse~=0.6.0` paired with `sql_metadata~=3.0.1` to resolve 5 parser advisories.
4. **Application-Level Compensating Controls:**
   - **PDF Processing (pypdf, WeasyPrint, pdfkit):** Add defensive server-side validation on user-uploaded VO attachments and print format generation (block SSRF, enforce local asset protocol, restrict file sizes and page limits).
   - **Bleach / HTML Sanitization:** Verify safe HTML handling in bilingual notes and custom print format fields.

---

## 2. Directory & Deliverables
Work in isolated directory:
`docs/ai/work-items/dependency-security-remediation/`

Deliverables required:
1. `SCOPE.md`: Authority, dependency matrix, reconciliation against the 70 GHSA identities, compensating controls, gate results.
2. `evidence/dependency-reconciliation.log`: Exact before/after version diff and scanner output against `ADVISORY_INVENTORY.json`.
3. `evidence/clean-build.log`: Output of `pip check` and dependency resolution proof.
4. `evidence/security-guards.log`: Unit test results exercising PDF upload validation, SSRF boundary guards, and SVG sanitization.
5. `evidence/gates.log`: Repository linters (`lint_scope_metadata.py`, `ai_context_check.py`, `schema_drift_checker.py`, `lint_translation_writes.py`).
6. `evidence/MANIFEST.json`: Self-verifying manifest pinning all evidence and modified files by SHA-256.

---

## 3. Allowed Code Modifications
- `pyproject.toml` (Construction app dependencies, if direct pins needed).
- `construction/utils/security.py` or `construction/services/file_security.py` (compensating guards for attachments/PDFs).
- `construction/tests/test_dependency_security_guards.py` (new tests verifying defenses).
- `docs/ai/work-items/dependency-security-remediation/*`.
- **Prohibited:** Editing `apps/frappe/`, `apps/erpnext/`, or touching operational DB records.

---

## 4. Verification & Handover
1. Run all security unit tests: `bench --site v16.localhost run-tests --module construction.tests.test_dependency_security_guards`.
2. Run standard linters (`python3 scripts/lint_scope_metadata.py`, `ai_context_check.py`, `schema_drift_checker.py`).
3. Compute SHA-256 digests and write `evidence/MANIFEST.json`.
4. Tear down ephemeral Redis (11000/13000). Leave working tree unstaged for Antigravity audit and commit.
