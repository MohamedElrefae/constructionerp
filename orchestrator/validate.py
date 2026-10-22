"""Read-only Phase 0 wire/structure checks; never interpret exports as workflow state."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_ROOT = Path(__file__).resolve().parent / "schemas" / "v1"


def validate_document(name, document):
    schema = json.loads((SCHEMA_ROOT / (name + ".json")).read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)
    if name == "result-envelope":
        start = datetime.fromisoformat(document["started_utc"].replace("Z", "+00:00"))
        finish = datetime.fromisoformat(document["finished_utc"].replace("Z", "+00:00"))
        if finish < start:
            raise ValueError("finished_utc precedes started_utc")
        if document["verdict"] == "PROPOSED" and document["role"] not in ("architect", "proposer"):
            raise ValueError("only architect/proposer may return PROPOSED")
        for ref in document.get("private_artifact_refs", []):
            if ref["visibility"] != "private":
                raise ValueError("private artifact reference has public visibility")
        if (
            document["candidate_kind"] == "stage4-proposal"
            and document["role"] == "verifier"
            and document["verdict"] == "PASS"
        ):
            if not all(k in document for k in ("bundle_sha256", "payload_sha256")):
                raise ValueError("Stage 4 verifier PASS requires bundle and payload hashes")
    if name == "repair-packet":
        ids = [f["finding_id"] for f in document["unresolved_findings"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate unresolved finding ID")
    return document


def validate_structure(root, contracts_only=False):
    root = Path(root)
    for name in ("inbox", "outbox"):
        directory = root / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("missing or symlinked directory: " + name)
    state = root / "STATE.json"
    if state.is_symlink():
        raise ValueError("STATE.json must not be a symlink")
    if not state.exists() and contracts_only:
        return "CONTRACTS_ONLY: no checkpoint/STATE.json created; runtime gate not tested"
    validate_document("state-export", json.loads(state.read_text()))
    return "VALID_EXPORT_STRUCTURE: this does not establish checkpoint authority"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    doc = sub.add_parser("document")
    doc.add_argument("schema", choices=[p.stem for p in SCHEMA_ROOT.glob("*.json")])
    doc.add_argument("path", type=Path)
    structure = sub.add_parser("structure")
    structure.add_argument("path", type=Path)
    structure.add_argument("--contracts-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "document":
            validate_document(args.schema, json.loads(args.path.read_text()))
            result = "VALID"
        else:
            result = validate_structure(args.path, args.contracts_only)
        print(json.dumps({"ok": True, "result": result}))
        return 0
    except Exception as exc:
        # No raw input/value or private validation dumps in console output.
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
