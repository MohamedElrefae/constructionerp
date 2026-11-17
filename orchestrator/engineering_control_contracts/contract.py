"""Single source for v1 JSON Schema 2020-12 / OpenAPI 3.1 artifacts.

No server, engine construction, provider discovery, filesystem fetch or dispatch.
Run with --write to regenerate the two checked-in artifacts in this package only.
"""

import json
from pathlib import Path

VERSION = "1.0.0-offline"
BASE = "/engineering/v1"
# JSON Schema patterns search substrings. Reject any forbidden character rather
# than relying on `$`, which can match before a final newline across engines.
# These character classes/`not`/length bounds use portable JSON Schema semantics.
ID = {
    "type": "string",
    "minLength": 1,
    "maxLength": 96,
    "pattern": "^[a-zA-Z0-9]",
    "not": {"pattern": "[^a-zA-Z0-9_-]"},
}
HASH = {"type": "string", "minLength": 64, "maxLength": 64, "not": {"pattern": "[^a-f0-9]"}}
GIT_SHA = {**HASH, "minLength": 40, "maxLength": 40}
GOVERNED_ROLES = ("architect", "reviewer", "builder", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3")
# Syntactic option vocabulary only: real advertised availability and qualification
# are separate checks, never implied by acceptance of a reasoning token here.
REASONING = {**ID, "maxLength": 64}
TEXT = {"type": "string", "minLength": 1, "maxLength": 2048}
REV = {"type": "integer", "minimum": 0, "maximum": 9007199254740991}
TIME = {"type": "string", "format": "date-time", "maxLength": 40}


def obj(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def ref(name):
    return {"$ref": "#/$defs/" + name}


def arr(items, maximum=100, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}


def enum(*values):
    return {"type": "string", "enum": list(values)}


# All live mappings are disabled. fake_enabled is an offline test capability only.
OPERATIONS = [
    ("list_work_items", "get", "/work-items", "Query", "WorkItemList", True),
    ("get_work_item", "get", "/work-items/{id}", "Query", "WorkItem", True),
    ("events", "get", "/work-items/{id}/events", "Query", "Events", True),
    ("review_context", "get", "/work-items/{id}/review-context", "Query", "Review", True),
    ("capabilities", "get", "/capabilities", "Query", "Capabilities", True),
    ("create_work_item", "post", "/work-items", "Create", "Receipt", False),
    ("plan", "post", "/work-items/{id}/plan", "Plan", "Receipt", False),
    ("assignments", "post", "/work-items/{id}/assignments", "Assignments", "Receipt", False),
    ("execution_request", "post", "/work-items/{id}/execution-requests", "Execute", "Receipt", True),
    ("operation", "get", "/operations/{id}", "Query", "Receipt", True),
    ("job", "get", "/jobs/{id}", "Query", "Job", True),
    ("observations", "post", "/jobs/{id}/observations", "Observation", "Receipt", True),
    ("results", "post", "/jobs/{id}/results", "Result", "Receipt", True),
    ("decisions", "post", "/work-items/{id}/decisions", "Decision", "Receipt", True),
    ("pause", "post", "/work-items/{id}/pause", "Reason", "Receipt", True),
    ("resume", "post", "/work-items/{id}/resume", "Reason", "Receipt", True),
    ("cancel", "post", "/jobs/{id}/cancel", "Reason", "Receipt", True),
    ("evidence", "get", "/evidence/{id}", "Query", "Artifact", True),
    ("evidence_content", "get", "/evidence/{id}/content", "Query", "Content", True),
]


def schemas():
    d = {}
    d["Query"] = obj({"limit": {"type": "integer", "minimum": 1, "maximum": 100}, "after": REV}, [])
    d["Assignment"] = obj(
        {
            "provider_instance": ID,
            "account_ref": ID,
            "model": TEXT,
            "runtime": enum("native"),
            "binary_sha256": HASH,
            "binary_version": TEXT,
            "prompt_sha256": HASH,
            "transport": enum("native-cli"),
            "role": enum(*GOVERNED_ROLES),
            "options": obj({"reasoning": REASONING}),
        }
    )
    d["Binding"] = obj(
        {
            "work_item_id": ID,
            "project_id": ID,
            "stage": ID,
            "repository_id": ID,
            "branch": TEXT,
            "base_commit": GIT_SHA,
            "candidate_id": HASH,
            "manifest_sha256": HASH,
            "context_sha256": HASH,
            "plan_sha256": HASH,
            "scope_sha256": HASH,
            "roles_sha256": HASH,
        }
    )
    d["Artifact"] = obj(
        {
            "artifact_id": ID,
            "work_item_id": ID,
            "job_id": ID,
            "sha256": HASH,
            "size_bytes": {"type": "integer", "minimum": 0, "maximum": 65536},
            "media_type": enum("text/plain", "application/json"),
            "complete": {"type": "boolean"},
            "truncated": {"type": "boolean"},
            "registered_by": enum("coordinator"),
        }
    )
    d["Evidence"] = obj(
        {
            "schema_version": {"const": VERSION},
            "evidence_id": ID,
            "job_id": ID,
            "attempt": {"type": "integer", "minimum": 1, "maximum": 100},
            "role": enum(*GOVERNED_ROLES),
            "binding": ref("Binding"),
            "assignment": ref("Assignment"),
            "environment_id": ID,
            "runtime_version": TEXT,
            "session_id": ID,
            "observer": enum("agent", "native_monitor", "coordinator"),
            "check_id": ID,
            "action_ref": ID,
            "started_at": TIME,
            "finished_at": TIME,
            "status": enum("pass", "fail", "blocked", "not_run", "skipped"),
            "artifacts": arr(ref("Artifact"), 20, 1),
            "limitations": arr(TEXT, 20),
        }
    )
    mut = {"expected_revision": REV}
    d["Create"] = obj({**mut, "project_id": ID, "base_id": ID, "title": TEXT, "brief": TEXT})
    d["Plan"] = obj({**mut, "proposal_artifact_id": ID})
    d["Assignments"] = obj({**mut, "assignments": arr(ref("Assignment"), 10, 1)})
    d["Execute"] = obj({**mut, "runtime_preference": enum("native", "t3")})
    d["Decision"] = obj(
        {
            **mut,
            "decision": enum(
                "approve_plan",
                "reject_plan",
                "accept_business",
                "approve_commit",
                "approve_deployment",
                "approve_import",
                "approve_dry_run",
                "resolve_findings",
            ),
            "gate_id": ID,
            "review_snapshot_id": ID,
        }
    )
    d["Reason"] = obj({**mut, "reason": TEXT})
    d["Observation"] = obj(
        {
            **mut,
            "job_id": ID,
            "attempt": {"type": "integer", "minimum": 1, "maximum": 100},
            "runtime_ref": ID,
            "state": enum("running", "terminated"),
            "observed_at": TIME,
        }
    )
    d["Result"] = obj({**mut, "evidence": ref("Evidence")})
    d["Receipt"] = obj(
        {
            "schema_version": {"const": VERSION},
            "operation_id": ID,
            "receipt_id": ID,
            "resource_id": ID,
            "revision": REV,
            "effect": enum(
                "approval_only",
                "initialization_only",
                "execution_requested",
                "pause_requested",
                "resume_requested",
                "cancellation_requested",
                "observation_recorded",
                "result_proposed",
            ),
            "effect_state": enum("completed", "pending", "uncertain", "failed"),
            "runtime": enum("native"),
            "job_ids": arr(ID, 10),
            "execution_complete": {"const": False},
        }
    )
    d["Job"] = obj(
        {
            "job_id": ID,
            "work_item_id": ID,
            "attempt": {"type": "integer", "minimum": 1, "maximum": 100},
            "binding": ref("Binding"),
            "assignment": ref("Assignment"),
            "session_id": ID,
            "runtime_ref": ID,
            "state": enum("intent", "running", "uncertain", "cancel_pending", "terminated"),
            "environment_id": ID,
            "runtime_version": TEXT,
            "result_accepted": {"type": "boolean"},
        }
    )
    d["WorkItem"] = obj(
        {
            "work_item_id": ID,
            "revision": REV,
            "binding": ref("Binding"),
            "paused": {"type": "boolean"},
            "approval_recorded": {"type": "boolean"},
        }
    )
    d["WorkItemList"] = obj({"items": arr(ref("WorkItem")), "next_cursor": REV})
    d["Review"] = obj({"review_snapshot_id": ID, "gate_id": ID, "revision": REV, "binding": ref("Binding")})
    d["Events"] = obj(
        {
            "events": arr(
                obj(
                    {
                        "sequence": REV,
                        "kind": enum("grant", "intent", "observation", "result", "pause", "resume", "cancel"),
                        "resource_id": ID,
                    }
                )
            ),
            "next_cursor": REV,
            "truncated": {"type": "boolean"},
        }
    )
    d["Capabilities"] = obj(
        {
            "schema_version": {"const": VERSION},
            "mode": enum("offline_fake_only"),
            "production_enabled": {"const": False},
            "t3_execution_enabled": {"const": False},
            "qualified_assignments": arr(ref("Assignment"), 10),
            "operations": arr(
                obj(
                    {
                        "operation_id": ID,
                        "live_enabled": {"const": False},
                        "fake_enabled": {"type": "boolean"},
                    }
                ),
                19,
                19,
            ),
        }
    )
    d["Content"] = obj(
        {
            "artifact": ref("Artifact"),
            "text": {"type": "string", "maxLength": 65536},
            "preview_truncated": {"type": "boolean"},
        }
    )
    d["Error"] = obj(
        {
            "schema_version": {"const": VERSION},
            "error": enum(
                "invalid_request",
                "unauthenticated",
                "forbidden",
                "not_found",
                "conflict",
                "unsupported_operation",
                "unsupported_decision",
                "unsupported_runtime",
                "unsupported_assignment",
                "unsupported_version",
                "invalid_evidence",
                "resource_limit",
                "uncertain_outcome",
            ),
            "message": TEXT,
            "retryable": {"type": "boolean"},
        }
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": d}


def openapi():
    paths = {}
    for name, method, path, request, response, fake in OPERATIONS:
        op = {
            "operationId": name,
            "x-live-enabled": False,
            "x-offline-fake-enabled": fake,
            "description": "Disabled in production. Synthetic offline contract only; no listener is supplied.",
            "security": [{"TrustedIngress": []}],
            "parameters": [
                {
                    "name": "Contract-Version",
                    "in": "header",
                    "required": True,
                    "schema": {"type": "string", "enum": [VERSION]},
                }
            ],
            "responses": {
                "200": {
                    "description": "Offline response; receipt is not execution completion",
                    "content": {
                        "application/json": {"schema": {"$ref": f"./schemas.json#/$defs/{response}"}}
                    },
                }
            },
        }
        if "{id}" in path:
            op["parameters"].append({"name": "id", "in": "path", "required": True, "schema": ID})
        if method == "post":
            op["parameters"].append(
                {"name": "Idempotency-Key", "in": "header", "required": True, "schema": ID}
            )
            op["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": f"./schemas.json#/$defs/{request}"}}},
            }
        else:
            for key, value in schemas()["$defs"]["Query"]["properties"].items():
                op["parameters"].append({"name": key, "in": "query", "schema": value})
        for code in (400, 401, 403, 404, 409, 413, 422, 501, 503):
            op["responses"][str(code)] = {
                "description": "Explicit denial; no fallback",
                "content": {"application/json": {"schema": {"$ref": "./schemas.json#/$defs/Error"}}},
            }
        paths.setdefault(BASE + path, {})[method] = op
    return {
        "openapi": "3.1.0",
        "info": {"title": "Engineering Control — OFFLINE CONTRACT", "version": VERSION},
        "paths": paths,
        "components": {
            "securitySchemes": {
                "TrustedIngress": {
                    "type": "mutualTLS",
                    "description": "Placeholder transport requirement, NOT implemented auth. Server authentication alone does not prove human identity; see THREAT_MODEL.md.",
                }
            }
        },
    }


def write_artifacts():
    target = Path(__file__).parent / "v1"
    for name, document in (("schemas.json", schemas()), ("openapi.json", openapi())):
        (target / name).write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", required=True)
    parser.parse_args()
    write_artifacts()
