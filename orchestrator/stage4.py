"""Stage 4 ERP Adoption helper contracts and invariant checkers.

Implements Canonical Plan §5.3, §11:
- Private Stage 4 proposal projection and candidate derivation.
- Deterministic bundle composition from frozen proposal + A2 decisions.
- Panel review quorum and exact identity coverage validation with failure enforcement.
- Discrete 64-char lowercase hexadecimal hash definitions (export, proposal, candidate_id, bundle, payload).
- Fail-closed revalidation of historical provenance directly from referenced files on disk.
- Pure, fail-closed, with zero mutation to apps/construction or database.
"""

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from core import WorkflowError, canonical, digest

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def is_hex64(val):
    """Return True if val is a 64-character lowercase hexadecimal string."""
    return isinstance(val, str) and bool(HEX64_RE.match(val))


def derive_identities_digest(identities):
    """Canonical Plan §11.1: Require exactly 81 unique, non-empty string identities and bind their deterministic digest."""
    if not isinstance(identities, (list, tuple, set)):
        raise WorkflowError("Identities must be a sequence or set")
    cleaned = []
    for ident in identities:
        if not isinstance(ident, str) or not ident.strip():
            raise WorkflowError("Identity must be a non-empty string")
        cleaned.append(ident.strip())
    if len(cleaned) != 81:
        raise WorkflowError(f"Expected exactly 81 identities, found {len(cleaned)}")
    if len(set(cleaned)) != 81:
        raise WorkflowError(f"Expected 81 unique identities, found {len(set(cleaned))} unique")
    return digest({"schema": "stage4-identities/v1", "count": 81, "identities": sorted(cleaned)})


