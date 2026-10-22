# Handoff Report: Disable Like Column in List View

**Date:** 2026-06-24
**Status:** Fix applied, pending user verification
**Agent:** opencode/mimo-v2.5-free → Codex

---

## 1. Problem Statement

The like/heart column in Frappe list views (showing a heart icon, like count, and comment count in the `level-right` section) was:

1. **Overlaying dropdown menus** due to `position: sticky; right: 0` on `.level-right`
2. **Not following theme or column configuration** — it's hardcoded, not a configurable column
3. **No way to disable it** per-doctype via List View Settings
4. **Even with like disabled, the space remained** because `.level-right` kept fixed width (130-200px) and the modified date still showed

**User request:** Add a `disable_like` toggle to List View Settings, similar to the existing `disable_comment_count`.

---

## 2. Root Cause Analysis

### Why the like column overlays other elements

In `apps/frappe/frappe/public/js/frappe/list/list_view.js`:
- **Line 801-814** (`get_header_html`): The "Liked by me" toggle button is rendered in `.level-right`
- **Line 1170-1185** (`get_meta_html`): The like button per row is rendered in `.list-row-activity` inside `.level-right`

In `apps/frappe/frappe/public/scss/desk/list.scss`:
- **Line 155-161**: `.level-right` has `position: sticky; right: 0` with a solid `background-color`, making it a fixed sidebar that overlays content
- **Line 129-134**: `.result.no-assign-to .list-row .level-right` has `flex: 0 0 130px; width: 130px` — a fixed width that persists even when like/comment are disabled

### Why the space remains after disabling like

Even with `disable_like=1`:
- The `.level-right` still renders with `flex: 0 0 130px` (fixed 130px width)
- The modified date (`<span class="modified">`) is always rendered in `get_meta_html()` — it has no disable toggle
- The sticky positioning + fixed width creates a permanent right sidebar

### Why the setting didn't work initially

**Root cause: Duplicate field definitions in `list_view_settings.json`.**

The original edits to the DocType JSON introduced duplicate entries:
- `fieldname: "fields"` appeared 3 times
- `fieldname: "disable_comment_count"` appeared 2 times

This caused `bench migrate` to create duplicate `tabDocField` rows, which corrupted the meta loading. When `frappe.get_meta("List View Settings")` loaded stale/corrupted meta, the `disable_like` field was missing from `get_valid_fields()`, so `as_dict()` excluded it from the API response.

### Additional caching layer

`frappe.get_cached_doc("List View Settings", doctype)` in `apps/frappe/frappe/desk/listview.py:15` caches the entire Document object (including its `_meta` cached_property) in Redis for 3600 seconds. Even after fixing the JSON, stale cached documents without `disable_like` would keep being served.

---

## 3. Changes Made (All 4 Files)

### File 1: `apps/frappe/frappe/desk/doctype/list_view_settings/list_view_settings.json`

**What:** Added `disable_like` Check field to the DocType definition. Cleaned up ALL duplicate field entries.

**field_order** (line 8-22): Added `"disable_like"` between `disable_comment_count` and `disable_scrolling`.

**fields** array: Contains exactly 13 unique entries (was previously corrupted with duplicates).

### File 2: `apps/frappe/frappe/desk/doctype/list_view_settings/list_view_settings.py`

**What:** Added type hint for the new field.

**Line 22:** Added `disable_like: DF.Check` in the `TYPE_CHECKING` block.

### File 3: `apps/frappe/frappe/public/js/frappe/list/list_view.js`

**Change A — Header rendering** (line 801-814):
```js
const right_html = `
    <span class="list-count" style=""></span>
    ${
        !this.list_view_settings?.disable_like
            ? `<span class="level-item list-liked-by-me hidden-xs">
                    <span title="${__("Liked by me")}">
                        <svg class="icon icon-sm like-icon">
                            <use href="#icon-heart"></use>
                        </svg>
                    </span>
                </span>`
            : ""
    }
`;
```

**Change B — Row rendering** (line 1170-1185):
```js
let like_html = "";
if (!this.list_view_settings?.disable_like) {
    like_html = `<span class="list-row-like hidden-xs" style="margin-bottom: 1px;">
        ${this.get_like_html(doc)}
    </span>`;
}
```

**Change C — `update_listview_classes`** (line ~1104): Adds `no-activity` class when both like AND comment count are disabled:
```js
if (
    this.list_view_settings?.disable_like &&
    this.list_view_settings?.disable_comment_count
) {
    this.$result.addClass("no-activity");
}
```

### File 4: `apps/frappe/frappe/public/scss/desk/list.scss`

**Change A — `z-index` on `.level-right`** (line ~155): Added `z-index: 1` to prevent stacking issues, and `z-index: 3` for header.

**Change B — `no-activity` class** (line ~168): When both like and comment are disabled, collapses `.level-right` to auto width:
```scss
&.no-activity .level-right {
    flex: 0 0 auto;
    width: auto;
    min-width: 0;
    padding: 9px 6px;
    border-left: none;
}
```

