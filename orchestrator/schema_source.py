"""Versioned wire contracts. This module neither launches agents nor advances state."""

import json
from pathlib import Path

HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
GIT_SHA = {"type": "string", "pattern": "^([0-9a-f]{40}|[0-9a-f]{64})$"}
TEXT = {"type": "string", "minLength": 1}
ID = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}
UTC = {"type": "string", "format": "date-time", "pattern": "Z$"}
ROLES = ["architect", "reviewer", "builder", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3"]
STATUSES = [
    "DRAFT",
    "PLAN_SUBMITTED",
    "NEEDS_REVISION",
    "APPROVED_FOR_BUILD",
    "BUILD_IN_PROGRESS",
    "BUILD_COMPLETE",
    "CHANGES_REQUESTED",
    "VERIFIED_FOR_RELEASE",
    "RELEASED",
    "CANCELLED",
    "PAUSED",
]
FAILURES = [
    "MISSING_BINARY",
    "AUTH_FAILURE",
    "DENIED_ACTION",
    "MALFORMED_RESULT",
    "EVIDENCE_UNAVAILABLE",
    "TIMEOUT",
]
CLASSES = ["implementation_defect", "design_defect", "optional_improvement", "owner_decision"]
SUB_STATUSES = [
    "PROPOSAL_PENDING",
    "PROPOSAL_FROZEN",
    "PANEL_REVIEW",
    "PANEL_RENEWAL",
    "BUNDLE_VALIDATED",
    "AI_R_VERIFICATION",
    "OWNER_PAYLOAD_AUTHORIZATION",
    "DRY_RUN",
    "IMPORT_AUTHORIZATION",
    "IMPORT",
    "POST_IMPORT_EVIDENCE",
    "STAGE_4_VERIFIED",
]


def enum(values):
    return {"enum": values}


def array(items, minimum=0, unique=False):
    return {"type": "array", "items": items, "minItems": minimum, "uniqueItems": unique}


def obj(properties, optional=()):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": [key for key in properties if key not in optional],
    }


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def condition(field, value, then):
    return {"if": {"properties": {field: {"const": value}}, "required": [field]}, "then": then}


# Artifact refs are opaque handles; resolving them against authorized roots is a Phase 1 check.
ARTIFACT = obj({"artifact_id": ID, "sha256": HASH, "visibility": enum(["public", "private"])})
SNAPSHOT = obj(
    {"reproduction_digest": HASH, "relevant_evidence_digest": HASH, "normalized_material_ref": ARTIFACT}
)
FINDING = obj(
    {
        "schema_version": {"const": 1},
        "finding_id": nullable(ID),
        "classification": enum(CLASSES),
        "blocking": {"type": "boolean"},
        "summary": TEXT,
        "affected_requirements": array(ID, 1, True),
        "evidence_refs": array(ARTIFACT),
        "snapshot": nullable(SNAPSHOT),
    }
)
FINDING["allOf"] = [
    condition("classification", "optional_improvement", {"properties": {"blocking": {"const": False}}})
]

RESULT = obj(
    {
        "schema_version": {"const": 1},
        "job_id": ID,
        "work_item": ID,
        "stage": ID,
        "role": enum(ROLES),
        "tool": enum(["codex", "antigravity", "opencode", "synthetic"]),
        "model": nullable(TEXT),
        "session_id": nullable(ID),
        "dispatch_mode": enum(["native", "manual"]),
        "candidate_kind": enum(["code", "stage4-proposal"]),
        "candidate_id": HASH,
        "plan_revision_hash": HASH,
        "prompt_version": HASH,
        "status": enum(["COMPLETE", "FAILED"]),
        "verdict": enum(["PASS", "BLOCKED", "PROPOSED", "FAILED"]),
        "failure_class": nullable(enum(FAILURES)),
        "findings": array(FINDING),
        "evidence_paths": array(ARTIFACT),
        "started_utc": UTC,
        "finished_utc": UTC,
        "export_sha256": HASH,
        "proposal_sha256": HASH,
        "bundle_sha256": HASH,
        "payload_sha256": HASH,
        "dry_run_evidence_digest": HASH,
        "private_artifact_refs": array(ARTIFACT),
    },
    optional=(
        "export_sha256",
        "proposal_sha256",
        "bundle_sha256",
        "payload_sha256",
        "dry_run_evidence_digest",
        "private_artifact_refs",
    ),
)
RESULT["allOf"] = [
    condition(
        "status",
        "COMPLETE",
        {
            "properties": {
                "session_id": ID,
                "model": TEXT,
                "failure_class": {"type": "null"},
                "verdict": enum(["PASS", "BLOCKED", "PROPOSED"]),
                "evidence_paths": array(ARTIFACT, 1),
            }
        },
    ),
    condition(
        "status", "FAILED", {"properties": {"failure_class": enum(FAILURES), "verdict": {"const": "FAILED"}}}
    ),
    condition(
        "verdict",
        "PASS",
        {"properties": {"findings": {"items": {"properties": {"blocking": {"const": False}}}}}},
    ),
    condition(
        "verdict",
        "BLOCKED",
        {
            "properties": {
                "findings": {
                    "contains": {"properties": {"blocking": {"const": True}}, "required": ["blocking"]},
                    "minContains": 1,
                }
            }
        },
    ),
    condition(
        "candidate_kind",
        "stage4-proposal",
        {"required": ["export_sha256", "proposal_sha256", "private_artifact_refs"]},
    ),
    condition(
        "candidate_kind",
        "code",
        {
            "not": {
                "anyOf": [
                    {"required": [field]}
                    for field in (
                        "export_sha256",
                        "proposal_sha256",
                        "bundle_sha256",
                        "payload_sha256",
                        "private_artifact_refs",
                    )
                ]
            }
        },
    ),
]
REPAIR = obj(
    {
        "schema_version": {"const": 1},
        "work_item": ID,
        "stage": ID,
        "job_id": ID,
        "candidate_id": HASH,
        "plan_revision_hash": HASH,
        "scope_hash": HASH,
        "review_round": {"type": "integer", "minimum": 1},
        "contract_refs": array(ARTIFACT, 1),
        "unresolved_findings": array(FINDING, 1),
        "backlog": array(FINDING),
    }
)
REPAIR["properties"]["unresolved_findings"]["items"] = {
    "allOf": [FINDING, {"properties": {"finding_id": ID, "blocking": {"const": True}}}]
}
REPAIR["properties"]["backlog"]["items"] = {
    "allOf": [
        FINDING,
        {"properties": {"classification": {"const": "optional_improvement"}, "blocking": {"const": False}}},
    ]
}

