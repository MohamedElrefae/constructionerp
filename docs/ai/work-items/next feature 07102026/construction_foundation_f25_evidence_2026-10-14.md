# F25 — Runtime and asset consistency (evidence)

Date: 2026-10-14 · Site: `v16rehearsal.localhost` (positive identity: `f04-pm` login, a user
existing only there) · Installed: frappe 16.51.1 (`2871914`), erpnext 16.50.0 (`7474d9e`),
Python 3.14 venv · Redis cache 13000 + queue 11000 both PONG.

This closes the runtime half of the F25 source review (2026-10-12): actual loaded assets,
hook registration, build reproducibility, cache invalidation and dependency/CI alignment —
measured, not configured.

## 1. JS target list (F24-D001 carried in, resolved here)

Each compat patch mapped to its upstream file/function at the installed vendor revision,
with a regression check. This table is the vendor-upgrade prerequisite: re-run it on any bump.

`frappe_compat_patches.js` (vendor rev `2871914`):

| Patch | Upstream target | Present at this rev? | Regression check |
|---|---|---|---|
| `patchTreeViewNewNodeGuard` | `frappe.views.TreeView.prototype.new_node` (`frappe/public/js/frappe/views/treeview.js:701`) | yes | wraps and delegates via `originalNewNode.apply`; guard flag `__ct_new_node_guard_patch` prevents double-wrap; retries on `app_ready` when the class is absent |
| `patchSavedFiltersGroupLabel` | `frappe.ui.Page.prototype.get_or_add_inner_group_button` (`:757`) / `get_inner_group_button` (`:827`) | yes, both | wraps both, normalises the Saved-Filters group by encoded data-label (works across languages); idempotent flag |
| `patchSidebarWorkspaceNavigation` | `frappe.ui.SidebarHeader.prototype.setup_select_options` / `add_app_item` (`frappe/public/js/frappe/ui/sidebar/sidebar_header.js`) | **no** — neither method exists in this file at this rev | dormant by guard: the direct assignments create methods the vendor never calls; the safety-net wrapper skips when the original is absent (`if (!proto.__ct_workspace_handler_wrapped && originalSetupSelect)`). Harmless but dead — remove or re-target on the next vendor review |
| `patchWorkspaceMenuNavigation` | `frappe.ui.create_menu.prototype.add_menu_item` | **no** — `frappe.ui.create_menu` does not exist anywhere in the installed public JS | dead by guard (returns false, retries on `app_ready`). Same disposition as above |

`native_frappe_controls_compat.js`:

| Patch | Upstream target | Present? | Check |
|---|---|---|---|
| `patchListViewMenu` | `frappe.views.ListView.prototype.get_menu_items` (`frappe/public/js/frappe/list/list_view.js:2531`) | yes | appends List Settings only when absent; non-System-Manager callers get the permission message instead of `show_list_settings` (`:2703`); flag `__ct_native_menu_patched` |
| `patchListViewRenderHooks` | `render_header` (`:839`) / `render_list` (`:1003`) | yes, both | wraps and delegates, installs column-resize handles on two timers; flag `__ct_native_resize_render_patched` |

F24-D001 is therefore closed as inventoried: four patches live against verified targets, two
are guarded dead code against this vendor rev. The standing rule for bumps: re-run this
table; a patch whose target disappears must be removed or re-targeted, never left assuming.

## 2. Test teardown (F24-D002 closed)

`test_security_audit_remediation` teardown tried to controller-delete Approved Quantity
Revisions, which the product guard correctly refuses (approved history is permanent). Fixed
without touching product code: controller delete is still attempted first, and only when the
refused row is Approved **and** its VO is in the test's own tracked list does teardown remove
the isolated fixture row directly (`frappe.db.delete`). Any other refusal still fails loudly.
Result: **24/24 OK**. `test_scope_and_measurement_policy` 5/5 (uses the dedicated
`f23-scopeless` account per F22-D008).

## 3. Loaded assets, hook registration, build, cache

- **Hook registration (live):** `frappe.get_hooks("app_include_js", app_name="construction")`
  returns the bumped URLs (`vite_layout_controls.js?v=1.22`, …).
