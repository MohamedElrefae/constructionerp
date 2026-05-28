from pathlib import Path

import frappe
from babel.messages.pofile import read_po

ARABIC_PLURAL_FORMS = (
    "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : "
    "n%100>=3 && n%100<=10 ? 3 : n%100>=0 && n%100<=2 ? 4 : 5);"
)


def execute():
    app_root = Path(frappe.get_app_path("construction")).parent
    package_root = Path(frappe.get_app_path("construction"))
    issues = []

    _check_po(package_root / "locale" / "ar.po", issues)
    _check_extractors(app_root / "babel_extractors.csv", issues)
    _check_translated_doctypes(issues)
    _check_required_db_translations(issues)
    _check_language_record(issues)

    result = {
        "ok": not issues,
        "issues": issues,
        "arabic_translation_count": frappe.db.count("Translation", {"language": "ar"}),
    }
    print(result)
    return result


def _check_po(po_path, issues):
    with po_path.open("rb") as po_file:
        catalog = read_po(po_file, locale="ar")

    if catalog.plural_expr != ARABIC_PLURAL_FORMS.split("plural=", 1)[1].rstrip(";"):
        issues.append("ar.po Arabic plural formula is incorrect")

    empty = [message.id for message in catalog if message.id and not message.string]
    if empty:
        issues.append(f"ar.po has {len(empty)} untranslated non-header messages")


def _check_extractors(extractor_path, issues):
    content = extractor_path.read_text()
    required_patterns = [
        "**/config/workspace_sidebar_items.json",
        "**/fixtures/workspace_sidebar*.json",
        "**/fixtures/construction_theme.json",
    ]
    for pattern in required_patterns:
        if pattern not in content:
            issues.append(f"Missing extractor pattern: {pattern}")


def _check_translated_doctypes(issues):
    hooks = frappe.get_hooks("translated_doctypes") or {}
    required = {
        "BOQ Header",
        "BOQ Item",
        "BOQ Item Stage",
        "BOQ Structure",
        "Construction Settings",
        "Construction Theme",
        "CostItem",
        "Modern Theme Settings",
        "PlantResource",
        "User Desk Theme",
        "User Scope Context",
    }
    missing = sorted(doctype for doctype in required if "ar" not in hooks.get(doctype, []))
    if missing:
        issues.append(f"Missing translated_doctypes Arabic coverage: {', '.join(missing)}")


def _check_required_db_translations(issues):
    required = {
        "BOQ Item Stage": "مراحل تنفيذ البنود",
    }
    for source_text, expected in required.items():
        actual = frappe.db.get_value(
            "Translation",
            {"language": "ar", "source_text": source_text, "context": ""},
            "translated_text",
        )
        if actual != expected:
            issues.append(f"Missing reviewed Arabic DB translation: {source_text}")


def _check_language_record(issues):
    values = frappe.db.get_value(
        "Language",
        "ar",
        ["enabled", "date_format", "time_format", "number_format", "first_day_of_the_week"],
        as_dict=True,
    )
    if not values or not values.enabled:
        issues.append("Arabic Language record is missing or disabled")
        return

    for field in ["date_format", "time_format", "number_format", "first_day_of_the_week"]:
        if not values.get(field):
            issues.append(f"Arabic Language record missing {field}")