COMMON_TOKEN = {
    "schema_version": {"const": 1},
    "token_id": ID,
    "work_item": ID,
    "gate_id": ID,
    "issuer": TEXT,
    "issued_utc": UTC,
    "status": enum(["ISSUED", "RESERVED", "CONSUMED", "INVALIDATED"]),
}
COMMON_TOKEN_V2 = {
    "schema_version": {"const": 2},
    "token_id": ID,
    "work_item": ID,
    "gate_id": ID,
    "issuer": TEXT,
    "issued_utc": UTC,
    "status": enum(["ISSUED", "RESERVED", "CONSUMED", "INVALIDATED"]),
}
PLAN_TOKEN_V1 = obj(
    {
        **COMMON_TOKEN,
        "scope": {"const": "PLAN"},
        "plan_revision_hash": HASH,
        "scope_hash": HASH,
        "repository_id": TEXT,
        "branch": TEXT,
        "stages": array(ID, 1, True),
    }
)
PLAN_TOKEN_V2 = obj(
    {
        **COMMON_TOKEN_V2,
        "scope": {"const": "PLAN"},
        "plan_revision_hash": HASH,
        "scope_hash": HASH,
        "roles_hash": HASH,
        "repository_id": TEXT,
        "branch": TEXT,
        "stages": array(ID, 1, True),
    }
)
PLAN_TOKEN = PLAN_TOKEN_V2
COMMIT_TOKEN = obj(
    {
        **COMMON_TOKEN,
        "scope": {"const": "COMMIT"},
        "candidate_id": HASH,
        "manifest_hash": HASH,
        "repository_id": TEXT,
        "branch": TEXT,
        "expected_parent_sha": GIT_SHA,
        "expected_tree_oid": GIT_SHA,
        "job_id": ID,
    }
)
ERP_BINDINGS = {
    "erp_descriptor_hash": HASH,
    "candidate_id": HASH,
    "export_sha256": HASH,
    "proposal_sha256": HASH,
    "bundle_sha256": HASH,
    "payload_sha256": HASH,
    "operation": {"const": "set_account_name_ar"},
    "job_id": ID,
}
DRY_TOKEN = obj({**COMMON_TOKEN, **ERP_BINDINGS, "scope": {"const": "DRY_RUN"}}, optional=("proposal_sha256",))
IMPORT_TOKEN = obj(
    {**COMMON_TOKEN, **ERP_BINDINGS, "scope": {"const": "IMPORT"}, "dry_run_evidence_digest": HASH},
    optional=("proposal_sha256",),
)
TOKEN = {"oneOf": [PLAN_TOKEN_V1, PLAN_TOKEN_V2, COMMIT_TOKEN, DRY_TOKEN, IMPORT_TOKEN]}

STATE = obj(
    {
        "schema_version": {"const": 1},
        "authority": {"const": "sqlite-checkpoint-export-only"},
        "work_item": ID,
        "stage": ID,
        "status": enum(STATUSES),
        "revision": {"type": "integer", "minimum": 0},
        "plan_revision_hash": nullable(HASH),
        "roles_hash": nullable(HASH),
        "candidate_id": nullable(HASH),
        "active_jobs": array(ID, unique=True),
        "completed_dependencies": array(ID, unique=True),
        "approval_refs": array(ID, unique=True),
        "escalation": obj(
            {
                "unsuccessful_cycles": {"type": "integer", "minimum": 0},
                "unchanged_rounds": {"type": "integer", "minimum": 0},
                "last_snapshot_digest": nullable(HASH),
            }
        ),
        "pause_reason": nullable(TEXT),
        "resume_to": nullable(enum([s for s in STATUSES if s != "PAUSED"])),
        "stages": {
            "type": "object",
            "additionalProperties": obj(
                {
                    "sub_status": nullable(enum(SUB_STATUSES)),
                    "historical": {"type": "boolean"},
                    "evidence_refs": array(ARTIFACT),
                }
            ),
        },
        "exported_utc": UTC,
    }
)
STATE["allOf"] = [
    condition(
        "status",
        "PAUSED",
        {"properties": {"pause_reason": TEXT, "resume_to": enum([s for s in STATUSES if s != "PAUSED"])}},
    )
]

SCHEMAS = {
    "finding": FINDING,
    "result-envelope": RESULT,
    "repair-packet": REPAIR,
    "approval-token": TOKEN,
    "state-export": STATE,
}


def documents():
    return {
        name: {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": name + " v1", **schema}
        for name, schema in SCHEMAS.items()
    }


if __name__ == "__main__":
    destination = Path(__file__).resolve().parent / "schemas" / "v1"
    destination.mkdir(parents=True, exist_ok=True)
    for name, schema in documents().items():
        (destination / (name + ".json")).write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
