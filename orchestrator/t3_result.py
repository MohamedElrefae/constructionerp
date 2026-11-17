"""Decode a real T3 assistant result into the Engine's result wire.

This module does not launch work or grant dispatch authority.  It accepts only
the structured envelope actually present in the T3 assistant response and
binds it to the prepared Engine job and the MCP thread identity.
"""

import json
from copy import deepcopy

from validate import validate_document


class T3ResultError(ValueError):
    """The received T3 response cannot safely represent an Engine result."""


WIRE_KEYS = {"result_json", "explanation", "plan_text"}
BUILDER_BUNDLE_KEY = "builder_bundle_json"
ENGINE_BINDINGS = (
    "job_id",
    "work_item",
    "stage",
    "role",
    "candidate_kind",
    "candidate_id",
    "plan_revision_hash",
    "prompt_version",
)
MAX_STANDARD_ASSISTANT_CHARS = 8_000
MAX_BUILDER_ASSISTANT_CHARS = 50_000


def _extract_wire(text: str, marker: str, *, allow_builder_bundle=False) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise T3ResultError("T3 assistant response is empty")
    max_chars = MAX_BUILDER_ASSISTANT_CHARS if allow_builder_bundle else MAX_STANDARD_ASSISTANT_CHARS
    if len(text) > max_chars:
        raise T3ResultError(f"T3 assistant response exceeds {max_chars} characters")
    if marker not in text:
        raise T3ResultError("T3 result marker is missing")

    # Accept a complete JSON object in a message line, including a fenced or
    # prose-wrapped response. Never synthesize missing wire fields.
    decoder = json.JSONDecoder()
    offset = 0
    while True:
        offset = text.find("{", offset)
        if offset < 0:
            break
        try:
            value, _end = decoder.raw_decode(text, offset)
        except ValueError:
            offset += 1
            continue
        offset += 1
        keys = set(value) if isinstance(value, dict) else set()
        accepted_keys = {frozenset(WIRE_KEYS)}
        if allow_builder_bundle:
            accepted_keys.add(frozenset(WIRE_KEYS | {BUILDER_BUNDLE_KEY}))
        if isinstance(value, dict) and frozenset(keys) in accepted_keys:
            if not all(isinstance(value[key], str) for key in WIRE_KEYS):
                raise T3ResultError("T3 result wire fields must be strings")
            if BUILDER_BUNDLE_KEY in value and not isinstance(value[BUILDER_BUNDLE_KEY], str):
                raise T3ResultError("T3 builder bundle wire field must be a string")
            return value
    raise T3ResultError("T3 assistant response has no complete result wire")


def decode_t3_result(
    *, assistant_text: str, job: dict, task_id: str, executed_model: str
) -> tuple[str, dict, dict, list]:
    """Return Engine parse tuple after validating received content and bindings."""
    if not isinstance(job, dict) or not isinstance(job.get("spec"), dict):
        raise T3ResultError("prepared Engine job is malformed")
    if not isinstance(task_id, str) or not task_id.strip():
        raise T3ResultError("T3 thread identity is missing")
    spec = job["spec"]
    expected = spec.get("envelope")
    if not isinstance(expected, dict):
        raise T3ResultError("prepared Engine result envelope is missing")
    if not isinstance(executed_model, str) or not executed_model:
        raise T3ResultError("T3 executed model is missing")
    if executed_model != spec.get("model"):
        raise T3ResultError("T3 executed model does not match prepared model")

    marker = f"ENGINE-T3-RESULT {job.get('job_id', '')}"
    wire = _extract_wire(assistant_text, marker, allow_builder_bundle=job.get("role") == "builder")
    try:
        body = json.loads(wire["result_json"])
    except (TypeError, ValueError) as exc:
        raise T3ResultError("T3 result_json is malformed") from exc
    if not isinstance(body, dict):
        raise T3ResultError("T3 result_json must be an object")

    for field in ENGINE_BINDINGS:
        if body.get(field) != expected.get(field):
            raise T3ResultError(f"T3 result binding mismatch: {field}")
    if body.get("model") != executed_model:
        raise T3ResultError("T3 result model does not match executed model")
    # Engine.accept later replaces these runtime-owned fields using the actual
    # process observation and locally captured evidence. Validate against that
    # canonical shape here; validating the model's raw evidence_paths/session
    # fields would reject the prepared envelope (which intentionally starts
    # with empty evidence_paths) before Engine can add its authoritative refs.
    validation_body = deepcopy(body)
    validation_body.update(
        tool=spec.get("tool"),
        model=executed_model,
        session_id=task_id,
        dispatch_mode="manual",
        started_utc="2026-01-01T00:00:00Z",
        finished_utc="2026-01-01T00:00:00Z",
        evidence_paths=[
            {
                "artifact_id": f"{job['job_id']}-native-events",
                "sha256": "0" * 64,
                "visibility": "public",
            }
        ],
    )
    try:
        validate_document("result-envelope", validation_body)
    except Exception as exc:
        raise T3ResultError("T3 result envelope failed schema validation") from exc

    # MCP supplies the thread identity independently of model-generated text.
    # Engine.accept overwrites session_id with this value as well; return it
    # here so duplicate-session checks are bound to the actual T3 thread.
    return task_id, body, wire, []
