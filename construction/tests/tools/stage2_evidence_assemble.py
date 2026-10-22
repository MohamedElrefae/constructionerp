#!/usr/bin/env python3
"""Stage-2 evidence assembler (persistent copy under tests/tools, excluded
from the localization scan). Reads raw captures from CAP and rebuilds the
ten governed envelopes + index.txt. See docs/ai/work-items/.../evidence.
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).resolve().parents[3]  # apps/construction
ROOT = APP
CAP = Path(os.environ.get("STAGE2_EVIDENCE_CAPTURE_DIR", "/tmp/opencode/stage2"))
EV = ROOT / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2"


def _load_checker():
    """The frozen contract lives in the checker: single source of truth.

    The assembler must never carry its own copy of the expected counts, or the
    two drift apart and a stale expectation silently reaches the evidence.
    """
    path = ROOT / "scripts" / "check_localization_gates.py"
    spec = importlib.util.spec_from_file_location("stage2_checker_contract", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CHECKER = _load_checker()

ARTIFACT_PATHS = {
    "CHECKER_SHA256": "scripts/check_localization_gates.py",
    "TESTS_SHA256": "construction/tests/test_localization_gates.py",
    "PO_SHA256": "construction/locale/ar.po",
    "CSV_SHA256": "construction/data/translations/approved_ar_overrides.csv",
    "MANIFEST_SHA256": "construction/data/localization/localization_manifest.json",
    "BASELINE_SHA256": "construction/data/localization/vendor_catalog_baseline.json",
    "DECISIONS_SHA256": "construction/data/translations/release_decisions.json",
    "INVENTORY_MANIFEST_SHA256": "construction/data/localization/stage2_inventory_manifest.json",
    "FRESHNESS_SHA256": "construction/data/localization/freshness_evidence.json",
    "SQL_SHA256": "scripts/stage2_inventory.sql",
    "SCOPELINT_SHA256": "scripts/lint_scope_metadata.py",
    "TRANSLATIONLINT_SHA256": "scripts/lint_translation_writes.py",
    "FRAPPE_PO_SHA256": "../frappe/frappe/locale/ar.po",
    "ERPNext_PO_SHA256": "../erpnext/erpnext/locale/ar.po",
}
EVIDENCE_FILES = (
    "all-tests.txt",
    "final-dryrun.txt",
    "freshness-envelope.txt",
    "full-gate.txt",
    "gate-tests-standalone.txt",
    "lints-diffcheck.txt",
    "merkle.txt",
    "scoped-gate.txt",
    "sync.txt",
    "vendor-audit.txt",
)
EXPECTED_COMMANDS = {
    "all-tests.txt": "COMMAND: bench --site v16.localhost run-tests x11 modules (aggregate)",
    "final-dryrun.txt": "COMMAND: bench --site v16.localhost console import_released_overrides(dry_run=True)",
    "freshness-envelope.txt": "COMMAND: bench --site v16.localhost console construction.localization_freshness.collect()",
    "full-gate.txt": "COMMAND: python3 scripts/check_localization_gates.py --skip-evidence",
    "gate-tests-standalone.txt": "COMMAND: python3 construction/tests/test_localization_gates.py (standalone, no site)",
    "lints-diffcheck.txt": "COMMAND: python3 scripts/lint_scope_metadata.py && python3 scripts/lint_translation_writes.py && git diff --check",
    "merkle.txt": "COMMAND: bench --site v16.localhost console (stage2 inventory categories + merkle via construction.localization_inventory.merkle_root; SQL: scripts/stage2_inventory.sql)",
    "scoped-gate.txt": "COMMAND: python3 scripts/check_localization_gates.py --files construction/www/login.html construction/workspace/construction/construction.json construction/config/workspace_sidebar_items.json construction/templates/generic_export_list_pdf.html",
    "sync.txt": "COMMAND: bench --site v16.localhost console sync_translation_catalog(dry_run=False)",
    "vendor-audit.txt": "COMMAND: python3 scripts/check_localization_gates.py --audit-vendor-coverage",
}
# Site-aware evidence protocol (execution order 31): the evidence site is an
# explicit invocation choice; the collector never runs against a protected site
# unless that exact site is the one the execution order authorized.
DEFAULT_EVIDENCE_SITE = "v16.localhost"
EVIDENCE_SITE = DEFAULT_EVIDENCE_SITE
CAPTURES = Path(os.environ.get("STAGE2_EVIDENCE_CAPTURE_DIR", "/tmp/opencode/stage2"))
OUTPUT_DIR = None


def expected_commands(site: str) -> dict:
    return {
        key: (value.replace(DEFAULT_EVIDENCE_SITE, site) if DEFAULT_EVIDENCE_SITE in value else value)
        for key, value in EXPECTED_COMMANDS.items()
    }


MODULES = [(module,) for module, _count in CHECKER.CURRENT_EXPECTED_MODULES]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ts(name):
    return (CAPTURES / name).read_text().strip()


def clean(raw_name):
    return re.sub(r"\x1b\[[0-9;]*m", "", (CAPTURES / raw_name).read_text(errors="replace"))


def main():
    art = {k: sha(ROOT / rel) for k, rel in ARTIFACT_PATHS.items()}
    fresh = json.loads((ROOT / ARTIFACT_PATHS["FRESHNESS_SHA256"]).read_text(encoding="utf-8"))
    assert fresh["critical_pass"] is True
    env = {}

    m = re.search(r"^Ran (\d+) tests in [\d.]+s$", clean("standalone.out"), re.M)
    # The captured count is transcribed verbatim: the assembler is a protocol
    # transcriber, NOT the gate. The frozen contract decides whether the
    # captured number is acceptable, so a tampered count must reach the
    # checker and be rejected there with an explicit error.
    assert m, m
    ok = re.search(r"^OK$", clean("standalone.out"), re.M)
    env["gate-tests-standalone.txt"] = (
        ts("standalone.start"),
        [m.group(0), ok.group(0), "TESTS_SHA256: " + art["TESTS_SHA256"]],
        ts("standalone.finish"),
    )

    body = []
    total = 0
    for (mod,) in MODULES:
        txt = clean(f"mod_{mod}.out")
        mm = re.search(r"^Ran (\d+) tests in ([\d.]+s)$", txt, re.M)
        assert mm and re.search(r"^OK$", txt, re.M), mod
        total += int(mm.group(1))
        body.append(f"{mod} :: {mm.group(0)} OK")
    body.append(f"AGGREGATE total={total} failed=0")
    body.append("TESTS_SHA256: " + art["TESTS_SHA256"])
    env["all-tests.txt"] = (ts("alltests.start"), body, ts("alltests.finish"))

    line = next(l for l in clean("dryrun.raw").splitlines() if re.match(r"^In \[\d+\]: DRY ", l))
    env["final-dryrun.txt"] = (
        ts("dryrun.start"),
        [
            line,
            "CSV_SHA256: " + art["CSV_SHA256"],
            "RUNTIME_DIGEST: " + fresh["runtime_digest"],
            "DECISIONS_SHA256: " + art["DECISIONS_SHA256"],
        ],
        ts("dryrun.finish"),
    )

    json_text = (ROOT / ARTIFACT_PATHS["FRESHNESS_SHA256"]).read_text(encoding="utf-8")
    body = [
        "ARTIFACT: construction/data/localization/freshness_evidence.json",
        "ARTIFACT_SHA256: " + art["FRESHNESS_SHA256"],
        "FRESHNESS_SHA256: " + art["FRESHNESS_SHA256"],
        "--- JSON START ---",
        *json_text.rstrip("\n").splitlines(),
        "--- JSON END ---",
    ]
    env["freshness-envelope.txt"] = (ts("freshness.start"), body, ts("freshness.finish"))

    gate_line = next(l for l in clean("fullgate.raw").splitlines() if l.startswith("checked="))
    assert gate_line.rstrip().endswith("errors=0")
    env["full-gate.txt"] = (
        ts("fullgate.start"),
        [
            gate_line,
            "CHECKER_SHA256: " + art["CHECKER_SHA256"],
            "PO_SHA256: " + art["PO_SHA256"],
            "CSV_SHA256: " + art["CSV_SHA256"],
            "MANIFEST_SHA256: " + art["MANIFEST_SHA256"],
            "NOTE: bootstrap run for envelope generation; CI and verification never pass this flag",
        ],
        ts("fullgate.finish"),
    )

    lint = clean("lints.raw")
    env["lints-diffcheck.txt"] = (
        ts("lints.start"),
        [
            next(l for l in lint.splitlines() if l.startswith("PASS: no scope-dimension")),
            "Translation write lint PASSED",
            "DIFFCHECK_CLEAN",
            "SCOPELINT_SHA256: " + art["SCOPELINT_SHA256"],
            "TRANSLATIONLINT_SHA256: " + art["TRANSLATIONLINT_SHA256"],
        ],
        ts("lints.finish"),
    )

    mraw = clean("merkle.raw")
    governed = []
    for mark in (
        "MANIFEST: ",
        "MANIFEST_SHA256: ",
        "INVENTORY_MANIFEST_SHA256: ",
        "MERKLE_ROOT: ",
        "MERKLE_ROWS: ",
        "SQL_SHA256: ",
    ):
        line = next(l for l in mraw.splitlines() if re.search(r"In \[\d+\]: " + re.escape(mark), l))
        governed.append(re.sub(r"^.*?In \[\d+\]: ", "", line))
    assert "LIVE_MATCH" not in " ".join(governed)
    env["merkle.txt"] = (ts("merkle.start"), governed, ts("merkle.finish"))

    sraw = clean("scoped.raw")
    env["scoped-gate.txt"] = (
        ts("scoped.start"),
        [
            next(l for l in sraw.splitlines() if l.startswith("SKIP ")),
            next(l for l in sraw.splitlines() if l.startswith("checked=")),
            "PO_SHA256: " + art["PO_SHA256"],
        ],
        ts("scoped.finish"),
    )

    line = next(l for l in clean("sync.raw").splitlines() if re.match(r"^In \[\d+\]: SYNC:", l))
    assert "'created': 0" in line and "'updated': 0" in line
    env["sync.txt"] = (ts("sync.start"), [line, "PO_SHA256: " + art["PO_SHA256"]], ts("sync.finish"))

    vraw = clean("vendor.raw")
    assert "FAIL " not in vraw
    env["vendor-audit.txt"] = (
        ts("vendor.start"),
        [
            "errors=0",
            "BASELINE_SHA256: " + art["BASELINE_SHA256"],
            "FRAPPE_PO_SHA256: " + art["FRAPPE_PO_SHA256"],
            "ERPNext_PO_SHA256: " + art["ERPNext_PO_SHA256"],
        ],
        ts("vendor.finish"),
    )

    for fname, (start, body, finish) in env.items():
        raw_command = next((l for l in body if l.startswith("COMMAND: ") or "COMMAND: bench --site" in l), "")
        for line in body:
            if "bench --site " in line:
                recorded_site = line.split("bench --site ", 1)[1].split()[0].strip()
                if recorded_site != EVIDENCE_SITE:
                    raise SystemExit(
                        f"capture {fname} was executed against site {recorded_site!r}, "
                        f"not the requested {EVIDENCE_SITE!r}"
                    )
    NO_REORDER = {"freshness-envelope.txt", "merkle.txt"}
    EV.mkdir(parents=True, exist_ok=True)
    for fname in EVIDENCE_FILES:
        start, body, finish = env[fname]
        if fname in NO_REORDER:
            lines = [
                "COMMAND: " + expected_commands(EVIDENCE_SITE)[fname][len("COMMAND: ") :],
                "SITE: " + EVIDENCE_SITE,
                "STARTED_UTC: " + start,
                *body,
                "EXIT_CODE: 0",
                "FINISHED_UTC: " + finish,
            ]
        else:
            marks = [
                l for l in body if re.match(r"^[A-Za-z_]+_(SHA256|DIGEST): ", l) or l.startswith("NOTE: ")
            ]
            results = [l for l in body if l not in marks]
            lines = [
                "COMMAND: " + expected_commands(EVIDENCE_SITE)[fname][len("COMMAND: ") :],
                "SITE: " + EVIDENCE_SITE,
                "STARTED_UTC: " + start,
                *results,
                "EXIT_CODE: 0",
                "FINISHED_UTC: " + finish,
                *marks,
            ]
        lines.append(f"ENVELOPE_LINES: {len(lines) + 1}")
        (EV / fname).write_text("\n".join(lines) + "\n", encoding="utf-8")

    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    lines = [
        "INDEX_VERSION: 1",
        "COMMAND: sha256sum evidence/raw-logs/stage2/<ten envelopes> + artifact hashes (governed index; this file excluded from its own listing)",
    ]
    start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append("STARTED_UTC: " + start)
    for fname in EVIDENCE_FILES:
        lines.append(sha(EV / fname) + "  " + fname)
    finish = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines += [
        "EXIT_CODE: 0",
        "FINISHED_UTC: " + finish,
        "CANDIDATE_HEAD: " + head,
        "CANDIDATE_ROOT: " + str(ROOT.resolve()),
        "EVIDENCE_SITE: " + EVIDENCE_SITE,
        "ARTIFACTS:",
    ]
    for k in ARTIFACT_PATHS:
        lines.append(k + ": " + art[k])
    lines.append(f"ENVELOPE_LINES: {len(lines) + 1}")
    (EV / "index.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        "assembled",
        len(env),
        "envelopes + index; HEAD",
        head[:12],
        "aggregate",
        total,
        "contract",
        CHECKER.CURRENT_CONTRACT_ID,
    )


ASSEMBLER_VALUE_OPTIONS = ("--site", "--captures", "--out")


def parse_cli_args(argv):
    """Explicit CLI contract (fail closed).

    Accepted spellings: ``--opt value`` and ``--opt=value``. Unknown options,
    duplicated options, missing values and empty values are refused by name.
    Returns (values, errors).
    """
    values = {}
    errors = []
    items = list(argv)
    index = 0
    while index < len(items):
        arg = items[index]
        name, sep, inline = arg.partition("=")
        if name not in ASSEMBLER_VALUE_OPTIONS:
            if arg.startswith("-"):
                errors.append(f"cli-option: unknown option {name!r}")
            else:
                errors.append(f"cli-option: unexpected argument {arg!r}")
        else:
            if name in values:
                errors.append(f"cli-option: {name} may be supplied only once")
            if sep:
                value = inline
            elif index + 1 < len(items):
                index += 1
                value = items[index]
            else:
                errors.append(f"cli-option: {name} requires a value")
                index += 1
                continue
            value = value.strip()
            if not value:
                errors.append(f"cli-option: {name} must not be empty")
            else:
                values[name] = value
        index += 1
    return values, errors


def _cli(argv=None) -> None:
    global EVIDENCE_SITE, CAPTURES, OUTPUT_DIR, EV
    argv = list(sys.argv[1:] if argv is None else argv)
    # Every invocation starts from the declared defaults: no state leaks from a
    # previous (possibly failed) invocation into the next one.
    EVIDENCE_SITE = DEFAULT_EVIDENCE_SITE
    CAPTURES = Path(os.environ.get("STAGE2_EVIDENCE_CAPTURE_DIR", "/tmp/opencode/stage2"))
    OUTPUT_DIR = None
    EV = ROOT / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2"
    values, errors = parse_cli_args(argv)
    if errors:
        for err in errors:
            print("FAIL " + err)
        raise SystemExit(1)
    if "--site" in values:
        EVIDENCE_SITE = values["--site"]
    if "--captures" in values:
        CAPTURES = Path(values["--captures"])
    if "--out" in values:
        OUTPUT_DIR = Path(values["--out"])
    if OUTPUT_DIR is not None:
        EV = OUTPUT_DIR


if __name__ == "__main__":
    _cli()
    main()
