"""Record governed release decisions (Stage 2, reviewed operation).

Reads the released payload CSV, transcribes per-role verdicts (independent
review evidence for new rows, historical batch for legacy rows), hashes
decision artifacts, and writes construction/data/translations/release_decisions.json
using the checker's canonical identity scheme. Any later row/artifact change
invalidates the pinned identity.

Usage: python3 scripts/record_release_decisions.py
"""

import csv
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from check_localization_gates import row_decision_id

AI_A1 = {
    "Desktop": ("approve", "high", "/root/ai_a1_arabic"),
    "Workspaces": ("approve", "high", "/root/ai_a1_arabic"),
    "Edit Sidebar": ("approve", "high", "/root/ai_a1_arabic"),
    "Toggle Theme": ("approve", "high", "/root/ai_a1_arabic"),
    "Toggle Full Width": ("approve", "high", "/root/ai_a1_arabic"),
    "Typography Settings": ("approve", "high", "/root/ai_a1_arabic"),
}
AI_A2 = {
    "Desktop": ("accept N/A generic navigation", 0.99, "/root/ai_a2_domain"),
    "Workspaces": ("accept N/A generic navigation", 0.98, "/root/ai_a2_domain"),
    "Edit Sidebar": ("accept N/A UI action", 0.99, "/root/ai_a2_domain"),
    "Toggle Theme": ("accept N/A appearance", 0.99, "/root/ai_a2_domain"),
    "Toggle Full Width": ("accept N/A after dual-meaning review", 0.97, "/root/ai_a2_domain"),
    "Typography Settings": ("accept N/A after dual-meaning review", 0.98, "/root/ai_a2_domain"),
}
BATCH = {"decision": "batch-accepted", "confidence": "batch", "session": "historical pre-v4 workflow"}


def main():
    rows = list(
        csv.DictReader(
            open(ROOT / "construction/data/translations/approved_ar_overrides.csv", encoding="utf-8")
        )
    )
    decisions = {}
    for r in rows:
        if (r.get("release_status") or "").strip() != "Released":
            continue
        src, val = r["source_text"], r["translated_text"]
        refs = sorted(x.strip() for x in (r.get("decision_ref") or "").split(";") if x.strip())
        ref_entries = []
        for ref in refs:
            scheme, _, sub = ref.partition(":")
            content = (ROOT / sub).read_text(encoding="utf-8") if scheme in ("content", "legacy") else ""
            ref_entries.append({"ref": ref, "sha256": hashlib.sha256(content.encode()).hexdigest()})
        if src in AI_A1:
            v1 = {"decision": AI_A1[src][0], "confidence": AI_A1[src][1], "session": AI_A1[src][2]}
            v2 = {"decision": AI_A2[src][0], "confidence": AI_A2[src][1], "session": AI_A2[src][2]}
            v3 = {"decision": "approve", "confidence": "high", "session": "/root/ai_a3_structural"}
        else:
            v1 = v2 = v3 = dict(BATCH)
        parts = [
            r["language"].strip(),
            r["ct_app"].strip(),
            (r.get("context") or "").strip(),
            src,
            val,
            r["a1_reviewer"].strip(),
            r["a1_approved_at"].strip(),
            r["a2_reviewer"].strip(),
            r["a2_approved_at"].strip(),
            r["a3_reviewer"].strip(),
            r["a3_approved_at"].strip(),
            r["release_version"].strip(),
            (r.get("domain") or "").strip(),
            (r.get("references") or "").strip(),
            hashlib.sha256(f"{src}|{val}".encode()).hexdigest(),
        ]
        did = row_decision_id(parts, ref_entries)
        decisions[did] = {
            "language": r["language"],
            "ct_app": r["ct_app"],
            "context": r.get("context") or "",
            "source_text": src,
            "translated_text": val,
            "domain": r.get("domain") or "",
            "reviewers": [r["a1_reviewer"], r["a2_reviewer"], r["a3_reviewer"]],
            "timestamps": [r["a1_approved_at"], r["a2_approved_at"], r["a3_approved_at"]],
            "release_version": r["release_version"],
            "references": r.get("references") or "",
            "proposal": {"arabic": val, "sha256": hashlib.sha256(f"{src}|{val}".encode()).hexdigest()},
            "verdicts": {"AI-A1": v1, "AI-A2": v2, "AI-A3": v3},
            "artifacts": ref_entries,
        }
    doc = {
        "schema": "release-decision/v2",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Reviewed generation. Verdicts transcribed from independent review evidence (six new rows) or marked historical batch (legacy).",
        "decisions": decisions,
    }
    out = ROOT / "construction/data/translations/release_decisions.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"recorded {len(decisions)} decisions -> {out}")


if __name__ == "__main__":
    main()