def canonical_bundle_sha256(bundle):
    """Deterministic SHA-256 digest of composed review bundle."""
    return hashlib.sha256(
        json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def canonical_payload_sha256(payload):
    """Deterministic SHA-256 digest of verified import payload."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


HISTORICAL_PROVENANCE_AUTHORITY = {
    "stage_0": {
        "evidence_relpath": "docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-0-baseline.md",
        "expected_sha256": "5334c6683a4fd51096c2f6e03d01458dff3ca70072c82998036806fe30d27efd",
        "artifact_id": "stage-0-baseline",
    },
    "stage_1": {
        "evidence_relpath": "docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-1c-ai-r-durability-final.md",
        "expected_sha256": "54ed9554fb2b8f82834598e5213a7aa6c954694497d0c5569754ed1a80dd42d8",
        "artifact_id": "stage-1c-ai-r-durability-final",
        "patch_relpath": "construction/patches/v8_8/add_account_arabic_name_field.py",
        "patch_expected_sha256": "33c23744bcff248b0884c5b51439ffdb02afdd216a43a2a4f4060371e32f594e",
    },
    "stage_2": {
        "evidence_relpath": "docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-2-ai-r-round19.md",
        "expected_sha256": "3e83a3528fff02a206745df235fcfb5cc212d335129847e3144e0ab68347a880",
        "artifact_id": "stage-2-ai-r-round19",
    },
    "stage_3": {
        "evidence_relpath": "docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-3-ai-r-round12.md",
        "expected_sha256": "4a397f7acfd72de31e3cc72796c45d4d917947fc213d808668d5df217292f7ed",
        "artifact_id": "stage-3-ai-r-round12",
        "service_relpath": "construction/services/bilingual_service.py",
        "service_expected_sha256": "a8c049443d7755714e2a173c75cd5747fce527a374be6b43cf7c76b49ebd0698",
    },
    "stage_4_foundation": {
        "manifest_relpath": "construction/data/localization/stage4_export_manifest.json",
        "manifest_expected_sha256": "cf2e5fed416fdc2626da9e40f37a43c0a1233261d5625c34d8a2f0c0eec9548f",
        "export_relpath": "sites/v16.localhost/private/stage4/account_catalog_20260910_121018.json",
        "export_expected_sha256": "206ecfae017b915742abc265016eee094304562e53838a932c7fd56af6db9ed1",
        "evidence_relpath": "docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-4-export.md",
        "expected_sha256": "a9f4c008ad70cb8646625d853975e5a58099271576660b73a92316b3a482149f",
        "bundle_service_relpath": "construction/services/account_review_bundle.py",
        "bundle_service_expected_sha256": "dd3bbf692391198897b11f34b0efcf9936e5817d2db9e6b4092407c084c74a74",
    },
}


def verify_historical_provenance(erp_checkout, bench_root=None):
    """Revalidates historical provenance directly from referenced files on disk.

    Fail-closed: reads every file on disk, computes its SHA-256 hash, and verifies it.
    Returns the audited provenance dictionary with corrected evidence references.
    """
    erp_checkout = Path(erp_checkout)
    bench_root = Path(bench_root) if bench_root else erp_checkout.parent.parent

    verified = {}
    for stage_key, spec in HISTORICAL_PROVENANCE_AUTHORITY.items():
        ev_path = erp_checkout / spec["evidence_relpath"]
        if not ev_path.exists():
            raise WorkflowError(f"Historical evidence file missing on disk: {ev_path}")
        ev_sha = hashlib.sha256(ev_path.read_bytes()).hexdigest()
        if ev_sha != spec["expected_sha256"]:
            raise WorkflowError(
                f"Historical evidence hash mismatch for {stage_key}: got {ev_sha}, expected {spec["expected_sha256"]}"
            )

        stage_data = {
            "status": "VERIFIED",
            "historical": True,
            "evidence_sha256": ev_sha,
            "artifact_id": spec.get("artifact_id"),
        }
        if "patch_relpath" in spec:
            p_path = erp_checkout / spec["patch_relpath"]
            if not p_path.exists():
                raise WorkflowError(f"Patch file missing on disk: {p_path}")
            p_sha = hashlib.sha256(p_path.read_bytes()).hexdigest()
            if p_sha != spec["patch_expected_sha256"]:
                raise WorkflowError(f"Patch hash mismatch: got {p_sha}, expected {spec["patch_expected_sha256"]}")
            stage_data["patch_sha256"] = p_sha

        if "service_relpath" in spec:
            s_path = erp_checkout / spec["service_relpath"]
            if not s_path.exists():
                raise WorkflowError(f"Service file missing on disk: {s_path}")
            s_sha = hashlib.sha256(s_path.read_bytes()).hexdigest()
            if s_sha != spec["service_expected_sha256"]:
                raise WorkflowError(f"Service hash mismatch: got {s_sha}, expected {spec["service_expected_sha256"]}")
            stage_data["service_sha256"] = s_sha

        if stage_key == "stage_4_foundation":
            m_path = erp_checkout / spec["manifest_relpath"]
            if not m_path.exists():
                raise WorkflowError(f"Manifest missing on disk: {m_path}")
            m_sha = hashlib.sha256(m_path.read_bytes()).hexdigest()
            if m_sha != spec["manifest_expected_sha256"]:
                raise WorkflowError(f"Manifest hash mismatch: got {m_sha}, expected {spec["manifest_expected_sha256"]}")

            exp_path = bench_root / spec["export_relpath"]
            if not exp_path.exists():
                raise WorkflowError(f"Export file missing on disk: {exp_path}")
            exp_sha = hashlib.sha256(exp_path.read_bytes()).hexdigest()
            if exp_sha != spec["export_expected_sha256"]:
                raise WorkflowError(f"Export file hash mismatch: got {exp_sha}, expected {spec["export_expected_sha256"]}")

            b_path = erp_checkout / spec["bundle_service_relpath"]
            if not b_path.exists():
                raise WorkflowError(f"Bundle service missing on disk: {b_path}")
            b_sha = hashlib.sha256(b_path.read_bytes()).hexdigest()
            if b_sha != spec["bundle_service_expected_sha256"]:
                raise WorkflowError(f"Bundle service hash mismatch: got {b_sha}, expected {spec["bundle_service_expected_sha256"]}")

            stage_data.update({
                "manifest_sha256": m_sha,
                "export_file_sha256": exp_sha,
                "bundle_service_sha256": b_sha,
            })

        verified[stage_key] = stage_data
    return verified


def project_proposal_rows(rows):
    """Derive private proposal projection sorted by identity.

    Per §5.3:
    Sort rows by identity; each contains identity, english, is_group, and the complete
    proposal object. Exclude A2 decisions and review-generated top-level row flags.
    """
    projected = []
    for r in rows:
        if not r.get("identity") or not r.get("english"):
            raise WorkflowError(f"Proposal row missing required identity or english: {r}")
        projected.append({
            "identity": r["identity"],
            "english": r["english"],
            "is_group": bool(r.get("is_group", False)),
            "proposal": deepcopy(r.get("proposal") or {}),
        })
    return sorted(projected, key=lambda x: x["identity"])


def derive_proposal_hash(rows, export_sha256):
    """Per §5.3: H of private projection {schema: stage4-proposal/v1, export_sha256, rows}."""
    if not is_hex64(export_sha256):
        raise WorkflowError("export_sha256 must be 64-character lowercase hex")
    sorted_rows = project_proposal_rows(rows)
    payload = {
        "schema": "stage4-proposal/v1",
        "export_sha256": export_sha256,
        "rows": sorted_rows,
    }
    return digest(payload)


def derive_stage4_candidate_id(export_sha256, proposal_sha256):
    """Per §5.3: H of {kind: stage4-proposal, export_sha256, proposal_sha256}."""
    if not is_hex64(export_sha256):
        raise WorkflowError("export_sha256 must be 64-character lowercase hex")
    if not is_hex64(proposal_sha256):
        raise WorkflowError("proposal_sha256 must be 64-character lowercase hex")
    return digest({
        "kind": "stage4-proposal",
        "export_sha256": export_sha256,
        "proposal_sha256": proposal_sha256,
    })


def compose_bundle(proposal_rows, a2_decisions, company="Elrefae"):
    """Per §5.3 and §11.3:

    Compose completed bundle deterministically from frozen proposal plus accepted A2 decisions/flags.
    Rows sorted by identity.
    Preserves proposal projection and proves composed bundle matches reviewed candidate.
    """
    sorted_proposal = project_proposal_rows(proposal_rows)
    bundle_rows = []
    for p_row in sorted_proposal:
        ident = p_row["identity"]
        a2 = a2_decisions.get(ident)
        if not a2:
            raise WorkflowError(f"Missing A2 review decision for identity: {ident}")

        # Flags on the row: preserve proposal flags + add no_verified_reference if reference absent
        flags = list(p_row.get("proposal", {}).get("flags", []))
        if a2.get("reference", {}).get("status") == "absent" and "no_verified_reference" not in flags:
            flags.append("no_verified_reference")

        b_row = {
            "identity": ident,
            "english": p_row["english"],
            "is_group": p_row["is_group"],
            "proposal": deepcopy(p_row["proposal"]),
            "a2_review": deepcopy(a2),
            "flags": sorted(list(set(flags))),
        }
        bundle_rows.append(b_row)

    bundle = {
        "schema": "construction-stage4-account-review-bundle/v1",
        "company": company,
        "workflow": "independent-proposal -> ai-a2-review -> owner-approval -> dry-run -> authorized import",
        "rows": bundle_rows,
    }

    # Prove projection matches
    composed_projection = project_proposal_rows(bundle["rows"])
    if composed_projection != sorted_proposal:
        raise WorkflowError("Bundle proposal projection does not match reviewed candidate projection")

    return bundle


def validate_panel_reviews(reviews, expected_identities, required_roles=("ai-a1", "ai-a2", "ai-a3")):
    """Per §11.3 & §11.4:

    - Exact required roles (no missing, no extraneous).
    - Distinct reviewer sessions (no duplicate session IDs).
    - Exact identity coverage across every reviewer (no missing, no duplicate, no extraneous).
    - Validates row decisions (approved or exception).
    - Collects blocking findings.
    - Flags requested Arabic value changes -> requires PANEL_RENEWAL.
    """
    required_set = set(required_roles)
    actual_set = set(reviews.keys())
    if actual_set != required_set:
        raise WorkflowError(f"Panel reviews role mismatch: got {actual_set}, expected exact {required_set}")

    sessions = []
    renewal_required = False
    blocking_findings = []
    expected_set = set(expected_identities)

    for role in required_roles:
        rev = reviews[role]
        sess = rev.get("session_id")
        if not sess or not isinstance(sess, str):
            raise WorkflowError(f"Panel review {role} lacks valid session_id")
        sessions.append(sess)

        # Check for top-level verdict and findings
        for f in rev.get("findings", []):
            if f.get("blocking", True):
                blocking_findings.append(dict(f, role=role))
            if f.get("classification") == "arabic_value_change":
                renewal_required = True

        if rev.get("verdict") == "BLOCKED" and not blocking_findings:
            blocking_findings.append({
                "finding_id": f"blocked-{role}",
                "role": role,
                "blocking": True,
                "classification": "review_rejected",
                "summary": f"Panel review {role} reported BLOCKED verdict",
            })

        # Check row-level coverage and decisions
        row_decisions = rev.get("row_decisions")
        if not isinstance(row_decisions, list):
            raise WorkflowError(f"Panel review {role} missing row_decisions list")

        identities_covered = set()
        for r in row_decisions:
            ident = r.get("identity")
            if not ident or not isinstance(ident, str):
                raise WorkflowError(f"Panel review {role} has row without valid identity: {r}")
            if ident in identities_covered:
                raise WorkflowError(f"Duplicate identity '{ident}' in panel review {role}")
            identities_covered.add(ident)

            # Check decision type
            decision = r.get("decision")
            if decision == "rejected":
                blocking_findings.append({
                    "finding_id": f"rejected-{role}-{ident}",
                    "role": role,
                    "blocking": True,
                    "classification": "row_rejected",
                    "identity": ident,
                    "summary": f"Reviewer {role} rejected row {ident}: {r.get('rationale') or 'no rationale'}",
                })
            elif decision not in ("approved", "exception"):
                raise WorkflowError(
                    f"Panel review {role} row {ident} invalid decision '{decision}': must be 'approved' or 'exception'"
                )

            if decision == "exception" and not (r.get("rationale") or r.get("exception_reason")):
                raise WorkflowError(
                    f"Panel review {role} row {ident} marked as 'exception' without required rationale"
                )

            # Check if reviewer requested an Arabic value change
            if r.get("suggested_arabic") and r.get("suggested_arabic") != r.get("proposed_arabic"):
                renewal_required = True

        if identities_covered != expected_set:
            diff = expected_set.symmetric_difference(identities_covered)
            missing = expected_set - identities_covered
            extra = identities_covered - expected_set
            raise WorkflowError(
                f"Panel review {role} does not cover exact identities: missing {len(missing)}, extra {len(extra)}, symmetric difference: {diff}"
            )

    if len(set(sessions)) != len(sessions):
        raise WorkflowError("Panel review sessions are not independent (duplicate session_id observed)")

    return {
        "ok": len(blocking_findings) == 0,
        "renewal_required": renewal_required,
        "blocking_findings": blocking_findings,
        "sessions": sessions,
    }


def verify_stage4_manifest(
    candidate_id,
    export_sha256,
    proposal_sha256,
    bundle_sha256,
    payload_sha256,
    panel_digests,
    required_roles=("ai-a1", "ai-a2", "ai-a3"),
):
    """Asserts all 5 Stage 4 hashes are present, non-empty 64-char lowercase hex, and distinct."""
    hashes = {
        "export_sha256": export_sha256,
        "proposal_sha256": proposal_sha256,
        "candidate_id": candidate_id,
        "bundle_sha256": bundle_sha256,
        "payload_sha256": payload_sha256,
    }
    for k, v in hashes.items():
        if not is_hex64(v):
            raise WorkflowError(f"Invalid {k}: must be 64-character lowercase hex digest")

    # All 5 hashes must be distinct from one another
    if len(set(hashes.values())) != 5:
        raise WorkflowError("Hash collision / non-distinct Stage 4 hashes detected")

    if not isinstance(panel_digests, dict) or set(panel_digests.keys()) != set(required_roles):
        raise WorkflowError(f"Invalid panel digests: keys must match exact required roles {set(required_roles)}")

    for role, digest_val in panel_digests.items():
        if not is_hex64(digest_val):
            raise WorkflowError(f"Invalid panel digest for role {role}: must be 64-character lowercase hex")

    return True
