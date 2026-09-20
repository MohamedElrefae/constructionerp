"""Explicit, harmless native adapter probes. Never engineering or pilot evidence."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    destination = parser.parse_args().report
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "orchestrator"))
    from adapters import WIRE_SCHEMA, parse_output
    from core import write_json

    pins = json.loads((root / "orchestrator/roles.json").read_text())
    records = []
    for role in ("reviewer", "builder"):
        pin = pins[role]
        private = Path(tempfile.mkdtemp(prefix="adapter-" + role + "-", dir=root / "orchestrator/var/probes"))
        scratch = Path(tempfile.mkdtemp(prefix="workflow-transport-root-"))
        work = scratch / "work-item"
        work.mkdir()
        write_json(private / "wire-schema.json", WIRE_SCHEMA)
        spec = dict(
            probe=True,
            job_id="transport-" + role,
            root=str(scratch),
            work_item_root=str(work),
            runtime=str(private),
            role=role,
            tool=pin["tool"],
            binary=pin["binary"],
            model=pin["model"],
            effort=pin.get("effort"),
            wire_schema=str(private / "wire-schema.json"),
            hard_timeout=90,
            soft_timeout=60,
            prompt='Transport capability probe only. Use no tools, read no files, modify nothing. Return exactly this JSON: {"result_json":"{}","explanation":"Native transport probe only; not engineering evidence.","plan_text":""}',
        )
        write_json(private / "spec.json", spec)
        subprocess.run(
            [
                str(root / "orchestrator/.venv/bin/python"),
                str(root / "orchestrator/worker.py"),
                str(private / "spec.json"),
            ],
            check=True,
            timeout=100,
        )
        terminal = json.loads((private / "terminal.json").read_text())
        record = dict(
            role=role,
            tool=pin["tool"],
            model=pin["model"],
            exit_code=terminal.get("exit_code"),
            phase=terminal["phase"],
        )
        try:
            session, body, _wire, _events = parse_output((private / "stdout.jsonl").read_text(), pin["tool"])
            record.update(
                session_id=session,
                wire_valid=body == {},
                sandbox_transport_pass=terminal.get("exit_code") == 0,
            )
        except Exception:
            record.update(sandbox_transport_pass=False, error_type="TRANSPORT_PARSE_FAILED")
        records.append(record)
    report = {
        "schema_version": 1,
        "purpose": "Native sandbox/transport capability only; not pilot evidence",
        "records": records,
    }
    write_json(destination, report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
