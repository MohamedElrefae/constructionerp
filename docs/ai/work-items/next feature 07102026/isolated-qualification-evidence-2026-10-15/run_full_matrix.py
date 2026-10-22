import json
import os
import subprocess
from pathlib import Path

LAB = Path(__file__).resolve().parent
modules = [
    "test_boq_properties",
    "test_quantity_revisions",
    "test_variation_orders",
    "test_cost_analysis_engine",
    "test_cost_database_api",
    "test_customer_release_financial_guards",
    "test_boq_transactions",
    "test_boq_wbs_generation",
    "test_boq_structure_conversion",
    "test_boq_structure_delete_safety",
    "test_boq_excel_parser",
    "test_boq_rollup_audit",
    "test_bilingual_install_schema",
    "test_packaged_translation_adoption",
    "test_report_export_authorization",
    "test_boq_legacy_cost_conversion",
    "test_boq_parent_permissions",
    "test_bilingual_desk_link_dispatch",
    "test_stage7_bilingual_reports",
]
os.environ["PYTHONPATH"] = (
    "/home/mohamed/frappe-bench/apps/construction/scripts" + os.pathsep + os.environ.get("PYTHONPATH", "")
)
results = []
for name in modules:
    log = LAB / "logs" / ("matrix-" + name + ".log")
    with log.open("wb") as out:
        p = subprocess.run(
            [
                "/home/mohamed/frappe-bench/env/bin/python",
                "-u",
                str(LAB / "run_lab.py"),
                "cli",
                "--site",
                "f31upgrade.localhost",
                "run-tests",
                "--app",
                "construction",
                "--module",
                "construction.tests." + name,
            ],
            stdout=out,
            stderr=subprocess.STDOUT,
        )
    results.append({"module": name, "exit": p.returncode, "log": log.name})
    print(name, p.returncode, flush=True)
(LAB / "artifacts/targeted-results.json").write_text(json.dumps(results, indent=2))
raise SystemExit(1 if any(r["exit"] for r in results) else 0)
