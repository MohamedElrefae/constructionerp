"""Stage 4: governed Account Arabic-name review-bundle contract.

Pure, stdlib-only, fail-closed. This module defines the schema an
INDEPENDENT Arabic-account proposal session must satisfy and the validator
that refuses to emit an import payload unless every row carries:

- a proposal block (arabic value, confidence, model/session provenance);
- a DISTINCT AI-A2 review block (independent reviewer/model/session, a
  decision in {approved, exception}, confidence, rationale, and either a
  verified authoritative reference or an EXPLICIT documented absence);
- ordered timestamps (proposal before AI-A2 review).

Rules:
- No Arabic value is invented or defaulted here — the validator only checks.
- Exceptions are preserved as reviewable rows (surfaced, never silently
  excluded).
- Nothing mutates the database; `build_import_payload` only returns an
  in-memory payload after the whole bundle passes.
"""

import hashlib
import json
import os
from datetime import datetime

BUNDLE_SCHEMA = "construction-stage4-account-review-bundle/v1"
# Schema of the private Stage 4 export this bundle must be bound to
# (mirrors construction.services.account_language_proposal.EXPORT_SCHEMA).
EXPORT_SCHEMA = "construction-stage4-account-language-proposal/v1"
GOVERNED_MANIFEST_SCHEMA = "construction-stage4-export-manifest/v1"
GOVERNED_MANIFEST_RELPATH = "construction/data/localization/stage4_export_manifest.json"
DECISIONS = ("approved", "exception")
REFERENCE_STATUSES = ("verified", "absent")
WORKFLOW = "independent-proposal -> ai-a2-review -> owner-approval -> dry-run -> authorized import"

_UTC = "%Y-%m-%dT%H:%M:%SZ"


class BundleError(ValueError):
    """Raised when a bundle is not eligible to produce an import payload."""


def _parse_utc(value):
    try:
        return datetime.strptime(str(value), _UTC)
    except (TypeError, ValueError):
        return None


def bundle_template():
    """Empty review-bundle scaffold for the independent sessions to fill.

    Never pre-fills Arabic values or decisions.
    """
    return {
        "schema": BUNDLE_SCHEMA,
        "company": None,
        "workflow": WORKFLOW,
        "created_utc": None,
        "rows": [
            {
                "identity": None,
                "english": None,
                "is_group": None,
                "proposal": {
                    "arabic": None,
                    "confidence": None,
                    "flags": [],
                    "provenance": {
                        "reviewer": None,
                        "model": None,
                        "session": None,
                        "submitted_utc": None,
                    },
                },
                "a2_review": {
                    "decision": None,
                    "confidence": None,
                    "rationale": None,
                    "reference": {
                        "status": None,  # "verified" | "absent"
                        "value": None,
                        "source": None,
                    },
                    "provenance": {
                        "reviewer": None,
                        "model": None,
                        "session": None,
                        "reviewed_utc": None,
                    },
                },
                "flags": [],
            }
        ],
    }


def _validate_row(row, index, errors):
    where = f"row[{index}]"
    identity = row.get("identity")
    if not identity:
        errors.append(f"{where}: identity is required")
    english = row.get("english")
    if not english:
        errors.append(f"{where}: english is required")

    proposal = row.get("proposal") or {}
    arabic = proposal.get("arabic")
    if not arabic or not str(arabic).strip():
        errors.append(f"{where}: proposal.arabic is required (no value may be invented)")
    if not proposal.get("confidence"):
        errors.append(f"{where}: proposal.confidence is required")
    pprov = proposal.get("provenance") or {}
    for key in ("reviewer", "model", "session", "submitted_utc"):
        if not pprov.get(key):
            errors.append(f"{where}: proposal.provenance.{key} is required")
    submitted = _parse_utc(pprov.get("submitted_utc"))

    a2 = row.get("a2_review") or {}
    decision = a2.get("decision")
    if decision not in DECISIONS:
        errors.append(f"{where}: a2_review.decision must be one of {list(DECISIONS)} (got {decision!r})")
    if not a2.get("confidence"):
        errors.append(f"{where}: a2_review.confidence is required")
    if not a2.get("rationale") or not str(a2.get("rationale")).strip():
        errors.append(f"{where}: a2_review.rationale is required")

    ref = a2.get("reference") or {}
    status = ref.get("status")
    if status not in REFERENCE_STATUSES:
        errors.append(
            f"{where}: a2_review.reference.status must be one of {list(REFERENCE_STATUSES)} (verified authoritative source or explicit documented absence)"
        )
    elif status == "verified":
        if not ref.get("value") or not ref.get("source"):
            errors.append(
                f"{where}: verified reference requires value and source; references must never be invented"
            )
    else:  # absent
        # explicit documented absence: the rationale above plus the flag below
        flags = set(row.get("flags") or [])
        if "no_verified_reference" not in flags:
            errors.append(f"{where}: absent reference requires the explicit 'no_verified_reference' flag")

    apro = a2.get("provenance") or {}
    for key in ("reviewer", "model", "session", "reviewed_utc"):
        if not apro.get(key):
            errors.append(f"{where}: a2_review.provenance.{key} is required")
    reviewed = _parse_utc(apro.get("reviewed_utc"))

    # Independence: distinct reviewer identity AND distinct session.
    if pprov.get("session") and apro.get("session") and pprov.get("session") == apro.get("session"):
        errors.append(f"{where}: proposal and AI-A2 provenance must use DISTINCT sessions (independence)")
    if pprov.get("reviewer") and apro.get("reviewer") and pprov.get("reviewer") == apro.get("reviewer"):
        errors.append(
            f"{where}: proposal and AI-A2 reviewers must be DISTINCT (proposal cannot approve itself)"
        )

    # Ordering.
    if submitted and reviewed and submitted > reviewed:
        errors.append(f"{where}: proposal timestamp is after the AI-A2 review timestamp")
    if submitted is None and pprov.get("submitted_utc"):
        errors.append(f"{where}: proposal.provenance.submitted_utc is not a valid {_UTC} timestamp")
    if reviewed is None and apro.get("reviewed_utc"):
        errors.append(f"{where}: a2_review.provenance.reviewed_utc is not a valid {_UTC} timestamp")


