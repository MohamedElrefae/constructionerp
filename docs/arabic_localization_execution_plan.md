# Arabic Localization Execution Plan

Date: 2026-05-24
App: Construction ERP
Target platform: Frappe/ERPNext v16
Primary site for validation: `v16.localhost`

## Objective

Deliver end-to-end Arabic language support for the Construction app without modifying core ERPNext/Frappe DocType permission JSON, without breaking upgrades, and without relying on one-off manual fixes.

This plan does not mean full ERPNext Arabic localization. ERPNext and Frappe core may still show English where their own Arabic catalogs are incomplete. Construction owns:

- Construction DocTypes, workspace, sidebar, theme UI, scope UI, BOQ UI, custom JS/Python messages, fixtures, and print/PDF custom surfaces.
- A small reviewed DB seed for high-frequency shared action words needed by Construction workflows.

ERPNext-specific untranslated text must be handled as a separate ERPNext/Frappe localization project or through explicitly approved global DB overrides.

The finished state must satisfy these conditions:

- Arabic users see consistent Arabic labels, actions, messages, workspace items, and construction terminology.
- Construction-specific strings are maintained in the app translation catalog.
- Critical global UI gaps are handled through a repeatable, idempotent database translation seed.
- Arabic plural rules compile correctly.
- RTL layout works for custom Construction UI, workspace/sidebar UI, navbar, list/forms, dialogs, and print/PDF surfaces.
- Fresh install and migration reproduce the Arabic translation setup automatically.
- Verification commands and UI checks are documented and repeatable.

## Current State Summary

Confirmed issues:

- `construction/insert_translations.py` seeds only a small global Arabic dictionary.
- `insert_translations.py` clears the wrong cache key: `lang_full_dict`.
- Arabic DB translations exist on `v16.localhost`, but only 37 records were found.
- `construction/locale/ar.po` exists but has empty `msgstr` entries for Construction strings.
- `construction/locale/ar.po` has an incorrect Arabic plural formula.
- `Construction Settings` exists but is missing from `translated_doctypes`.
- `construction/config/workspace_sidebar_items.json` contains labels but is not covered by `babel_extractors.csv`.
- `fixtures/construction_theme.json` contains translatable theme data that is not extracted by the current extractor map.
- Arabic `Language` record is enabled, but date/time/number/week settings are null on the validation site.
- RTL CSS exists, but coverage is incomplete until visually verified across the custom UI.

Corrected audit note:

- RTL support is not absent. It exists in `public/css/modern_theme.css` and `public/css/scope_context.css`, but it must be tested and extended where gaps are found.

## Architecture Decision

Use Frappe's native three-layer translation model:

1. DB translations in `tabTranslation`
   - Use only for critical global UI terms that are missing or unreliable in upstream Frappe/ERPNext Arabic catalogs.
   - Seed through an idempotent app script.

2. PO/MO catalogs in `construction/locale/ar.po`
   - Use as the source of truth for Construction app strings.
   - Compile to `.mo` through the Frappe gettext pipeline.

3. Optional CSV fallback in `construction/translations/ar.csv`
   - Treat as compatibility fallback only.
   - Do not make it the primary translation source unless PO/MO compilation is unavailable.

Do not alter core ERPNext/Frappe DocType permission structures for localization.

## Phase 0 - Baseline Audit

Purpose: capture the exact starting point before edits.

Commands:

```bash
cd /home/mohamed/frappe-bench
git -C apps/construction status --short
bench --site v16.localhost execute frappe.db.count --args '["Translation", {"language":"ar"}]'
bench --site v16.localhost execute frappe.db.get_value --args '["Language", "ar", "*"]'
rg -n 'Plural-Forms|msgstr "[^"]+"' apps/construction/construction/locale/ar.po
rg -n 'translated_doctypes|after_install|after_migrate' apps/construction/construction/hooks.py
nl -ba apps/construction/babel_extractors.csv
```

Acceptance criteria:

- Current DB translation count is recorded.
- Current Arabic Language record is recorded.
- Current PO translation coverage is recorded.
- Worktree status is clean or unrelated existing changes are documented.

## Phase 1 - Fix Translation Seed Script

Files:

- `construction/insert_translations.py`
- `construction/hooks.py`

Tasks:

1. Replace the wrong cache clear call.

Current bad behavior:

```python
frappe.cache().delete_key("lang_full_dict")
```

Required behavior:

```python
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY

frappe.cache.hdel(USER_TRANSLATION_KEY, "ar")
frappe.cache.hdel(MERGED_TRANSLATION_KEY, "ar")
frappe.cache.delete_value(keys=["bootinfo"])
```

Alternative acceptable behavior:

```python
from frappe.translate import clear_cache

clear_cache()
```

Use targeted cache clearing unless simplicity is preferred.

2. Make the script hook-safe.

- Avoid unconditional `frappe.db.commit()` when called during install/migrate.
- Either remove the commit or add a parameter such as `commit=False`.
- Keep the script executable through `bench execute`.

Recommended shape:

```python
def execute(commit=False):
    ...
    if commit:
        frappe.db.commit()
```

3. Set `doc.flags.ignore_permissions = True` before insert/save.

4. Include `context` in duplicate lookup if context-aware entries are added.

5. Add the script to hooks:

```python
after_install = [
    "construction.install.create_system_themes",
    "construction.install.setup_branch_company_field",
    "construction.insert_translations.execute",
]

after_migrate = [
    ...
    "construction.insert_translations.execute",
]
```

6. Expand the seed dictionary only for stable, global UI strings.

Minimum additions:

```text
Amend, Close, Retry, Reload, Upload, Import, Export, Preview,
More, Less, Select All, Deselect All, Sort Ascending, Sort Descending,
Group By, Add Filter, Set, Unset, Enable, Disable, Previous, Next,
First, Last, Back, Continue, Mandatory, Optional, Read Only, Hidden,
Approve, Reject, Not permitted, Missing field, Required
```

Arabic quality rules:

- Prefer `تنزيل` for `Download`.
- Prefer `إرسال` for generic `Submit`; use context-specific records if workflow meaning is `اعتماد`.
- Prefer `عوامل التصفية` for noun `Filters`.
- Keep noun/verb ambiguity out of shared DB entries where possible.

Validation:

```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost execute construction.insert_translations.execute --kwargs '{"commit": true}'
bench --site v16.localhost clear-cache
bench --site v16.localhost execute frappe.db.count --args '["Translation", {"language":"ar"}]'
```

Acceptance criteria:

- Running the script twice does not create duplicates.
- Cache invalidation uses Frappe v16 keys.
- Fresh install/migrate can seed translations automatically.

## Phase 2 - Fix Hook Registration

File:

- `construction/hooks.py`

Tasks:

1. Add `Construction Settings` to `translated_doctypes`.

Required:

```python
translated_doctypes = {
    ...
    "Construction Settings": ["ar"],
}
```

2. Verify all app-owned DocTypes are represented:

```bash
find apps/construction/construction/construction/doctype -mindepth 2 -maxdepth 2 -name '*.json' | sort
```

Expected DocTypes:

- BOQ Header
- BOQ Item
- BOQ Structure
- Construction Settings
- Construction Theme
- CostItem
- Modern Theme Settings
- PlantResource
- User Desk Theme
- User Scope Context

Acceptance criteria:

- All 10 Construction DocTypes are covered by `translated_doctypes`.

## Phase 3 - Fix Extractor Coverage

File:

- `babel_extractors.csv`

Tasks:

1. Add extraction for config sidebar JSON.

Required line:

```csv
**/config/workspace_sidebar_items.json,frappe.gettext.extractors.workspace_sidebar.extract
```

2. Add extraction for workspace sidebar fixtures if they remain in use.

Required line:

```csv
**/fixtures/workspace_sidebar*.json,frappe.gettext.extractors.workspace_sidebar.extract
```

3. Add extraction for Construction Theme fixture data if those records remain a fixture source.

Recommended line:

```csv
**/fixtures/construction_theme.json,frappe.gettext.extractors.doctype.extract
```

Important: verify whether the generic DocType extractor gives useful results for a list of fixture records. If not, create a small app-specific extractor for fixture records that yields:

- `theme_name`
- `theme_type`
- `description`
- select-like values intended for display

4. Keep more-specific JSON patterns above broad Python/JS patterns.

Regenerate:

```bash
cd /home/mohamed/frappe-bench
bench generate-pot-file --app construction
bench update-po-files --app construction --locale ar
```

Acceptance criteria:

