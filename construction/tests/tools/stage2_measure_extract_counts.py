#!/usr/bin/env python3
"""Independent live extraction of the per-module test counts (AST based).

This is the cross-validation of the frozen contract: it counts, straight from
the source, every ``test_*`` method that ``unittest.TestLoader`` would
collect in a module of the required module set, and prints the same shape the
executed ``bench --site <site> run-tests`` runs produce.

It never reads the evidence and never reads the contract constants: it is an
independent second extraction that must agree with the executed counts.

Usage:
    python3 construction/tests/tools/stage2_measure_extract_counts.py [APP_ROOT]
"""

import ast
import sys
from pathlib import Path

MODULES = [
    "construction.searchable_dropdown.tests.test_search_api",
    "construction.searchable_dropdown.tests.test_integration",
    "construction.tests.test_bilingual_account_schema",
    "construction.tests.test_translation_catalog",
    "construction.tests.test_translation_stabilization_gates",
    "construction.tests.test_localization_gates",
    "construction.tests.test_bilingual_service",
    "construction.tests.test_bilingual_account_pilot",
    "construction.tests.test_stage4_account_language",
    "construction.tests.test_stage4_report_extension",
    "construction.tests.test_stage4_review_bundle",
]


def module_test_count(path: Path):
    """(total, per-class breakdown) for one module file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    total = 0
    detail = []
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        names = sorted(
            {
                f.name
                for f in cls.body
                if isinstance(f, ast.FunctionDef | ast.AsyncFunctionDef) and f.name.startswith("test")
            }
        )
        if names:
            total += len(names)
            detail.append(f"{cls.name}={len(names)}")
    return total, detail


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    total = 0
    for mod in MODULES:
        path = root / (mod.replace(".", "/") + ".py")
        if not path.is_file():
            print(f"{mod} :: MISSING {path}", file=sys.stderr)
            return 1
        count, detail = module_test_count(path)
        total += count
        print(f"{mod} :: {count}  [{', '.join(detail)}]")
    print(f"AGGREGATE_STATIC_TOTAL {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
