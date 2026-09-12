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
import os
import re
import tempfile
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


ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]|\\u0[6-8][0-9a-fA-F]{2}|\\u[fF][b-fB-F][0-9a-fA-F]{2}"
)


def sanitize_public_text(text, catalog_terms=()):
    """Scrub private information from text intended for public artifacts, events, or logs.

    Redacts:
    - Any Arabic character sequences.
    - Any catalog identities or catalog English names passed in catalog_terms.
    """
    if not isinstance(text, str):
        return ""
    sanitized = ARABIC_RE.sub("[REDACTED_ARABIC]", text)
    if catalog_terms:
        for term in sorted(catalog_terms, key=len, reverse=True):
            if term and len(term) >= 2:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                sanitized = pattern.sub("[REDACTED_TERM]", sanitized)
    return sanitized


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
    for idx, r in enumerate(rows):
        if not isinstance(r, dict) or not r.get("identity") or not r.get("english"):
            raise WorkflowError(f"Proposal row at index {idx} missing required identity or english")
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
    for idx, p_row in enumerate(sorted_proposal):
        ident = p_row["identity"]
        a2 = a2_decisions.get(ident)
        if not a2:
            raise WorkflowError(f"Missing A2 review decision for row at index {idx}")

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
        for idx, r in enumerate(row_decisions):
            if not isinstance(r, dict):
                raise WorkflowError(f"Panel review {role} row at index {idx} not an object")
            ident = r.get("identity")
            if not ident or not isinstance(ident, str):
                raise WorkflowError(f"Panel review {role} has row at index {idx} without valid identity")
            if ident in identities_covered:
                raise WorkflowError(f"Duplicate identity in panel review {role}")
            identities_covered.add(ident)

            # Check decision type
            decision = r.get("decision")
            if decision == "rejected":
                blocking_findings.append({
                    "finding_id": f"rejected-{role}-{idx}",
                    "role": role,
                    "blocking": True,
                    "classification": "row_rejected",
                    "summary": f"Reviewer {role} rejected row at index {idx}",
                })
            elif decision not in ("approved", "exception"):
                raise WorkflowError(
                    f"Panel review {role} row at index {idx} invalid decision: must be 'approved' or 'exception'"
                )

            if decision == "exception" and not (r.get("rationale") or r.get("exception_reason")):
                raise WorkflowError(
                    f"Panel review {role} row at index {idx} marked as 'exception' without required rationale"
                )

            # Check if reviewer requested an Arabic value change
            if r.get("suggested_arabic") and r.get("suggested_arabic") != r.get("proposed_arabic"):
                renewal_required = True

        if identities_covered != expected_set:
            missing = expected_set - identities_covered
            extra = identities_covered - expected_set
            raise WorkflowError(
                f"Panel review {role} does not cover exact identities: missing {len(missing)}, extra {len(extra)}"
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


def store_private_blob(private_root, doc_bytes, expected_sha=None):
    """Store canonical document bytes in content-addressed storage with 0700 dir and 0600 file."""
    if not isinstance(doc_bytes, bytes):
        raise WorkflowError("doc_bytes must be bytes")
    blobs_dir = Path(private_root) / "blobs"
    blobs_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(blobs_dir), 0o700)
    sha256 = hashlib.sha256(doc_bytes).hexdigest()
    if expected_sha and sha256 != expected_sha:
        raise WorkflowError("Content SHA-256 does not match expected digest")
    target_path = blobs_dir / f"{sha256}.json"
    fd, tmp_name = tempfile.mkstemp(prefix=".blob-", dir=blobs_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(doc_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, target_path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    return sha256, target_path


def read_private_blob(private_root, sha256):
    """Read blob bytes from content-addressed storage and verify digest."""
    if not is_hex64(sha256):
        raise WorkflowError("Invalid blob digest: must be 64-character lowercase hex")
    blob_path = Path(private_root) / "blobs" / f"{sha256}.json"
    if not blob_path.exists() or blob_path.is_symlink():
        raise WorkflowError("Private blob missing or invalid")
    data = blob_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha256:
        raise WorkflowError("Private blob digest corrupted")
    return data


def validate_and_store_proposal(
    private_root,
    raw_proposal_path,
    expected_export_sha,
    expected_identities,
    expected_identities_digest,
    export_catalog_path=None,
):
    """Enforce exact 81 identities, English matching, is_group matching, non-empty Arabic, and semantic hash."""
    raw_path = Path(raw_proposal_path)
    if not raw_path.exists() or raw_path.is_symlink():
        raise WorkflowError("Raw proposal file missing or invalid symlink")

    try:
        content = raw_path.read_text()
        doc = json.loads(content)
    except (OSError, json.JSONDecodeError):
        raise WorkflowError("Raw proposal file could not be parsed as JSON")

    if not isinstance(doc, dict):
        raise WorkflowError("Proposal payload must be a JSON object")

    raw_export_sha = doc.get("export_sha256")
    if raw_export_sha != expected_export_sha:
        raise WorkflowError("Proposal export_sha256 mismatch")

    rows = doc.get("rows")
    if not isinstance(rows, list):
        raise WorkflowError("Proposal missing rows list")

    if len(rows) != len(expected_identities):
        raise WorkflowError(f"Proposal identity count mismatch: expected {len(expected_identities)}, found {len(rows)}")

    sorted_rows = project_proposal_rows(rows)
    identities = [r["identity"] for r in sorted_rows]

    if len(set(identities)) != len(expected_identities):
        raise WorkflowError("Proposal contains duplicate identities")

    if set(identities) != set(expected_identities):
        raise WorkflowError("Proposal identities do not match expected identities")

    actual_ident_digest = derive_identities_digest(identities)
    if actual_ident_digest != expected_identities_digest:
        raise WorkflowError("Proposal identities digest mismatch")

    catalog_by_id = {}
    if export_catalog_path:
        cat_p = Path(export_catalog_path)
        if cat_p.exists() and not cat_p.is_symlink():
            try:
                cat_doc = json.loads(cat_p.read_text())
                for cat_r in cat_doc.get("rows", []):
                    if isinstance(cat_r, dict) and cat_r.get("identity"):
                        catalog_by_id[cat_r["identity"]] = cat_r
            except (OSError, json.JSONDecodeError):
                pass

    for idx, r in enumerate(sorted_rows):
        ident = r["identity"]
        prop = r.get("proposal")
        if not isinstance(prop, dict):
            raise WorkflowError(f"Proposal row at index {idx} missing proposal dictionary")
        arabic = prop.get("arabic")
        if not isinstance(arabic, str) or not arabic.strip():
            raise WorkflowError(f"Proposal row at index {idx} missing non-empty Arabic text")

        if catalog_by_id and ident in catalog_by_id:
            cat_row = catalog_by_id[ident]
            cat_english = cat_row.get("english") or cat_row.get("account_name")
            if cat_english and r.get("english") != cat_english:
                raise WorkflowError(f"Proposal English name mismatch against catalog at row index {idx}")
            if "is_group" in cat_row:
                if bool(r.get("is_group", False)) != bool(cat_row.get("is_group", False)):
                    raise WorkflowError(f"Proposal is_group boolean mismatch against catalog at row index {idx}")

    canonical_proposal = {
        "schema": "stage4-proposal/v1",
        "export_sha256": expected_export_sha,
        "rows": sorted_rows,
    }
    canonical_bytes = canonical(canonical_proposal)
    proposal_sha256 = hashlib.sha256(canonical_bytes).hexdigest()

    calc_proposal_hash = derive_proposal_hash(sorted_rows, expected_export_sha)
    if proposal_sha256 != calc_proposal_hash:
        raise WorkflowError("Proposal canonical artifact hash does not match semantic projection hash")

    store_private_blob(private_root, canonical_bytes, expected_sha=proposal_sha256)

    return {
        "proposal_sha256": proposal_sha256,
        "artifact_sha256": proposal_sha256,
        "rows_count": len(sorted_rows),
        "export_sha256": expected_export_sha,
    }


def validate_and_store_review(
    private_root,
    raw_review_path,
    expected_role,
    expected_proposal_sha,
    expected_identities,
    expected_session_id=None,
    catalog_terms=(),
):
    """Validate reviewer row decisions, store canonical blob, and return metadata."""
    raw_path = Path(raw_review_path)
    if not raw_path.exists() or raw_path.is_symlink():
        raise WorkflowError("Raw review file missing or invalid symlink")

    try:
        content = raw_path.read_text()
        doc = json.loads(content)
    except (OSError, json.JSONDecodeError):
        raise WorkflowError("Raw review file could not be parsed as JSON")

    if not isinstance(doc, dict):
        raise WorkflowError("Review payload must be a JSON object")

    # Enforce declared provenance on the review document
    role = doc.get("role")
    if role != expected_role:
        raise WorkflowError(f"Review document role mismatch: expected {expected_role}, got {role}")

    proposal_sha = doc.get("proposal_sha256")
    if proposal_sha != expected_proposal_sha:
        raise WorkflowError(
            f"Review document proposal_sha256 mismatch: expected {expected_proposal_sha}, got {proposal_sha}"
        )

    session_id = doc.get("session_id")
    if not session_id or not isinstance(session_id, str):
        raise WorkflowError(f"Review for {expected_role} missing valid session_id")
    if expected_session_id and session_id != expected_session_id:
        raise WorkflowError(
            f"Review document session_id mismatch: expected {expected_session_id}, got {session_id}"
        )

    row_decisions = doc.get("row_decisions")
    if not isinstance(row_decisions, list) or len(row_decisions) != len(expected_identities):
        raise WorkflowError(
            f"Reviewer row decisions count mismatch for role {expected_role}: expected {len(expected_identities)}, found {len(row_decisions) if isinstance(row_decisions, list) else 0}"
        )

    expected_set = set(expected_identities)
    covered_set = set()
    blocking_findings = []
    renewal_required = False

    for idx, r in enumerate(row_decisions):
        if not isinstance(r, dict):
            raise WorkflowError(f"Reviewer {expected_role} row at index {idx} not an object")
        ident = r.get("identity")
        if not ident or not isinstance(ident, str):
            raise WorkflowError(f"Reviewer {expected_role} row at index {idx} lacks valid identity")
        if ident in covered_set:
            raise WorkflowError(f"Duplicate identity in panel review {expected_role}")
        covered_set.add(ident)

        decision = r.get("decision")
        if decision == "rejected":
            blocking_findings.append({
                "finding_id": f"rejected-{expected_role}-{idx}",
                "role": expected_role,
                "blocking": True,
                "classification": "row_rejected",
                "summary": f"Reviewer {expected_role} rejected row at index {idx}",
            })
        elif decision not in ("approved", "exception"):
            raise WorkflowError(
                f"Reviewer {expected_role} row at index {idx} invalid decision: must be 'approved' or 'exception'"
            )

        if decision == "exception" and not (r.get("rationale") or r.get("exception_reason")):
            raise WorkflowError(
                f"Reviewer {expected_role} row at index {idx} marked as 'exception' without required rationale"
            )

        if r.get("suggested_arabic") and r.get("suggested_arabic") != r.get("proposed_arabic"):
            renewal_required = True

    if covered_set != expected_set:
        missing = expected_set - covered_set
        extra = covered_set - expected_set
        raise WorkflowError(
            f"Panel review {expected_role} does not cover exact identities: missing {len(missing)}, extra {len(extra)}"
        )

    for f in doc.get("findings", []):
        if f.get("blocking", True):
            blocking_findings.append(dict(f, role=expected_role))
        if f.get("classification") == "arabic_value_change":
            renewal_required = True

    if doc.get("verdict") == "BLOCKED" and not blocking_findings:
        blocking_findings.append({
            "finding_id": f"blocked-{expected_role}",
            "role": expected_role,
            "blocking": True,
            "classification": "review_rejected",
            "summary": f"Reviewer {expected_role} reported BLOCKED verdict",
        })

    canonical_review = {
        "schema": "stage4-panel-review/v1",
        "role": role,
        "session_id": session_id,
        "proposal_sha256": proposal_sha,
        "verdict": "BLOCKED" if blocking_findings else doc.get("verdict", "PASS"),
        "renewal_required": bool(renewal_required),
        "row_decisions": row_decisions,
        "findings": doc.get("findings", []),
    }
    canonical_bytes = canonical(canonical_review)
    review_sha = hashlib.sha256(canonical_bytes).hexdigest()
    store_private_blob(private_root, canonical_bytes, expected_sha=review_sha)

    sanitized_blocking = [
        {
            "finding_id": f.get("finding_id", f"finding-{i}"),
            "role": expected_role,
            "blocking": bool(f.get("blocking", True)),
            "classification": f.get("classification", "generic"),
            "summary": sanitize_public_text(f.get("summary", ""), catalog_terms=catalog_terms),
        }
        for i, f in enumerate(blocking_findings)
    ]

    return {
        "review_sha256": review_sha,
        "role": expected_role,
        "session_id": session_id,
        "verdict": canonical_review["verdict"],
        "renewal_required": bool(renewal_required),
        "blocking_findings": sanitized_blocking,
    }


def compose_and_store_bundle_and_payload(
    private_root,
    proposal_sha,
    a2_review_sha,
    company,
    candidate_id,
    export_sha,
    erp_descriptor_hash,
    panel_digests,
    required_roles=("ai-a1", "ai-a2", "ai-a3"),
):
    """Reads blobs, composes bundle and payload, verifies manifest, stores blobs, and returns metadata."""
    # Ensure every required review has PASS, no blocking findings, and no renewal
    for role in required_roles:
        if role not in panel_digests:
            raise WorkflowError(f"Missing panel review digest for required role {role}")
        rev_sha = panel_digests[role]
        rev_bytes = read_private_blob(private_root, rev_sha)
        rev_doc = json.loads(rev_bytes)
        if rev_doc.get("verdict") != "PASS":
            raise WorkflowError(
                f"Cannot compose bundle: panel review {role} reported non-PASS verdict {rev_doc.get('verdict')}"
            )
        if any(f.get("blocking", True) for f in rev_doc.get("findings", [])):
            raise WorkflowError(f"Cannot compose bundle: panel review {role} contains blocking findings")
        if any(r.get("decision") == "rejected" for r in rev_doc.get("row_decisions", [])):
            raise WorkflowError(f"Cannot compose bundle: panel review {role} contains rejected row decisions")
        renewal = (
            bool(rev_doc.get("renewal_required"))
            or any(
                r.get("suggested_arabic") and r.get("suggested_arabic") != r.get("proposed_arabic")
                for r in rev_doc.get("row_decisions", [])
            )
            or any(f.get("classification") == "arabic_value_change" for f in rev_doc.get("findings", []))
        )
        if renewal:
            raise WorkflowError(f"Cannot compose bundle: panel review {role} requires renewal")

    proposal_bytes = read_private_blob(private_root, proposal_sha)
    proposal_doc = json.loads(proposal_bytes)
    proposal_rows = proposal_doc.get("rows", [])

    a2_bytes = read_private_blob(private_root, a2_review_sha)
    a2_doc = json.loads(a2_bytes)
    a2_rows = a2_doc.get("row_decisions", [])
    a2_decisions = {r["identity"]: r for r in a2_rows}

    bundle = compose_bundle(proposal_rows, a2_decisions, company=company)
    bundle_bytes = canonical(bundle)
    bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
    store_private_blob(private_root, bundle_bytes, expected_sha=bundle_sha)

    payload = [{"identity": r["identity"], "arabic": r["proposal"]["arabic"]} for r in bundle["rows"]]
    payload_bytes = canonical(payload)
    payload_sha = hashlib.sha256(payload_bytes).hexdigest()
    store_private_blob(private_root, payload_bytes, expected_sha=payload_sha)

    verify_stage4_manifest(
        candidate_id,
        export_sha,
        proposal_sha,
        bundle_sha,
        payload_sha,
        panel_digests,
        required_roles=required_roles,
    )

    return {
        "bundle_sha256": bundle_sha,
        "payload_sha256": payload_sha,
        "bundle_artifact": {
            "artifact_id": f"stage4-bundle-{bundle_sha[:16]}",
            "sha256": bundle_sha,
            "visibility": "private",
        },
        "payload_artifact": {
            "artifact_id": f"stage4-payload-{payload_sha[:16]}",
            "sha256": payload_sha,
            "visibility": "private",
        },
    }