- **Loaded assets (browser, one clean context, site-asserted):** all five probed files
  return HTTP 200 with the expected `?v=` — `vite_layout_controls.js` 1.22,
  `vite_form_override.css` 1.6, `vfc_layout_engine.js` 1.44, `ct_link_control.js` v17,
  `frappe_compat_patches.js` v2. The VFC panel opens and the F23-D002 density label is live.
- **Build reproducibility:** source and served asset are byte-identical
  (`md5 2ed02e36…` for both `apps/construction/construction/public/js/vite_layout_controls.js`
  and `sites/assets/construction/js/vite_layout_controls.js`) — these raw assets ship
  without a bundling transform, so what is reviewed is what is served.
- **Cache invalidation (found the hard way):** after the `?v=` bump the desk HTML still
  served the old versions until `bench --site v16rehearsal.localhost clear-cache`. The
  `?v=` query defeats *browser* caching, but the HTML embedding the URLs is itself
  server-cached. Procedure going forward: bump `?v=`, then `clear-cache`, then verify the
  served HTML carries the new versions before taking browser evidence. (This also explains an
  earlier confusing reading in this session; no code was wrong.)
- **Cache-buster discipline:** the F23-D002 edits shipped without a bump; corrected here
  (`vite_layout_controls.js` 1.21→1.22, `vite_form_override.css` 1.5→1.6) per the standing
  rule. Doctype/page JS (`boq_header.js`, viewer) rides the framework's own asset pipeline
  and carries no manual `?v=`.

## 4. Dependency / CI alignment

The F25 review's S1 blocker (five app ranges disjoint from CI-pinned frappe 16.18) is stale:
the bench now runs frappe 16.51.1, whose `pyproject.toml` declares the **same** five ranges
(`cryptography~=50.0.0`, `pyOpenSSL~=26.4.0`, `Pillow~=12.3.0`, `sqlparse~=0.6.0`,
`sql_metadata~=3.0.1`), and the venv holds satisfying versions (cryptography 50.0.2, Pillow
12.3.0, pyOpenSSL 26.4.0, sqlparse 0.6.0, sql_metadata 3.0.1). `pip check` reports only
unrelated drift (filelock, PyJWT, pypdf, WeasyPrint, Werkzeug newer than pinned) — not the
five governed ranges, and not caused by this program. CI-pin vs bench alignment (F13) remains
the owner's call; the runtime measured here is coherent.

## 5. Full-asset sweep (2026-10-15)

Sweep script: `isolated-qualification-evidence-2026-10-15/f25_asset_sweep.py` — enumerates
**every** hooks-registered asset (`app_include_css` ×6, `app_include_js` ×27,
`web_include_css` ×2, `web_include_js` ×1, `website_context` images ×3 = 38 registrations),
resolves each to source (`construction/public/…`) and served (`sites/assets/construction/…`),
and compares md5.

Result: **0 source-missing · 0 not-synced · 0 byte-mismatch** — all 38 registered
regensions are byte-identical between review and serve. 7 registrations intentionally ride
the framework pipeline without a manual `?v=` (print/export menus, dropdown utils,
email_theme.css, logo images).

**Finding F25-D003 (hygiene, no functional impact):** `modern_theme.css` is registered at
two versions — `app_include_css` carries `?v=2.5.9`, `web_include_css` carries `?v=2.5.8`.
Both URLs resolve to the same file and serve identical bytes, so no staleness exists today;
the split only risks a stale login-page cache after a future theme edit that bumps one
registration and not the other. **Disposition:** align `web_include_css` to `2.5.9` in the
F38 batch (one-line, no behavior change) and add the standing rule: theme edits bump
**both** registrations together, and this sweep runs on every candidate freeze.

## 6. Status

F25 **Engineering verified** for runtime/asset consistency on the measured stack: targets
inventoried with per-patch regression checks, teardown repaired (24/24), all 38 registered
assets loaded byte-identical, hooks live, build reproducible, cache procedure corrected,
dependencies coherent, full sweep clean with one hygiene finding dispositioned into the
F38 batch. Owner acceptance stays in the consolidated final block.
