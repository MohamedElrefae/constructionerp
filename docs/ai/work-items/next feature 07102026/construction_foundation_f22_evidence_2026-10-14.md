# F22 — Arabic and everyday UI usability (evidence)

Date: 2026-10-14 · Site: `v16rehearsal.localhost` (served via a temporarily flipped `default_site`, disclosed below) · Personas: `f04-pm`, `f20-buyer` (both switched to `language = ar`)

---

## 1. What F22 verified

Actual navigation and pages in Arabic/RTL with **ordinary personas**, not visibility alone:

| Area | Check | Result |
|---|---|---|
| locale | `html lang=ar`, `dir=rtl`, body RTL | pass |
| navigation | sidebar on the construction module route, every label Arabic | pass (17 entries) |
| work area | the persona's own workspace link present, page opens, no foreign work area | pass |
| workspace page | all card labels Arabic | pass (5 cards) |
| table | list view title + headers Arabic, rows RTL, mixed-direction cells render | pass |
| translated errors | mandatory-field refusal fully Arabic; permission denial Arabic | pass |
| dialog | K-01 two-step import dialog: title, field labels, options, buttons all Arabic | pass |
| export | app export menu Arabic (3 items), print-settings dialog Arabic (4 buttons) | pass |

Two personas, one clean browser context each:
- **f04-pm (Project Manager, Arabic): 19/19 checks**
- **f20-buyer (Purchase User, Arabic): 8/8 checks** — own work area only, no foreign work area leaked

Screenshots: `/tmp/opencode/f22-shots/` (workspace, list, dialog, print-settings, buyer workspace).

## 2. Defects found and fixed

**F22-D001 — the mandatory-field refusal was half English.** The framework's own
`ar.po` ships `"Please fill the following mandatory fields before saving:"` with an
**empty** `msgstr`, so an Arabic session showed
`Please fill the following mandatory fields before saving:مشروع مطلوب.`
Fixed by supplying the translation; the app merges after frappe, so an app entry fills the gap.

**F22-D002 — sidebar chrome untranslated.** `Desk`, `Column Widths`,
`Select BOQ Header first` appeared in English in the Arabic session. Translated.

**F22-D003 — the K-01 import dialog could never be Arabic.** `title`, `Excel File`,
`Import Mode`, the mode options, the field description and both `set_primary_action`
labels were hardcoded strings, not passed through `__()`. Wrapped in `__()` (10 sites in
`boq_header.js`) and translated. The dialog now reads
`استيراد جدول الكميات من Excel` / `ملف Excel` / `طريقة الاستيراد` / `منظَّم، شبه منظَّم، مسطَّح` /
`إرفاق` / `تحقَّق`.

**F22-D004 — export and print settings were English.** The export/print column labels
(`WBS Code`, `Line Total`, `BOQ ID`, …) were hardcoded English in `boq_header.js`, so an
exported or printed Arabic BOQ carried English headers. All 21 wrapped in `__()` and
translated; the export menu and print-settings dialog are now Arabic
(`ملف Excel (XLSX)`, `حفظ الإعدادات`, `استعادة الإعدادات الافتراضية`, `إلغاء`, `تصدير`).

**F22-D005 — sidebar and workspace labels had no translation entries.** `Estimating and
commercial`, `Variation Order`, `User Scope Context`, `Construction Report Viewer`,
`Cost Database Workbench`, the other four work-area labels and the five workspace card
labels rendered in English. Translated; the sidebar and workspace cards are now Arabic
for both personas.

**F22-D006 — an ordinary persona got a permission-error dialog on every BOQ Header form.**
`construction.api.scope_context_api.get_project_display_name` authorises a caller without
Project read by their active scope project, then read the name with `frappe.get_list`,
which **raises** "Insufficient Permission" for a DocType the caller cannot read at all. The
documented fallback was therefore unreachable and `syncProjectName` put a 403 dialog on the
form. Fixed: after the active-scope authorisation, the single already-authorised name is
read with a parameterised `frappe.db.sql` lookup. The framework's blanket doctype gate no
longer runs before the app's own check, and missing/unauthorised names still get the same
generic denial (no existence oracle). Verified: the PM now resolves its own project name;
sibling call sites already caught `PermissionError` and needed no change.

## 3. Open finding (not fixed — needs an owner decision)

**F22-D007 — routing investigation, concluded 2026-10-14: `/app/construction-home` is NOT a
supported route.**

The desk decides what an `/app/<segment>` URL names in one place,
`frappe/public/js/frappe/router.js` → `segment_kind(segment)`, in this order:

1. `frappe.workspaces[segment]` → **workspace** (populated in `desk.js`
   `setup_workspaces()` as `slug(page.name)` for every page in
   `get_workspaces()["pages"]` — i.e. only actual **Workspace** documents the user may see);
2. `private` → private shell;
3. `this.routes[segment]` → doctype;
4. `frappe.boot.page_info[segment]` or `standard_pages` → **page**;
5. a registered view factory → view;
6. otherwise `null` — "a word the desk does not know", left for `render_page`, which calls
   `frappe.views.pageview.with_page(name)` → `frappe.desk.desk_page.getpage(name)` →
   `frappe.get_doc("Page", name)`.

`Construction Home` is a **Sidebar** document (the module's shell), not a Workspace
document, so its slug is in none of those registries. The route therefore lands on the
Page loader, and stock ERPNext grants **Page** read only to System Manager and
Administrator — hence the 403 for every ordinary persona.

Measured (one clean browser context per case, rehearsal site verified first):

| Route | Persona | Result | Path taken |
|---|---|---|---|
| `/app/construction` | f04-pm | loaded | module → its shell |
| `/app/estimating-and-commercial` | f04-pm | loaded | workspace slug |
| `/app/site-work` | f04-engineer | loaded | workspace slug |
| `/app/cost-database` | f18-maintainer | loaded | workspace slug |
| `/app/procurement-and-stores` | f20-buyer | loaded | workspace slug |
| `/app/construction-home` | f04-pm | **denied** | `desk_page.getpage` → 403 |

**Canonical entry: `/app/construction`.** It is the module route, it is what the dock and
sidebar produce, and it renders the same shell. Each role workspace also has its own
supported slug: `/app/site-work`, `/app/estimating-and-commercial`,
`/app/procurement-and-stores`, `/app/finance`, `/app/cost-database`.

**No promises of the broken URL remain.** A repo-wide search found no code, fixture, test
or user-facing document that links to `/app/construction-home`; the only user-facing
reference to a construction route is `docs/arabic_localization_execution_plan.md`, which
already uses `/app/construction`.

**Remaining owner decision:** whether to make the shell slug work at all (rename the Sidebar
back to the module name, or grant Page read to the audience), or to accept it as
not deep-linkable. Nothing a user clicks is affected either way, so this is a tidy-up
choice, not a defect blocking acceptance.

## 4. Translation coverage and how it is kept

Two app-code fixes, then translations applied through the canonical service
(`construction.translation_service.upsert_runtime_translation`, `origin="Site Override"`,
auditable via `ct_origin` / `ct_review_status`) — never a direct table edit.

A scan of every `__()` string across the ten files an ordinary persona loads found
**187 distinct strings, 126 with no Arabic entry**. All 126 are now translated, plus the
sidebar/workspace labels and the framework gaps. A falsifiable check confirms it:

```
distinct translatable strings found: 187
MISSING ARABIC (0)
```

Regression suite `construction/tests/test_f22_arabic_coverage.py` (4 tests, all pass):
1. every `__()` string on those surfaces has a non-empty Arabic entry;
2. sidebar + workspace item labels are translated;
3. framework strings our surfaces rely on are translated (they ship empty);
4. the K-01 dialog strings are wrapped in `__()`, not hardcoded.

Run: `bench --site <site> run-tests --module construction.tests.test_f22_arabic_coverage`

One case could not be stored: `" (truncated at the export limit)"` carries a leading space
and the service normalises keys by stripping it, so it can never be matched. Rather than
special-case the service, the viewer now keeps the space outside the translatable string
(`" (" + __("truncated at the export limit") + ")"`).

## 5. Environment actions (disclosed)

- `default_site` in `sites/common_site_config.json` was temporarily set to
  `v16rehearsal.localhost` so `bench serve` could serve the UAT site for browser work; the
  previous value (`v16.localhost`) is saved in `/tmp/opencode/csc-before-f22.json` and is
  restored at the end of the session (see §6).
- The dev server (`bench serve --port 8000`) was restarted twice during this work; both
  Redis instances (13000 cache, 11000 queue) had died and were restarted with
  `config/redis_cache.conf` / `config/redis_queue.conf`.
- Fixture changes: `f04-pm` and `f20-buyer` switched to `language = ar` to represent the
  Arabic-speaking audience. Other personas remain `en` for the remaining work.

## 6. Status

F22 **Engineering verified** for Arabic/RTL on the surfaces the owner listed: navigation,
pages, translated errors, mixed-direction identifiers, tables, dialogs and exports — with
two ordinary personas. Owner acceptance remains in the consolidated final block (F43/F44),
including the print/export output as a document and the Arabic reviewer's terminology pass.
F22-D007 (shell deep link) is open for the owner's decision.
