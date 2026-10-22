# Arabic Sidebar Translation Deployment Report

## Problem

Arabic translations were inserted on the site, but some Desk/sidebar labels still appeared in English on Frappe Cloud:

- Sidebar/module titles such as `Projects` and `Home`.
- Construction sidebar entries, especially the Scope Context area.
- Workspace section headers such as `Reports & Masters`.

## Root Cause

1. Frappe builds `boot.workspace_sidebar_item` during boot. It translates child sidebar item labels, but the top-level sidebar/module title is sent as the raw English sidebar name.
2. The deployed site can keep an older `Workspace Sidebar` database record until a migration hook or patch reconciles it. That is why the local Construction sidebar can contain Scope Context items while Cloud still misses them.
3. Some reviewed ERPNext workspace header strings existed in `docs/erpnext_ar_missing_review_filled.csv` with blank Arabic values, so the seeder correctly skipped them. Exact HTML labels such as `<span class="h4"><b>Reports &amp; Masters</b></span>` therefore had no Arabic row.

## Fix Added

- `construction.boot.extend_bootinfo` now translates sidebar titles and any sidebar labels still present in bootinfo.
- Arabic translation overrides now include the exact sidebar/workspace labels needed for:
  - `Home`
  - `Projects`
  - `Reports & Masters`
  - `Reports &amp; Masters`
  - `Your Shortcuts`
  - `BOQ Management`
  - `Scope Management`
  - `User Scope Context`
  - `Construction Settings`
- Patch `construction.patches.v6_4.reconcile_sidebar_and_arabic_translations` was added. On Frappe Cloud migration it:
  - reseeds all reviewed Arabic translations,
  - rebuilds the Construction workspace sidebar from `construction/config/workspace_sidebar_items.json`,
  - clears cache.

## Cloud Deployment Check

After deploy and migrate, run this in the browser console:

```js
await frappe.call({
  method: "construction.insert_translations.get_arabic_translation_seed_status"
})
```

Expected:

- `patch_v6_4: true`
- `samples["Reports & Masters"].translated_text` is Arabic.
- `samples["Projects"].translated_text` is Arabic.
- `construction_sidebar_items` includes `Scope Management` and `User Scope Context`.

If `patch_v6_4` is false, the app code reached Cloud but migration did not run for the site.
