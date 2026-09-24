"""Build W6-5 proposal dispositions after owner-approved read-only recon."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from stage6_w605_dict import CANDIDATE_TRANSLATIONS

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "stage6_w605_setup_rows_2026-09-24.csv"
RECON = HERE / "stage6_w605_setup_site_recon_2026-09-24.json"
OUT = HERE / "stage6_w605_proposal_2026-09-24.csv"
SCOPE_SHA = "e2d672c4a1b479f9cd52c017f76a3c8a8b1b24dced24ed4b5f5c6d8113900a09"
DECISION_REF = "stage6-W6-5 Setup owner-approved 2026-09-24"
PLACEHOLDER = re.compile(r"\{\d*\}")

TECH_13 = {
    "Ampere-Hour", "Ampere-Minute", "Ampere-Second", "Gram-Force",
    "Horsepower-Hours", "Kilogram-Force", "Kilopound-Force", "Kilowatt-Hour",
    "Litre-Atmosphere", "Ounce-Force", "Pound-Force", "Volt-Ampere", "Watt-Hour"
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    assert hashlib.sha256(SCOPE.read_bytes()).hexdigest() == SCOPE_SHA
    scope = read_rows(SCOPE)
    recon = json.loads(RECON.read_text(encoding="utf-8"))
    assert recon["site"] == "v16.localhost" and recon["scope_sha256"] == SCOPE_SHA
    assert recon["scope_rows"] == len(scope) == 469
    preserve_rows = recon["site_overrides"]
    preserve = {row["source_text"]: row["translated_text"] for row in preserve_rows}
    assert len(preserve) == len(preserve_rows) == 107
    assert len(set(preserve) & set(CANDIDATE_TRANSLATIONS)) == 0
    assert len(set(preserve) & TECH_13) == 0
    assert len(set(CANDIDATE_TRANSLATIONS) & TECH_13) == 0
    keys = {row["source_text"] for row in scope}
    assert set(preserve) | set(CANDIDATE_TRANSLATIONS) | TECH_13 == keys, "proposal does not partition exact approved scope"
    assert not recon["nonempty_non_site_overrides"]
    assert not recon["duplicate_runtime_keys"]

    for source, arabic in CANDIDATE_TRANSLATIONS.items():
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
            elif source in TECH_13:
                disposition, arabic, rationale = (
                    "EXCEPTION-technical", "",
                    "Technical UOM/force unit token; retain vendor rendering; no catalog release.",
                )
            else:
                disposition, arabic, rationale = (
                    "PROPOSED-payload", CANDIDATE_TRANSLATIONS[source],
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
    print(f"scope={len(scope)} preserve={len(preserve)} tech_exceptions={len(TECH_13)} proposed_payload={len(CANDIDATE_TRANSLATIONS)}")
    print(f"proposal_sha256={proposal_sha}")
    print(f"proposal={OUT}")


if __name__ == "__main__":
    main()