def validate_bundle(bundle, expected_identities=None, expected_english=None, now_utc=None):
    """Validate the whole bundle; fail-closed. Returns a summary dict.

    Identity binding (when provided):
    - `expected_identities`: the exported/candidate identities the bundle
      must cover. Every bundle identity must be known (no invented/foreign
      identities) and every expected identity must appear exactly once —
      a silently omitted exported account is a violation, not acceptable.
    - `expected_english`: {identity: english} — the row's English value must
      match the candidate, preventing identity/content mix-ups.
    - `now_utc`: reject future proposal/review timestamps (fail-closed).

    Exceptions are PRESERVED as reviewable rows (never silently excluded).
    """
    errors = []
    if not isinstance(bundle, dict):
        return {
            "violations": ["bundle is not an object"],
            "reviewable_exceptions": [],
            "approved_count": 0,
            "row_count": 0,
            "missing_identities": [],
        }
    if bundle.get("schema") != BUNDLE_SCHEMA:
        errors.append("schema must be {!r} (got {!r})".format(BUNDLE_SCHEMA, bundle.get("schema")))
    rows = bundle.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("rows must be a non-empty list")
        rows = []

    now = None
    if now_utc is not None:
        now = _parse_utc(now_utc)
        if now is None:
            errors.append(
                f"now_utc is not a valid {_UTC} timestamp (future-timestamp control cannot be silently disabled)"
            )
    now_utc_valid = now_utc is None or now is not None
    seen = set()
    reviewable_exceptions = []
    approved_count = 0
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row[{i}]: not an object")
            continue
        _validate_row(row, i, errors)
        identity = row.get("identity")
        if identity:
            if identity in seen:
                errors.append(f"row[{i}]: duplicate identity {identity!r}")
            seen.add(identity)
        if expected_identities is not None and identity and identity not in set(expected_identities):
            errors.append(f"row[{i}]: identity {identity!r} is not in the exported/candidate account set")
        if expected_english and identity in expected_english:
            expected_value = expected_english[identity]
            if expected_value is not None and row.get("english") != expected_value:
                errors.append(
                    f"row[{i}]: english {row.get('english')!r} does not match the candidate value "
                    f"{expected_value!r} for identity {identity!r}"
                )
        if now is not None:
            prop_ts = _parse_utc(((row.get("proposal") or {}).get("provenance") or {}).get("submitted_utc"))
            a2_ts = _parse_utc(((row.get("a2_review") or {}).get("provenance") or {}).get("reviewed_utc"))
            if prop_ts and prop_ts > now:
                errors.append(f"row[{i}]: proposal timestamp is in the future")
            if a2_ts and a2_ts > now:
                errors.append(f"row[{i}]: AI-A2 timestamp is in the future")
        a2 = row.get("a2_review") or {}
        if a2.get("decision") == "exception":
            reviewable_exceptions.append(identity or f"row[{i}]")
        elif a2.get("decision") == "approved":
            approved_count += 1

    missing_identities = []
    if expected_identities is not None:
        expected_set = set(expected_identities)
        missing_identities = sorted(expected_set - seen)
        for identity in missing_identities:
            errors.append(
                f"identity {identity!r} from the exported/candidate set is silently omitted from the bundle "
                "(record it as approved or exception)"
            )

    return {
        "violations": errors,
        "reviewable_exceptions": reviewable_exceptions,
        "approved_count": approved_count,
        "row_count": len(rows),
        "missing_identities": missing_identities,
    }


def canonical_sha256(bundle):
    """Deterministic bundle hash for provenance binding."""
    return hashlib.sha256(
        json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _governed_manifest_path():
    """Resolve the ONE internally governed manifest path (the trust root).

    Not caller-selectable: the production entry point always uses this
    fixed app path. Tests may monkeypatch this private resolver to a temp
    manifest; the public entry point exposes no path parameter.
    """
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "localization",
        "stage4_export_manifest.json",
    )


