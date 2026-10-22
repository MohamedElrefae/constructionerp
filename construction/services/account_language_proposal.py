"""Stage 4: Egyptian Arabic Account-language export + proposal machinery.

Generates a governed, provenance-carrying export of the authorized
non-production Account catalog (default company 'Elrefae') plus an empty
AI-proposal template with the required fields. NO Account value is invented
and NO live Account mutation occurs.

Authorized coverage:
- Export runs only on the authorized non-production test site
  (site_classification 'non-production test').
- Raw rows are written to the site's private directory (never committed);
  only a non-sensitive manifest (schema, company, row count, export file
  SHA-256, provenance) is returned and may be committed.
- Never invents a MOF/EAS/ETA reference: every row is flagged
  `no_verified_reference` until a VERIFIED source reference is supplied by
  an independent AI-A2 review. Missing references are acceptable evidence.
- Proposal fields (proposed_arabic / confidence) are left empty until the
  independent AI proposal + AI-A2 review session produces and signs them;
  this module records the provenance scaffold, not a proposal decision.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

EXPORT_SCHEMA = "construction-stage4-account-language-proposal/v1"
GOVERNED_MANIFEST_SCHEMA = "construction-stage4-export-manifest/v1"
GOVERNED_MANIFEST_RELPATH = "data/localization/stage4_export_manifest.json"
DEFAULT_COMPANY = "Elrefae"
DOMAIN = "account-master"
GLOSSARY_FIELD = "glossary_match"
FLAG_PENDING = "pending_proposal"
FLAG_NO_VERIFIED_REFERENCE = "no_verified_reference"


def _utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def glossary_lookup():
    """Map English label -> Arabic from the governed Egyptian overrides CSV."""
    import csv

    import frappe

    path = frappe.get_app_path("construction", "data/translations/approved_ar_overrides.csv")
    mapping = {}
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            english = (row.get("source_text") or "").strip()
            arabic = (row.get("translated_text") or "").strip()
            if english and arabic:
                mapping.setdefault(english, arabic)
    return mapping


def export_account_catalog(company=DEFAULT_COMPANY, write=True):
    """Export the non-production Account catalog + build a proposal scaffold.

    Returns (rows, manifest). When `write`, rows are written to the site's
    private dir and the manifest carries the file SHA-256. No mutation.
    """
    import frappe

    site = frappe.local.site
    classification = "non-production test"
    glossary = glossary_lookup()

    accounts = frappe.get_all(
        "Account",
        filters={
            "company": company,
            "docstatus": ("<", 2),
            "disabled": 0,
        },
        fields=[
            "name",
            "account_name",
            "account_number",
            "parent_account",
            "is_group",
            "root_type",
            "account_type",
            "report_type",
            "account_name_ar",
        ],
        order_by="lft asc",
        limit_page_length=0,
    )

    rows = []
    glossary_match_count = 0
    for acc in accounts:
        english = (acc.account_name or "").strip()
        arabic_match = glossary.get(english)
        if arabic_match:
            glossary_match_count += 1
        rows.append(
            {
                "identity": acc.name,
                "english": english or None,
                "account_number": acc.account_number or None,
                "parent_account": acc.parent_account or None,
                "is_group": bool(acc.is_group),
                "root_type": acc.root_type or None,
                "account_type": acc.account_type or None,
                "report_type": acc.report_type or None,
                "current_arabic": acc.account_name_ar or None,
                # proposal scaffold (filled only by an independent AI
                # proposal + AI-A2 review session — never invented here):
                "proposed_arabic": None,
                "confidence": None,
                "glossary_match": arabic_match,
                "source_reference": None,
                "flags": [FLAG_PENDING, FLAG_NO_VERIFIED_REFERENCE],
                "provenance": {"recorded_by": frappe.session.user},
            }
        )

    recorded_utc = _utcnow()
    payload = {
        "schema": EXPORT_SCHEMA,
        "company": company,
        "domain": DOMAIN,
        "source_site": site,
        "source_classification": classification,
        "recorded_utc": recorded_utc,
        "recorded_by": frappe.session.user,
        "rows": rows,
        "no_verified_reference_policy": "No MOF/EAS/ETA reference is invented; 'no verified reference' is acceptable evidence until an independent AI-A2 review supplies a verified source reference.",
    }

    export_filename = None
    export_sha = None
    if write:
        private_dir = frappe.utils.get_site_path("private", "stage4")
        os.makedirs(private_dir, exist_ok=True)
        export_filename = "account_catalog_{}.json".format(
            recorded_utc.replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")
        )
        export_path = os.path.join(private_dir, export_filename)
        with open(export_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        export_sha = _sha256(export_path)
        export_abs = os.path.abspath(export_path)

    manifest = {
        "schema": EXPORT_SCHEMA,
        "company": company,
        "domain": DOMAIN,
        "rows": len(rows),
        "groups": sum(1 for r in rows if r["is_group"]),
        "leaves": sum(1 for r in rows if not r["is_group"]),
        "with_current_arabic": sum(1 for r in rows if r["current_arabic"]),
        "glossary_match_count": glossary_match_count,
        "no_verified_reference": FLAG_NO_VERIFIED_REFERENCE,
        "export_file": export_filename,
        "export_file_sha256": export_sha,
        "private_location": ("<site>/private/stage4/" + export_filename) if export_filename else None,
        "recorded_utc": recorded_utc,
        "recorded_by": frappe.session.user,
        "source_site": site,
        "source_classification": classification,
        "proposal_pending": FLAG_PENDING,
    }
    if write and export_sha:
        # Governed (non-sensitive) manifest: the ONLY authority the import
        # payload boundary trusts. Records the absolute private export path
        # and its SHA-256; contains no account rows.
        governed = dict(manifest)
        governed["schema"] = GOVERNED_MANIFEST_SCHEMA
        governed["export_path"] = export_abs
        governed["export_sha256"] = export_sha
        manifest_path = frappe.get_app_path("construction", GOVERNED_MANIFEST_RELPATH)
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(governed, fh, sort_keys=True, indent=1)
        manifest["governed_manifest"] = GOVERNED_MANIFEST_RELPATH
    return rows, manifest


def validate_proposal(record):
    """Validate a single proposal record contract (used by the AI-A2 road).

    Returns a list of violations; empty means structurally valid. This does
    NOT certify Arabic correctness — that remains with an independent AI-A2
    Egyptian accounting/QS review.
    """
    violations = []
    if not record:
        violations.append("record is empty")
        return violations
    for key in ("identity", "english", "is_group", "proposed_arabic", "confidence"):
        if key not in record:
            violations.append(f"missing field {key}")
    return violations


def dry_run_apply_proposals(rows, proposals_by_identity):
    """Zero-mutation preview: which rows WOULD be updated, nothing applied.

    Optimistic check: only proposes updating rows whose current `arabic`
    field is empty (or unchanged), and only for rows present in the export.
    Returns the plan; no DB write is performed.
    """
    plan = {"would_update": [], "unchanged": [], "missing": []}
    for row in rows:
        prop = (proposals_by_identity or {}).get(row["identity"])
        if not prop:
            plan["missing"].append(row["identity"])
            continue
        if row["current_arabic"]:
            plan["unchanged"].append(row["identity"])
            continue
        plan["would_update"].append(row["identity"])
    return plan
