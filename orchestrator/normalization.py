"""Conservative blocker snapshots bound to owner-mapped requirement source files."""

import re

from core import bytes_hash, digest, within, write_json


def snapshot(finding, root, scope, destination, artifact_id):
    mapping = scope.get("requirement_paths", {})
    requirements = finding["affected_requirements"]
    if not all(mapping.get(r) for r in requirements):
        return None
    paths = sorted({p for r in requirements for p in mapping[r]})
    code = {}
    for name in paths:
        p = within(root, name)
        if not p.is_file():
            return None
        code[name] = bytes_hash(p.read_bytes())
    summary = re.sub(r"\b\d{4}-\d{2}-\d{2}[T ][0-9:.]+Z?\b", "<utc>", finding["summary"])
    summary = re.sub(r"\b(?:job|run)-[a-f0-9]{8,}\b", "<run>", summary)
    material = {
        "reproduction": {"summary": summary, "requirements": sorted(requirements)},
        "relevant_evidence": {"source_hashes": code},
    }
    write_json(destination, material, immutable=True)
    return {
        "reproduction_digest": digest(material["reproduction"]),
        "relevant_evidence_digest": digest(material["relevant_evidence"]),
        "normalized_material_ref": {
            "artifact_id": artifact_id,
            "sha256": digest(material),
            "visibility": "public",
        },
    }
