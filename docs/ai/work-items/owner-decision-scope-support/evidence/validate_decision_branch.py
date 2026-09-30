"""Validate the G1-proposed DECISION branch by injecting it into a COPY of the real schema."""
import json, copy, tempfile, pathlib
from jsonschema import Draft202012Validator, FormatChecker

real = json.loads(pathlib.Path("orchestrator/schemas/v1/approval-token.json").read_text())

DECISION = {
  "type": "object", "additionalProperties": False,
  "properties": {
    "schema_version": {"const": 1},
    "token_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
    "work_item": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
    "gate_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
    "issuer": {"type": "string", "minLength": 1},
    "issued_utc": {"type": "string", "format": "date-time", "pattern": "Z$"},
    "status": {"enum": ["ISSUED", "RESERVED", "CONSUMED", "INVALIDATED"]},
    "scope": {"const": "DECISION"},
    "disposition": {"enum": ["RATIFIED", "WAIVED", "REJECTED", "SUPERSEDED"]},
    "decision_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "candidate_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "plan_revision_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "scope_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "resolved_finding_digests": {"type": "array", "minItems": 1, "uniqueItems": True,
                    "items": {"type": "string", "pattern": "^[0-9a-f]{64}$"}},
    "repository_id": {"type": "string", "minLength": 1},
    "branch": {"type": "string", "minLength": 1},
    "expected_parent_sha": {"type": "string", "pattern": "^([0-9a-f]{40}|[0-9a-f]{64})$"},
    "supersedes_decision_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
  },
  "required": ["schema_version","token_id","work_item","gate_id","issuer","issued_utc","status","scope",
               "disposition","decision_hash","candidate_id","plan_revision_hash","scope_hash",
               "resolved_finding_digests","repository_id","branch","expected_parent_sha"],
}
schema = copy.deepcopy(real)
schema["oneOf"].append(DECISION)
V = Draft202012Validator(schema, format_checker=FormatChecker())

H = "a"*64
good = {"schema_version":1,"token_id":"owner-decision-44","work_item":"workspace-desk-coverage",
        "gate_id":"decision-44","issuer":"owner","issued_utc":"2026-09-30T00:00:00Z","status":"ISSUED",
        "scope":"DECISION","disposition":"RATIFIED","decision_hash":H,"candidate_id":"b"*64,
        "plan_revision_hash":"c"*64,"scope_hash":"d"*64,"resolved_finding_digests":["2060223e47de5207bcb353e90c12510fe43b055702ffd07c587ca335d884b9ca"],
        "repository_id":"/repo","branch":"feature/x","expected_parent_sha":"4123646bd8b7016abad8c276cea36a58d6cbfb3a"}

cases = [
    ("valid DECISION token", good, True),
    ("missing decision_hash", {k:v for k,v in good.items() if k!="decision_hash"}, False),
    ("non-hex decision_hash", {**good,"decision_hash":"ZZZ"}, False),
    ("empty resolved_finding_digests", {**good,"resolved_finding_digests":[]}, False),
    ("non-hex digest entry", {**good,"resolved_finding_digests":["SCP-006"]}, False),
    ("duplicate digests", {**good,"resolved_finding_digests":[H,H]}, False),
    ("bad disposition", {**good,"disposition":"APPROVED"}, False),
    ("unknown extra property", {**good,"rogue":"x"}, False),
    ("removed rationale_sha256 rejected", {**good,"rationale_sha256":"e"*64}, False),
    ("bad expected_parent_sha", {**good,"expected_parent_sha":"nothex"}, False),
    ("missing expected_parent_sha", {k:v for k,v in good.items() if k!="expected_parent_sha"}, False),
    ("supersedes non-hex", {**good,"supersedes_decision_hash":"nope"}, False),
    ("valid + supersedes", {**good,"supersedes_decision_hash":"f"*64}, True),
]
ok = True
for name, doc, should_pass in cases:
    errs = list(V.iter_errors(doc))
    passed = not errs
    status = "OK " if passed == should_pass else "BAD"
    if passed != should_pass: ok = False
    detail = "" if passed else f"  <- {errs[0].message[:70]}"
    print(f"  [{status}] expect={'accept' if should_pass else 'reject':<6} {name}{detail}")

# Regression: pre-existing scopes must still validate and stay unambiguous
print("\n  regression on existing scopes:")
plan = {"schema_version":2,"token_id":"t","work_item":"w","gate_id":"g","issuer":"owner",
        "issued_utc":"2026-09-30T00:00:00Z","status":"ISSUED","scope":"PLAN","plan_revision_hash":H,
        "scope_hash":H,"roles_hash":H,"repository_id":"/r","branch":"b","stages":["1"]}
commit = {"schema_version":1,"token_id":"t","work_item":"w","gate_id":"g","issuer":"owner",
        "issued_utc":"2026-09-30T00:00:00Z","status":"ISSUED","scope":"COMMIT","candidate_id":H,
        "manifest_hash":H,"repository_id":"/r","branch":"b","expected_parent_sha":"a"*40,
        "expected_tree_oid":"b"*40,"job_id":"j"}
for name, doc in (("PLAN v2", plan), ("COMMIT", commit)):
    errs = list(V.iter_errors(doc))
    if errs: ok = False
    print(f"    [{'OK ' if not errs else 'BAD'}] {name} still validates ({len(errs)} errors)")
print("\n  note: SCP-006/007/008 are NOT ledger finding_ids (all null in seq 45);")
print("        tokens bind to snapshot.reproduction_digest instead (SPEC §2.3).")
print("\nSCHEMA BRANCH VALID:", ok)