- `Home`, `BOQ Management`, `Theme Settings`, `Scope Management`, and `Construction Settings` appear in the generated POT/PO.
- Construction Settings labels and HTML help content appear in POT/PO.
- Theme display strings appear if they are still displayed to users.

## Phase 4 - Repair Arabic PO Header

File:

- `construction/locale/ar.po`

Tasks:

1. Replace incorrect plural formula.

Required header:

```po
"Plural-Forms: nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5);\n"
```

2. Replace placeholder version if app version is known.

Example:

```po
"Project-Id-Version: Construction ERP 1.0.0\n"
```

Validation:

```bash
cd /home/mohamed/frappe-bench
bench compile-translations --app construction --locale ar
```

Acceptance criteria:

- PO compiles without errors.
- Generated MO file exists for Arabic.

## Phase 5 - Translate Construction Catalog

File:

- `construction/locale/ar.po`

Tasks:

1. Translate all Construction-specific `msgstr` values.

Priority order:

- Workspace/sidebar/navigation strings
- DocType names
- BOQ, cost, plant, project, quantity, rate, unit, estimate, contract terminology
- Field labels
- Select options
- Validation and API messages
- Theme/settings labels
- HTML help content

2. Preserve placeholders and formatting.

Rules:

- Do not translate Python format keys: `{doctype}`, `{name}`, `{0}`, `%s`.
- Preserve HTML tags exactly when translating HTML-bearing msgids.
- Preserve newline structure in select options.
- Avoid translating technical identifiers that are shown as stable product names unless the UI requirement says otherwise.

3. Use a glossary.

Recommended glossary:

| English | Arabic |
|---|---|
| BOQ | جدول الكميات |
| BOQ Header | رأس جدول الكميات |
| BOQ Item | بند جدول الكميات |
| BOQ Structure | هيكل جدول الكميات |
| Cost Item | بند تكلفة |
| Plant Resource | مورد معدات |
| Estimated Unit Cost | تكلفة الوحدة المقدرة |
| Estimated Unit Price | سعر الوحدة المقدر |
| Contract Unit Price | سعر الوحدة التعاقدي |
| Total Estimated Value | إجمالي القيمة المقدرة |
| Total Contract Value | إجمالي قيمة العقد |
| Quantity | الكمية |
| Unit | الوحدة |
| Factor | المعامل |
| Overhead | مصاريف غير مباشرة |
| Provisional Sum | مبلغ احتياطي |
| Prime Cost | تكلفة أولية |
| Scope Context | سياق النطاق |
| Scope Management | إدارة النطاق |
| Theme Settings | إعدادات السمة |

Validation:

```bash
cd /home/mohamed/frappe-bench
bench compile-translations --app construction --locale ar
bench --site v16.localhost clear-cache
```

Acceptance criteria:

- No empty `msgstr` remains for user-facing Construction strings.
- PO compiles successfully.
- Arabic UI displays translated Construction labels after cache clear.

## Phase 6 - Workspace Sidebar Localization

Files:

- `construction/config/workspace_sidebar_items.json`
- `construction/install.py`
- `construction/locale/ar.po`

Tasks:

1. Ensure sidebar labels are extracted and translated.

2. Confirm runtime rendering calls Frappe translation on labels.

If Frappe workspace sidebar rendering does not translate stored labels, apply translation at boot/runtime rather than storing Arabic permanently in DB.

Preferred approach:

- Keep DB values in English canonical form.
- Translate display labels in the UI or server response using `_()`.

Avoid:

- Storing Arabic labels directly into `Workspace Sidebar Item.label`, because English users would then see Arabic.

Acceptance criteria:

- Arabic user sees Arabic sidebar labels.
- English user still sees English sidebar labels.
- Re-running `setup_workspace_sidebar()` does not overwrite language-specific user experience with one language only.

## Phase 7 - Arabic Language Record

Target:

- `Language` DocType record `ar`

Tasks:

Set missing locale fields on the site:

Recommended baseline:

```text
enabled = 1
date_format = yyyy-mm-dd
time_format = HH:mm
number_format = #,###.##
first_day_of_the_week = Saturday or Sunday, based on business requirement
```

Note:

- Do not assume Friday is correct for all Arabic deployments.
- For Egypt business use, Saturday or Sunday may be required. Confirm with business owner.

Validation:

```bash
bench --site v16.localhost execute frappe.db.get_value --args '["Language", "ar", ["enabled", "date_format", "time_format", "number_format", "first_day_of_the_week"]]'
```

Acceptance criteria:

- Arabic Language record has explicit date/time/number/week settings.

## Phase 8 - RTL UI Completion

Files:

- `construction/public/css/modern_theme.css`
- `construction/public/css/scope_context.css`
- `construction/templates/includes/navbar_brand.html`
- print/PDF template or API output used by `construction.api.theme_api.get_pdf_header`
- print/PDF template or API output used by `construction.api.theme_api.get_pdf_footer`

Tasks:

1. Audit custom selectors with physical direction properties.

Command:

```bash
rg -n 'margin-left|margin-right|padding-left|padding-right|border-left|border-right|left:|right:|text-align' apps/construction/construction/public/css
```

2. Prefer logical CSS properties for new work:

- `margin-inline-start`
- `margin-inline-end`
- `padding-inline-start`
- `padding-inline-end`
- `border-inline-start`
- `border-inline-end`
- `inset-inline-start`
- `inset-inline-end`

3. Add targeted `[dir="rtl"]` overrides where Frappe markup requires physical properties.

4. Update navbar brand markup/CSS if Arabic title alignment or icon order is wrong.

5. Validate custom UI:

- Workspace sidebar
- Navbar brand
- Scope context selectors
- Searchable dropdowns
- Link/select overrides
- BOQ tree view
- BOQ forms
- List views
- Dialogs
- Print/PDF headers and footers

Acceptance criteria:

- No overlapping text.
- Icons and labels are visually ordered correctly in RTL.
- Dropdowns open in the correct direction.
- Tree/list active indicators appear on the correct side.
- PDF/print output renders Arabic in correct direction.

## Phase 9 - Automated Checks

Create or update tests/scripts where practical.

Recommended files:

- `construction/tests/test_arabic_localization.py`
- `scripts/check_arabic_localization.py` if app scripts are used

Minimum checks:

- `ar.po` plural formula matches approved Arabic formula.
- `ar.po` has no empty `msgstr` for user-facing Construction strings.
- `translated_doctypes` covers all app DocTypes.
- `babel_extractors.csv` covers config workspace sidebar JSON.
- Translation seed script is idempotent.
- Arabic Language record is enabled on target site.

Example commands:

```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost run-tests --app construction
bench compile-translations --app construction --locale ar
bench --site v16.localhost execute construction.insert_translations.execute --kwargs '{"commit": true}'
bench --site v16.localhost execute construction.insert_translations.execute --kwargs '{"commit": true}'
```

Acceptance criteria:

- Tests pass.
- Compile succeeds.
- Running seed twice does not increase duplicate count.

## Phase 10 - Manual Arabic QA Script

Before production sign-off:

1. Create or use an Arabic test user.
2. Set user language to Arabic.
3. Clear cache and reload browser.
4. Visit:

- `/app/construction`
- BOQ Header list and form
- BOQ Structure tree
- BOQ Item form
- Construction Settings
- Construction Theme
- Modern Theme Settings
- User Scope Context

5. Validate:

- Page titles are Arabic.
- Sidebar is Arabic.
- Buttons are Arabic.
- Field labels are Arabic.
- Select options are Arabic.
- Validation messages are Arabic.
- No English remains except approved product names/codes.
- RTL layout is correct.
- English user still sees English UI.

Acceptance criteria:

- Arabic smoke test passes.
- English regression smoke test passes.

## Phase 11 - Translation Review And Correction Workflow

Purpose: allow Arabic reviewers to correct existing translations without editing PO syntax by hand.

Files:

- `construction/scripts/arabic_translation_review.py`
- `docs/arabic_po_review.csv`
- `docs/arabic_db_translation_review.csv`
- `docs/arabic_ui_i18n_guidelines.md`

Export current Construction PO translations:

```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost execute construction.scripts.arabic_translation_review.export_po_review
```

Edit:

```text
apps/construction/docs/arabic_po_review.csv
```

Import reviewed Construction PO translations:

```bash
bench --site v16.localhost execute construction.scripts.arabic_translation_review.import_po_review --kwargs "{'csv_path': 'apps/construction/docs/arabic_po_review.csv', 'dry_run': False}"
bench compile-po-to-mo --app construction --locale ar --force
bench --site v16.localhost clear-cache
bench --site v16.localhost execute construction.scripts.check_arabic_localization.execute
```