def _load_governed_manifest(manifest_path):
    """Load + structurally validate the governed export manifest.

    The manifest is the ONLY trust root: it records the absolute private
    export path and the export's recorded SHA-256, and carries no account
    rows. A caller cannot supply an object, a mapping, or a SHA.
    """
    if not isinstance(manifest_path, str | bytes) or not manifest_path:
        raise BundleError("governed manifest path must be a filesystem path")
    manifest_path = os.fspath(manifest_path)
    if not os.path.exists(manifest_path):
        raise BundleError(f"governed export manifest not found: {manifest_path}")
    try:
        with open(manifest_path, "rb") as fh:
            raw = fh.read()
        manifest = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise BundleError(f"governed export manifest is unreadable: {exc}")
    if not isinstance(manifest, dict) or manifest.get("schema") != GOVERNED_MANIFEST_SCHEMA:
        raise BundleError(f"governed manifest schema must be {GOVERNED_MANIFEST_SCHEMA!r}")
    for key in ("export_path", "export_sha256"):
        if not manifest.get(key):
            raise BundleError(f"governed manifest lacks {key}")
    return manifest


def _reload_verified_export(manifest):
    """Reload the private export from disk and verify it against the
    governed manifest; derive the identity->English map INTERNALLY.

    Called by the import-facing operation immediately before payload
    construction. Mismatch (missing file, tampered bytes, wrong schema,
    duplicate/empty identity) raises BundleError.
    """
    export_path = manifest["export_path"]
    if not os.path.isabs(export_path):
        raise BundleError("governed manifest export_path must be absolute")
    if not os.path.exists(export_path):
        raise BundleError(f"private export referenced by the governed manifest is missing: {export_path}")
    with open(export_path, "rb") as fh:
        raw = fh.read()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != str(manifest["export_sha256"]).strip():
        raise BundleError(
            "private export SHA-256 mismatch against the governed manifest: recorded {} != actual {}".format(
                str(manifest["export_sha256"]).strip(), actual
            )
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BundleError(f"private export is not valid JSON: {exc}")
    if not isinstance(payload, dict) or payload.get("schema") != EXPORT_SCHEMA:
        raise BundleError(f"private export schema must be {EXPORT_SCHEMA!r}")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise BundleError("private export has no rows")
    identities = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("identity"):
            raise BundleError(f"private export row[{i}] lacks an identity")
        if row["identity"] in identities:
            raise BundleError("private export has a duplicate identity {!r}".format(row["identity"]))
        if not row.get("english"):
            raise BundleError(f"private export row[{i}] ({row['identity']}) lacks an English value")
        identities[row["identity"]] = row["english"]
    return identities, actual


def build_import_payload(bundle, now_utc=None):
    """Return the in-memory import payload IFF the whole bundle passes and is
    bound to the private Stage 4 export behind the governed manifest.

    The production entry point accepts ONLY the bundle (and an optional time
    bound): it resolves the single internally governed manifest path — it
    CANNOT be given a manifest path, object, or SHA by the caller. It then
    reloads the private export itself, verifies its bytes against the
    manifest's recorded SHA-256, and derives the identity->English map
    internally. The bundle must name EXACTLY the export's identities with
    matching English values (missing, extra, or forged keys refused).
    Fail-closed: raises BundleError on any violation. NO database write.

    Test-only dependency injection lives on the private
    `_governed_manifest_path` resolver (monkeypatched), never here.
    """
    governed_manifest_path = _governed_manifest_path()
    manifest = _load_governed_manifest(governed_manifest_path)
    identities, export_sha = _reload_verified_export(manifest)
    summary = validate_bundle(
        bundle,
        expected_identities=set(identities),
        expected_english=identities,
        now_utc=now_utc,
    )
    if summary["violations"]:
        raise BundleError(
            f"review bundle is not eligible for an import payload ({len(summary['violations'])} violation(s)): "
            f"{summary['violations'][0]}"
        )
    payload = [{"identity": row["identity"], "arabic": row["proposal"]["arabic"]} for row in bundle["rows"]]
    return {
        "payload": payload,
        "manifest": {
            "schema": BUNDLE_SCHEMA,
            "bundle_sha256": canonical_sha256(bundle),
            "governed_manifest": governed_manifest_path,
            "candidate_export": manifest["export_path"],
            "candidate_export_sha256": export_sha,
            "candidate_company": manifest.get("company"),
            "candidate_identity_count": len(identities),
            "row_count": summary["row_count"],
            "approved_count": summary["approved_count"],
            "exception_count": len(summary["reviewable_exceptions"]),
            "reviewable_exceptions": summary["reviewable_exceptions"],
            "workflow": WORKFLOW,
            "note": "In-memory payload only, bound to the private export via the governed manifest. Owner approval and explicit import authorization remain separate gates.",
        },
    }


def rollback_note():
    """Engineering-only module: rollback = remove this file + its test module.
    No database state, no Arabic values, and no import is created here."""
    return (
        "Review-bundle schema/validator are pure and non-mutating. Rollback = "
        "delete construction/services/account_review_bundle.py and "
        "construction/tests/test_stage4_review_bundle.py. No data to reverse."
    )
