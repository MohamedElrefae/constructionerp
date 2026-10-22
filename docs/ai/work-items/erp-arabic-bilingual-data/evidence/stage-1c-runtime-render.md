# Stage 1C — Runtime + Fresh-Session Render Evidence (2026-09-04)

Session: fresh Chromium login as `stage1c.prover@test.local` (language `ar`, created on
test site for this evidence; System Manager), `htmlLang=ar`, `frappe.boot.lang=ar`.
Target: `v16.localhost` test site (port 8000). No production data. No English fallback session was harmed.

## AI-R blocker 1 — raw `Workspaces` path: RESOLVED WITHOUT VENDOR EDIT OR EXTENSION

- `sidebar_header.js:20` is indeed a raw `label: "Workspaces"` literal.
- BUT the visible dropdown is rendered by `frappe.ui.menu` (`menu.js:109`):
  `<span class="menu-item-title">${__(item.label)}</span>` — every label, raw or wrapped,
  passes through the governed runtime dictionary at render time.
- The `add_app_item`/`dropdown_menu` path (`sidebar_header.js:345-362`) is dead in this
  Frappe version: template `sidebar_header.html` contains no `.sidebar-header-menu`
  element, so items append to an empty set. Verified live: no `.sidebar-header-menu`
  node exists in the rendered DOM.
- A first-attempt Construction-side DOM extension (`stage1c_sidebar_labels.js`) was
  created, then REMOVED unused: it targeted a non-existent node and the dictionary
  already covers the real render path. `hooks.py` restored — no diff remains.
- Live proof: on `/app/invoicing` (sibling-workspaces condition true) the header menu
  renders **مساحات العمل**. Screenshot: `render-1c/workspaces-entry-1366.png` (`48e5de31…`).

## AI-R blocker 2 — runtime payload: PROMOTED ON TEST SITE ONLY

- `import_released_overrides(dry_run=True)`: 34 rows, 6 creates, 0 drift.
- `dry_run=False` on `v16.localhost`: 6 created, 28 skipped, 0 drift.
- `get_effective_translation("ar", …)` returns all six approved values:
  Desktop→سطح المكتب, Workspaces→مساحات العمل, Edit Sidebar→تحرير الشريط الجانبي,
  Toggle Theme→تبديل المظهر, Toggle Full Width→تبديل العرض الكامل,
  Typography Settings→إعدادات الخطوط.
- Catalog rows stamped Released with matching values by the governed service; vendor
  `.po` files untouched. Payload: 6 new rows in `approved_ar_overrides.csv` (v1.0)
  carrying AI-A1/AI-A2/AI-A3 session provenance.

## AI-R blocker 3 — fresh-session render + narrow-width test: CAPTURED

Fresh Arabic session, header dropdown opened, all labels read from live DOM:

| Label | 1366px | 390px |
|---|---|---|
| سطح المكتب | ✅ | ✅ |
| مساحات العمل | ✅ (on `/app/invoicing`) | n/a (condition route-dependent) |
| تحرير الشريط الجانبي | ✅ | ✅, no clipping |
| تبديل المظهر | ✅ (Display submenu) | ✅ |
| تبديل العرض الكامل | ✅ (Display submenu) | ✅ |
| إعدادات الخطوط | ✅ (Display submenu) | ✅ |

Narrow-width (390px) `Edit Sidebar` measurement: `scrollWidth == clientWidth` (127px),
no horizontal viewport overflow, `white-space:nowrap; overflow:hidden; text-overflow:ellipsis`
with no truncation active. AI-A3 non-blocking exception CLOSED by measurement.
Screenshots: `header-menu-1366.png` (`6d8a0671…`), `display-submenu-1366.png`
(`87b2359d…`), `header-menu-390.png` (`cf69e3d3…`).

## Out of scope (observed, not changed)

`Notification Settings`, `Add Sidebar Item`, raw `Display`→عرض (resolves via dictionary)
are outside the six-row Stage 1C scope and were not modified.

## Resolved test-site mutations (all on shared test DB, documented)

- `stage1c.prover@test.local` (ar, System Manager) created for browser evidence.
- Six runtime `Translation` rows created + six catalog rows stamped Released.
- `account_name_ar` Custom Field + column from Stage 1B (unchanged in this pass).
