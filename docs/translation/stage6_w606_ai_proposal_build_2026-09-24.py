"""Build W6-6 proposal dispositions after owner-approved read-only recon."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from stage6_w606_dict import ASSETS_CANDIDATE_TRANSLATIONS

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w606_assets_rows_2026-09-24.csv"
RECON = HERE / "stage6_w606_assets_site_recon_2026-09-24.json"
OUT = HERE / "stage6_w606_proposal_2026-09-24.csv"
SCOPE_SHA = "6f142646ae55cf147751e8d751f10638c79420dfa184855985ecd6068ee63a40"
DECISION_REF = "stage6-W6-6 Assets owner-approved 2026-09-24"
PLACEHOLDER = re.compile(r"\{\d*\}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    assert hashlib.sha256(SCOPE.read_bytes()).hexdigest() == SCOPE_SHA
    scope = read_rows(SCOPE)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["site"] == "v16.localhost" and recon["scope_sha256"] == SCOPE_SHA
    assert recon["total_scope_rows"] == len(scope) == 211
    preserve_rows = recon["site_overrides"]
    preserve = {row["source_text"]: row["translated_text"] for row in preserve_rows}
    assert len(preserve) == len(preserve_rows) == 98
    assert len(set(preserve) & set(ASSETS_CANDIDATE_TRANSLATIONS)) == 0
    assert len(ASSETS_CANDIDATE_TRANSLATIONS) == 113
    keys = {row["source_text"] for row in scope}
    assert set(preserve) | set(ASSETS_CANDIDATE_TRANSLATIONS) == keys, "proposal does not partition exact approved scope"
    assert not recon.get("duplicate_runtime_keys")

    for source, arabic in ASSETS_CANDIDATE_TRANSLATIONS.items():
        assert arabic and arabic != source
        assert sorted(PLACEHOLDER.findall(source)) == sorted(PLACEHOLDER.findall(arabic)), source
        assert source[: len(source) - len(source.lstrip())] == arabic[: len(arabic) - len(arabic.lstrip())], source
        assert source[len(source.rstrip()):] == arabic[len(arabic.rstrip()):], source
        assert not any(char in arabic for char in "\x00\t\r\n")

    fields = [
        "source_text", "proposed_ar", "proposed_disposition",
        "disposition_rationale", "decision_ref", "locations",
    ]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in scope:
            source = row["source_text"]
            if source in preserve:
                disposition, arabic, rationale = (
                    "preserved-site-override", preserve[source],
                    "Preserve the exact live v16.localhost Site Override; do not import or replace.",
                )
            else:
                disposition, arabic, rationale = (
                    "PROPOSED-payload", ASSETS_CANDIDATE_TRANSLATIONS[source],
                    "AI draft; requires independent A1/A2/A3 quorum before release.",
                )
            writer.writerow({
                "source_text": source,
                "proposed_ar": arabic,
                "proposed_disposition": disposition,
                "disposition_rationale": rationale,
                "decision_ref": DECISION_REF,
                "locations": row["locations"],
            })

    payload = OUT.read_bytes()
    proposal_sha = hashlib.sha256(payload).hexdigest()
    print(f"scope={len(scope)} preserve={len(preserve)} proposed_payload={len(ASSETS_CANDIDATE_TRANSLATIONS)}")
    print(f"proposal_sha256={proposal_sha}")
    print(f"proposal={OUT}")


if __name__ == "__main__":
    main()