Export reviewed DB seed translations:

```bash
bench --site v16.localhost execute construction.scripts.arabic_translation_review.export_db_review
```

Edit:

```text
apps/construction/docs/arabic_db_translation_review.csv
```

Import reviewed DB seed translations:

```bash
bench --site v16.localhost execute construction.scripts.arabic_translation_review.import_db_review --kwargs "{'csv_path': 'apps/construction/docs/arabic_db_translation_review.csv', 'dry_run': False}"
bench --site v16.localhost clear-cache
```

Important:

- PO review is the normal path for Construction app corrections.
- DB review affects all apps and should be limited to shared UI action terms.
- If a word is ERPNext-specific and not used in Construction workflows, do not add it to the Construction seed without business approval.

Acceptance criteria:

- Reviewed CSV imports cleanly.
- PO compiles after import.
- Arabic localization check remains `ok: true`.
- Business-approved glossary changes are reflected in `ar.po`.

## Deployment Sequence

Recommended order:

1. Merge code changes.
2. Run:

```bash
cd /home/mohamed/frappe-bench
bench generate-pot-file --app construction
bench update-po-files --app construction --locale ar
bench compile-translations --app construction --locale ar
bench --site v16.localhost migrate
bench --site v16.localhost clear-cache
bench build
bench restart
```

3. Run automated checks.
4. Run manual Arabic QA.
5. Run English regression smoke test.

## Rollback Plan

If Arabic deployment causes UI issues:

1. Disable user language override for affected users by setting language back to English.
2. Clear cache:

```bash
bench --site v16.localhost clear-cache
```

3. If DB translations are faulty, correct or delete only the affected `Translation` records.
4. If PO/MO translation is faulty, revert `ar.po`, recompile translations, clear cache.
5. Do not modify core Frappe/ERPNext files as a rollback shortcut.

## Definition Of Done

Arabic localization is complete only when:

- DB seed script is idempotent, hook-safe, and cache-correct.
- Arabic seed runs on install and migrate.
- All Construction DocTypes are registered for Arabic translation.
- Extractors cover DocTypes, workspace/sidebar config, workspace JSON, Python, JS, HTML/Vue, custom fields, and active fixtures.
- `ar.po` has correct plural formula.
- `ar.po` contains Arabic translations for all user-facing Construction strings.
- `bench compile-translations --app construction --locale ar` succeeds.
- Arabic Language record has explicit locale settings.
- Arabic user smoke test passes.
- English user smoke test passes.
- RTL custom UI smoke test passes.
- No permission JSON was modified for localization.

## AI Agent Execution Prompt

Use this prompt for a follow-up coding agent:

```text
You are working in /home/mohamed/frappe-bench on the Construction Frappe app.

Goal: implement end-to-end Arabic localization support according to apps/construction/docs/arabic_localization_execution_plan.md.

Constraints:
- Do not modify core Frappe/ERPNext permission JSON.
- Do not revert unrelated user changes.
- Keep DB translations idempotent and hook-safe.
- Use PO/MO as the source of truth for Construction strings.
- Use DB Translation records only for critical global UI terms.
- Preserve English canonical data in Workspace Sidebar records; translate display output, not stored DB labels, if runtime translation is needed.
- Preserve placeholders, HTML tags, and formatting in PO translations.
- Validate with bench commands on site v16.localhost.

Execution order:
1. Read the plan file completely.
2. Inspect current files before editing:
   - apps/construction/construction/insert_translations.py
   - apps/construction/construction/hooks.py
   - apps/construction/babel_extractors.csv
   - apps/construction/construction/locale/ar.po
   - apps/construction/construction/install.py
   - apps/construction/construction/public/css/modern_theme.css
   - apps/construction/construction/public/css/scope_context.css
3. Implement Phase 1 through Phase 4 first.
4. Regenerate/update PO catalog.
5. Translate high-priority Construction strings first, then complete the catalog.
6. Compile translations and clear cache.
7. Add automated checks if time permits.
8. Run validation commands and report exact results.

Required final report:
- Files changed.
- Commands run.
- Translation count before/after.
- PO compile result.
- Remaining untranslated strings count.
- RTL QA status.
- Any blocker requiring business translation approval.
```
