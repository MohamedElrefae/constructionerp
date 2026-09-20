# Stage 4 — CoA tree live verification closed (2026-09-20, follow-up to stage4-browser-regression)

This record closes the one limitatation left by
`stage4-browser-regression-2026-09-20.md`: the tree-routed DOM check.

## Root cause of the prior blocker — found and repaired (data-only)

The `/browser/account/view/tree` route aborted rendering with an uncaught
`SidebarItem.get_path` crash (`Cannot read properties of undefined (reading
'public')`). Precise in-page Proxy instrumentation attributed it to a missing
Workspace slug `accounting` in `frappe.workspaces`, caused by one stale
record:

- `Workspace Sidebar Item` row `aonu1hu7j6` ("Home", link_type Workspace,
  link_to "Accounting") under the "Accounting" sidebar group — while **no
  Workspace named Accounting exists** on the site (ERPNext workspace/fixture
  drift; the group's other 10 items are DocType/Report/Dashboard links that
  never consult `frappe.workspaces`).

**Repair: data-only deletion of that single stale row** (governed
`frappe.delete_doc`, cache cleared). After repair the tree route mounts with
zero page errors (`window.__miss` recorder: `{}`).

## Tree DOM verification (headless Playwright, real session)

With the tree's Company filter set to **Elrefae** (the pilot chart; the
default company chart "Best Test" is a vendor test chart whose accounts are
out of the 81-account migration scope and hence correctly render the English
fallback chain), in an `frappe.boot.lang = ar` session the live tree renders
the migrated Arabic:

- root: `Elrefae`
- `استخدامات الأموال (الأصول)` (Application of Funds (Assets))
- children: `الأصول المتداولة`, `الأصول الثابتة`, `الاستثمارات`, `الحسابات المؤقتة`
- plus `مصادر الأموال (الالتزامات)`, `حقوق الملكية`, `الإيرادات`, `المصروفات`

The shipped verification script
(`construction/public/js/bilingual/account_bilingual_browser_tests.js`)
executed on that rendered tree:

| Session/context | Checks | Verdict |
|---|---|---|
| tree page, `ar`, Elrefae company | 7 | **5 PASS / 2 SKIP / 0 FAIL** — includes `tree labels show arabic without internal name (arabic session)` **PASS** |
| form page, `ar` (prior evidence) | 7 | 6 PASS / 1 SKIP / 0 FAIL |
| form page, `en` (prior evidence) | 7 | 6 PASS / 1 SKIP / 0 FAIL |

All 7 script checks now pass live across the two contexts; the two identity
checks legitimately SKIP off-form (and did PASS in the form-context runs).

## Method note (honest scope)

The Company filter was set programmatically in-page
(`frappe.views.trees['Account'].args.company = 'Elrefae'`, then
`make_tree()`); the default-company chart rendering is unchanged vendor
behavior. Login used a temporary site admin password during this session;
it was revoked afterwards, and `Administrator.language` restored to `en`.

## Verdict

Stage 4 "Visible bilingual display" — tree-routed DOM evidence now **closed
headless**, in addition to the earlier form/identity/search evidence. The
manual devtools paste step is no longer blocking for the non-production
test site.
