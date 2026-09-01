"""AST lint: detect Translation mutations outside canonical service."""

import ast
import sys
from pathlib import Path

ALLOWLIST = {
    "construction/translation_service.py",
    "construction/translation_loader.py",
    "construction/patches/v8_6/add_translation_identity_and_dedup.py",
    "construction/setup/translation_catalog_fields.py",
    "construction/patches/v6_2/seed_arabic_translations.py",
    "construction/patches/v6_3/seed_reviewed_arabic_translation_files.py",
    "construction/patches/v6_4/reconcile_sidebar_and_arabic_translations.py",
    "construction/patches/v6_5/harden_boq_item_stage_arabic_translation.py",
    "construction/patches/v8_3/fix_arabic_domain_terminology.py",
    "construction/patches/v8_4/fix_tree_view_arabic_translations.py",
    "construction/patches/v8_5/seed_translation_catalog.py",
    "construction/api/translation_tools.py",
    "construction/insert_translations.py",
    "construction/scripts/arabic_translation_review.py",
    "construction/scripts/global_arabic_translation_review.py",
    "scripts/lint_translation_writes.py",
}

FORBIDDEN_PATTERNS = [
    "frappe.db.set_value.*Translation",
    "frappe.get_doc.*Translation",
    "frappe.new_doc.*Translation",
    "frappe.db.delete.*Translation",
    "bulk_insert.*Translation",
    "frappe.db.sql.*tabTranslation",
]


def is_allowed(path: str) -> bool:
    p = path.replace("\\", "/")
    for allowed in ALLOWLIST:
        if p.endswith(allowed) or p == allowed:
            return True
    if "/tests/" in p or p.endswith("_test.py") or "/test_" in p:
        return True
    return False


def check_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    if "Translation" not in text:
        return []
    if is_allowed(str(path)):
        return []
    errors = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            src = ast.unparse(node) if hasattr(ast, "unparse") else ""
            if "Translation" in src:
                if any(kw in src for kw in ["set_value", "get_doc", "new_doc", "delete", "bulk_insert", "tabTranslation"]):
                    errors.append(f"{path}:{node.lineno}: forbidden Translation mutation outside canonical service: {src[:120]}")
    if not errors and "tabTranslation" in text and "frappe.db.sql" in text:
        for i, line in enumerate(text.splitlines(), 1):
            if "tabTranslation" in line and "frappe.db.sql" in line:
                errors.append(f"{path}:{i}: direct SQL on tabTranslation outside canonical service")
                break
    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    errors = []
    for py in root.rglob("*.py"):
        if "translation_service" in str(py) or "translation_loader" in str(py):
            continue
        file_errors = check_file(py)
        errors.extend(file_errors)
    if errors:
        print("Translation write lint FAILED:")
        for e in errors:
            print(f"  {e}")
        print(f"\nTotal: {len(errors)} violation(s). All Translation writes must go through construction/translation_service.py")
        sys.exit(1)
    print("Translation write lint PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