**Change C — Dropdown z-index fix** (line ~177): Ensures dropdown menus appear above the sticky `.level-right`:
```scss
.list-row-container .level-right + .dropdown-menu,
.list-row-container .level-right ~ .dropdown-menu {
    z-index: 1050;
}

.filterable-dropdown {
    z-index: 1050 !important;
}
```

---

## 4. Data Flow (How It Works)

```
1. List View Settings DocType (JSON defines fields)
        ↓
2. bench migrate → creates tabDocField rows (including disable_like)
        ↓
3. frappe.get_meta("List View Settings") → loads field definitions
        ↓
4. API: frappe.desk.listview.get_list_settings(doctype)
   → frappe.get_cached_doc("List View Settings", doctype)
   → Document.as_dict() → iterates meta.get_valid_fields() → includes disable_like
        ↓
5. JS: base_list.js get_list_view_settings() → sets this.list_view_settings
        ↓
6. JS: list_view.js setup_view() → calls setup_columns() then render_header()
        ↓
7. Header checks: !this.list_view_settings?.disable_like → conditionally renders heart
   Rows check: !this.list_view_settings?.disable_like → conditionally renders like button
   update_listview_classes: if both disabled → adds "no-activity" class to $result
        ↓
8. CSS: .no-activity .level-right → flex: 0 0 auto (collapses width)
```

---

## 5. How to Verify

### Step 1: Check DB state
```bash
bench --site localhost console
```
```python
import frappe
# Should show disable_like: 1
doc = frappe.get_doc("List View Settings", "BOQ Header")
print(doc.as_dict().get("disable_like"))

# Should show no duplicates
meta = frappe.get_meta("List View Settings")
from collections import Counter
dupes = {k: v for k, v in Counter([f.fieldname for f in meta.fields]).items() if v > 1}
print("Duplicates:", dupes)  # Should be {}
```

### Step 2: Check API response
Open browser DevTools → Network → find `get_list_settings` call → check response has `"disable_like": 1`.

### Step 3: Check UI
Navigate to BOQ Header list view. The heart icon column (both header toggle and per-row like button) should be gone.

### Step 4: Verify space collapses
With both `disable_like=1` AND `disable_comment_count=1`, the `.level-right` area should collapse to minimal width (no more 130px fixed sidebar).

### Step 5: Verify dropdown not overlapped
Open any dropdown menu in the list view — it should appear ABOVE the sticky right area, not behind it.

### Step 6: Re-enable (if needed)
Go to BOQ Header → List View Settings → uncheck "Disable Like" → Save.

---

## 6. Important Notes for Codex

### Caching gotcha
`frappe.get_cached_doc` caches Document objects for 3600 seconds. After modifying the DocType JSON:
```bash
bench --site localhost console
```
```python
import frappe
frappe.clear_document_cache("List View Settings", "BOQ Header")
frappe.clear_cache()
```

### The like column is NOT a regular column
It lives in `.level-right` (sticky sidebar), not in `.level-left` (configurable columns). It's rendered by:
- `get_header_html()` for the header toggle
- `get_meta_html()` for per-row buttons

It is NOT part of the `this.columns` array managed by `setup_columns()`.

### The modified date cannot be disabled separately
The modified date (`<span class="modified">`) is always rendered in `get_meta_html()` — there is no `disable_modified` setting. If the user wants to hide it too, a new setting would need to be added.

### Construction app does NOT override like functionality
Confirmed: no overrides in any of the construction app's 38 JS files. The monkey-patches in `native_frappe_controls_compat.js` (line 311-328) only add column-resize handles after `render_header`/`render_list` — they don't modify the like button DOM.

### Files involved (complete list)
| File | Role |
|------|------|
| `apps/frappe/frappe/desk/doctype/list_view_settings/list_view_settings.json` | DocType definition |
| `apps/frappe/frappe/desk/doctype/list_view_settings/list_view_settings.py` | Type hints + save logic |
| `apps/frappe/frappe/public/js/frappe/list/list_view.js` | Header + row rendering + no-activity class |
| `apps/frappe/frappe/public/js/frappe/list/base_list.js` | Loads settings via API |
| `apps/frappe/frappe/desk/listview.py` | API endpoint |
| `apps/frappe/frappe/public/scss/desk/list.scss` | CSS: sticky positioning, no-activity collapse, dropdown z-index |

---

## 7. Rollback

To revert all changes:
```bash
cd /home/mohamed/frappe-bench
git checkout -- apps/frappe/frappe/desk/doctype/list_view_settings/list_view_settings.json
git checkout -- apps/frappe/frappe/desk/doctype/list_view_settings/list_view_settings.py
git checkout -- apps/frappe/frappe/public/js/frappe/list/list_view.js
git checkout -- apps/frappe/frappe/public/scss/desk/list.scss
bench migrate
bench build --app frappe
bench clear-cache
```
