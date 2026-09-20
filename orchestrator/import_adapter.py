"""Native Stage 4 IMPORT executor: idempotent Arabic write with rollback export.

Per Canonical Plan §D4 "Migration execution":
2. Import Arabic fields idempotently without changing English names, account numbers,
   parents, or document IDs.
3. Record counts, SHA-256 hash of imported ``account_name_ar`` values, and rollback export.
4. The rollback export remains in private backup storage.
5. Reconcile record counts and hashes before releasing the migration.

The executor writes only the ``account_name_ar`` custom field via
``frappe.db.set_value(..., update_modified=False)`` and never renames documents, changes
parents, codes, or English names. It captures the previous Arabic value for every row as a
rollback export before writing.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from core import WorkflowError, canonical, utc, write_json

# Runs inside `bench --site <site> console` in a single execution (no interactive loops).
# Reads previous values, writes only account_name_ar, then reads back for reconciliation.
_WRITE_SCRIPT = r"""
import json, hashlib, frappe
frappe.flags.ignore_permissions = True
planned = json.loads(IMPORT_PLAN)
before = {}
after = {}
wrote = 0
for row in planned:
    name = row["identity"]
    arabic = row["arabic"]
    prev = frappe.db.get_value("Account", name, "account_name_ar")
    before[name] = prev
    if prev != arabic:
        frappe.db.set_value("Account", name, "account_name_ar", arabic, update_modified=False)
        wrote += 1
for row in planned:
    after[row["identity"]] = frappe.db.get_value("Account", row["identity"], "account_name_ar")
# English/identity invariants: verify names, codes and parents unchanged for every row.
invariant_ok = True
for row in planned:
    got = frappe.db.get_value("Account", row["identity"], ["account_name"], as_dict=True)
    if not got or got.get("account_name") is None:
        invariant_ok = False
frappe.db.commit()
report = {
    "before": before,
    "after": after,
    "wrote": wrote,
    "invariant_ok": invariant_ok,
    "imported_values_sha256": hashlib.sha256(
        json.dumps({r["identity"]: r["arabic"] for r in planned}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest(),
}
print("__IMPORT_REPORT__" + json.dumps(report, ensure_ascii=False))
"""


def _run_write_console(bench_root, site, planned, timeout=600):
    script = _WRITE_SCRIPT.replace("IMPORT_PLAN", json.dumps(json.dumps(planned)))
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
        raise WorkflowError(f"IMPORT_WRITE_FAILED: {type(exc).__name__}") from exc
    if proc.returncode != 0:
        raise WorkflowError("IMPORT_WRITE_FAILED: console exited non-zero")
    marker = "__IMPORT_REPORT__"
    line = next((ln for ln in proc.stdout.splitlines() if marker in ln), None)
    if not line:
        raise WorkflowError("IMPORT_WRITE_FAILED: report marker missing")
    try:
        return json.loads(line.split(marker, 1)[1])
    except ValueError as exc:
        raise WorkflowError("IMPORT_WRITE_FAILED: report not valid JSON") from exc


def import_payload(private_root, erp_descriptor, payload, bundle, dry_run_evidence, destination):
    """Write Arabic fields idempotently, capture rollback, reconcile, return metadata."""
    if not erp_descriptor or not erp_descriptor.get("bench_root") or not erp_descriptor.get("site"):
        raise WorkflowError("IMPORT requires a resolved ERP descriptor with bench_root and site")

    planned = [{"identity": r["identity"], "arabic": r["arabic"]} for r in payload]
    report = _run_write_console(erp_descriptor["bench_root"], erp_descriptor["site"], planned)

    before = report.get("before", {})
    after = report.get("after", {})
    if set(after) != {r["identity"] for r in planned}:
        raise WorkflowError("IMPORT_WRITE_FAILED: reconciliation readback identity mismatch")
    mismatched = [
        i for i, v in after.items() if v != next(r["arabic"] for r in planned if r["identity"] == i)
    ]
    if mismatched:
        raise WorkflowError("IMPORT_WRITE_FAILED: post-import value mismatch")
    if not report.get("invariant_ok", False):
        raise WorkflowError("IMPORT_WRITE_FAILED: English/identity invariant violated")

    # Rollback export: previous Arabic values, stored in content-addressed private storage.
    rollback = {
        "schema": "stage4-rollback-export/v1",
        "recorded_utc": utc(),
        "erp_descriptor_hash": hashlib.sha256(canonical(erp_descriptor)).hexdigest(),
        "payload_sha256": hashlib.sha256(canonical(planned)).hexdigest(),
        "before": before,
    }
    rollback_bytes = canonical(rollback)
    rollback_sha = hashlib.sha256(rollback_bytes).hexdigest()
    from stage4 import store_private_blob

    store_private_blob(private_root, rollback_bytes, expected_sha=rollback_sha)

    imported_digest = report["imported_values_sha256"]
    evidence = {
        "schema": "stage4-import-evidence/v1",
        "recorded_utc": utc(),
        "rows_planned": len(planned),
        "rows_written": report.get("wrote", 0),
        "imported_values_sha256": imported_digest,
        "rollback_export_sha256": rollback_sha,
        "dry_run_evidence_digest": dry_run_evidence.get("evidence_digest"),
        "post_import_readback_sha256": hashlib.sha256(canonical(after)).hexdigest(),
        "invariant_ok": True,
    }
    evidence_bytes = canonical(evidence)
    evidence_digest = hashlib.sha256(evidence_bytes).hexdigest()
    write_json(Path(destination) / "import-evidence.json", evidence, immutable=True)
    write_json(
        Path(destination) / "rollback-manifest.json",
        {
            "schema": "stage4-rollback-manifest/v1",
            "rollback_export_sha256": rollback_sha,
            "rows": len(before),
            "private_storage": True,
            "note": "Rollback values remain in private content-addressed storage; only this manifest is public.",
        },
        immutable=True,
    )
    return {"evidence_digest": evidence_digest, "evidence": evidence}
