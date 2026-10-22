# Arabic UI i18n Guidelines

Date: 2026-05-24
Scope: Construction app only

## Scope Boundary

The Construction app must be fully translated to Arabic.

ERPNext and Frappe core may still show English where their upstream Arabic catalogs are incomplete. This app should not claim to fully translate ERPNext. The Construction app may seed a small set of global DB translations for high-frequency shared UI actions, but that is a compatibility layer, not full ERPNext localization.

## Translation Sources

Use this order:

1. `construction/locale/ar.po`
   - Source of truth for Construction app UI, DocTypes, workspace, JS, Python messages, settings, and theme text.

2. `construction.insert_translations`
   - Only for critical shared Frappe/ERPNext action strings that affect Construction workflows.
   - Keep the list small, reviewed, and idempotent.

3. Runtime user data
   - Keep stored values language-neutral where possible.
   - Do not store Arabic-only labels in records that English users also see.

## Rules For New UI Components

### JavaScript

Wrap every visible string with `__()`.

Good:

```javascript
frappe.msgprint(__("Please select a BOQ Header first."));
button.text(__("Export to PDF"));
```

Bad:

```javascript
frappe.msgprint("Please select a BOQ Header first.");
button.text("Export to PDF");
```

For placeholders, labels, empty states, tooltips, dialog titles, button labels, menu labels, and alerts, use `__()`.

```javascript
{
    label: __("Select BOQ Header"),
    fieldname: "boq_header",
    fieldtype: "Link",
    options: "BOQ Header",
}
```

For context-sensitive words, add context when ambiguity matters.

```javascript
__("Submit", null, "Workflow action")
```

### Python

Import and use Frappe `_()`.

```python
from frappe import _

frappe.throw(_("Company is mandatory for Scope Context."))
```

Never build translatable strings by concatenating translated and untranslated fragments.

Good:

```python
frappe.throw(_("Not authorized: Company '{0}'").format(company))
```

Bad:

```python
frappe.throw(_("Not authorized: ") + company)
```

### DocType JSON

Use standard `label`, `description`, and `options` fields. The DocType extractor reads these fields.

For Select fields:

```json
"options": "Draft\nPricing\nFrozen\nLocked"
```

Do not use hardcoded HTML text in DocType HTML fields unless necessary. If HTML is needed, preserve simple markup and keep the text reviewable in `ar.po`.

### Workspace And Sidebar

Keep canonical stored labels in English. Frappe translates workspace/sidebar item labels during boot with `_()`.

Do not store Arabic labels directly into:

- `Workspace Sidebar.title`
- `Workspace Sidebar Item.label`
- Workspace JSON labels

### Fixtures

If fixture values are displayed to users, make sure they are covered by an extractor or translated at display time.

Covered fixture examples:

- `fixtures/construction_theme.json`
- `fixtures/workspace_sidebar*.json`

### CSS And RTL

Prefer logical CSS properties for new UI:

- `margin-inline-start`
- `margin-inline-end`
- `padding-inline-start`
- `padding-inline-end`
- `border-inline-start`
- `border-inline-end`
- `inset-inline-start`
- `inset-inline-end`

Use `[dir="rtl"]` overrides only when Frappe markup or third-party controls require physical direction fixes.

Avoid negative letter spacing for Arabic text.

## Translation Review Workflow

1. Export current Arabic PO for review:

```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost execute construction.scripts.arabic_translation_review.export_po_review
```

2. Edit the generated CSV:

```text
apps/construction/docs/arabic_po_review.csv
```

3. Import reviewed changes:

```bash
bench --site v16.localhost execute construction.scripts.arabic_translation_review.import_po_review --kwargs "{'csv_path': 'apps/construction/docs/arabic_po_review.csv', 'dry_run': False}"
```

4. Compile and validate:

```bash
bench compile-po-to-mo --app construction --locale ar --force
bench --site v16.localhost clear-cache
bench --site v16.localhost execute construction.scripts.check_arabic_localization.execute
```

## Review Standards

- Preserve placeholders: `{0}`, `{1}`, `{name}`, `%s`.
- Preserve HTML tags exactly.
- Preserve DocType names when they are technical identifiers unless the UI explicitly requires Arabic labels.
- Prefer clear ERP terminology over literal translation.
- Use one glossary consistently across BOQ, cost, plant, and scope modules.

## ERPNext English Text

If English remains in ERPNext standard modules, handle it separately from Construction app localization:

- Confirm whether the string belongs to Frappe, ERPNext, or Construction.
- If Construction: add/fix it in `construction/locale/ar.po`.
- If shared action text used heavily in Construction: consider `insert_translations.py`.
- If ERPNext-specific: do not modify it in the Construction app unless the business explicitly approves global DB overrides.

