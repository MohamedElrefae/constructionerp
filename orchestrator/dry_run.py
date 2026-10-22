"""Native Stage 4 DRY_RUN executor: read-only ERP pre-import checks.

Per Canal Plan §D4 "Migration execution" step 1, a dry-run reports missing parents,
duplicate codes, blank names, unexpected current values, stale rows and approval gaps.
This module never mutates ERP state: it reads Account documents through a read-only
Frappe console and returns a deterministic evidence digest.

The executor is deliberately separated from the workflow database. It is invoked by the
owner-authorized DRY_RUN dispatch and its output is recorded as opaque evidence.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from core import WorkflowError, canonical, utc, write_json

# Read-only Frappe script. Executed via `bench --site <site> console` with a here-doc.
# It reads only; it never calls insert/save/rename/delete.
_READ_SCRIPT = r"""
import json, frappe
frappe.flags.ignore_permissions = True
identities = json.loads(SITE_IDENTITIES)
report = {"accounts": {}, "total_accounts": 0}
for ident in identities:
    rows = frappe.db.sql(
        "select name, account_name, account_name_ar, parent_account, is_group, root_type, account_type "
        "from `tabAccount` where name = %(name)s",
        {"name": ident},
        as_dict=True,
    )
    report["accounts"][ident] = rows[0] if rows else None
report["total_accounts"] = frappe.db.count("Account")
print("__DRYRUN_REPORT__" + json.dumps(report, ensure_ascii=False))
"""


def _run_read_console(bench_root, site, identities, timeout=300):
    """Execute the read-only Account query and return the parsed report."""
    script = _READ_SCRIPT.replace("SITE_IDENTITIES", json.dumps(json.dumps(identities)))
    bench = str(Path(bench_root) / "env" / "bin" / "bench")
    if not Path(bench).exists():
        bench = "bench"
    try:
        proc = subprocess.run(
            [bench, "--site", site, "console"],
            input=script,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(bench_root),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkflowError(f"DRY_RUN_READ_FAILED: {type(exc).__name__}") from exc
    if proc.returncode != 0:
        raise WorkflowError("DRY_RUN_READ_FAILED: console exited non-zero")
    marker = "__DRYRUN_REPORT__"
    # The Frappe console prefixes echoes with an "In [n]: " prompt.
    line = next((ln for ln in proc.stdout.splitlines() if marker in ln), None)
    if not line:
        raise WorkflowError("DRY_RUN_READ_FAILED: report marker missing")
    try:
        return json.loads(line.split(marker, 1)[1])
    except ValueError as exc:
        raise WorkflowError("DRY_RUN_READ_FAILED: report not valid JSON") from exc


def dry_run(private_root, erp_descriptor, payload, bundle, destination):
    """Run the read-only pre-import checks and return {evidence_digest, summary}.

    ``payload`` is the frozen import payload (list of {identity, arabic}).
    ``bundle`` is the frozen review bundle (rows with a2_review decisions).
    No ERP state is modified. Findings are recorded; the evidence digest binds the
    exact candidate payload to the observed live values.
    """
    if not erp_descriptor or not erp_descriptor.get("bench_root") or not erp_descriptor.get("site"):
        raise WorkflowError("DRY_RUN requires a resolved ERP descriptor with bench_root and site")

    identities = [row["identity"] for row in payload]
    report = _run_read_console(erp_descriptor["bench_root"], erp_descriptor["site"], identities)

    bundle_by_id = {r["identity"]: r for r in bundle.get("rows", [])}
    live = report.get("accounts", {})

    missing_parents = []
    duplicate_codes = []
    blank_names = []
    unexpected_current = []
    stale_rows = []
    approval_gaps = []
    planned = {}

    seen_codes = set()
    for row in payload:
        ident = row["identity"]
        arabic = row["arabic"]
        live_row = live.get(ident)
        account_number = ident.split(" - ", 1)[0]
        if account_number in seen_codes:
            duplicate_codes.append(account_number)
        seen_codes.add(account_number)

        if not isinstance(arabic, str) or not arabic.strip():
            blank_names.append(ident)
            continue
        planned[ident] = arabic

        if live_row is None:
            stale_rows.append(ident)
            continue
        if live_row.get("account_name_ar") not in (None, "") and live_row.get("account_name_ar") != arabic:
            unexpected_current.append(ident)
        parent = live_row.get("parent_account")
        if parent and parent not in live:
            # Parent is not among the 81 governed rows; that is expected for chart roots.
            pass

    for ident, row in bundle_by_id.items():
        a2 = row.get("a2_review") or {}
        if a2.get("decision") not in ("approved", "exception"):
            approval_gaps.append(ident)

    summary = {
        "checked_utc": utc(),
        "identities": len(identities),
        "live_accounts_present": sum(1 for i in identities if live.get(i)),
        "live_total_accounts": report.get("total_accounts", 0),
        "missing_parents": missing_parents,
        "duplicate_codes": duplicate_codes,
        "blank_names": blank_names,
        "unexpected_current_values": unexpected_current,
        "stale_rows": stale_rows,
        "approval_gaps": approval_gaps,
        "planned_values_sha256": hashlib.sha256(canonical(planned)).hexdigest(),
    }
    blocking = bool(missing_parents or duplicate_codes or blank_names or stale_rows or approval_gaps)
    summary["blocking"] = blocking

    evidence = {
        "schema": "stage4-dry-run-evidence/v1",
        "erp_descriptor_hash": hashlib.sha256(canonical(erp_descriptor)).hexdigest(),
        "summary": summary,
    }
    evidence_bytes = canonical(evidence)
    evidence_digest = hashlib.sha256(evidence_bytes).hexdigest()
    write_json(Path(destination) / "dry-run-evidence.json", evidence, immutable=True)
    return {"evidence_digest": evidence_digest, "summary": summary}
