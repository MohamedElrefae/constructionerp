# Stage 4 — `ar`/`en`-session browser regression evidence (2026-09-20)

## Scope

Executed the shipped manual verification script
(`construction/public/js/bilingual/account_bilingual_browser_tests.js`) in an
automated headless browser (Playwright 1.60.0, bundled Chromium) against the
authorized test site `v16.localhost`, with the site services on merged
`develop` @ `24d1290`. Runner preserved as
`stage4-browser-regression-runner-2026-09-20.py` (raw outputs as the two JSON
files in this directory).

## Result summary — 0 failures in both sessions

| Session | `frappe.boot.lang` | Checks | Verdict |
|---|---|---|---|
| `ar` | `ar` (verified in-page) | 7 | **6 PASS / 1 SKIP / 0 FAIL** |
| `en` | `en` | 7 | **6 PASS / 1 SKIP / 0 FAIL** |

Checks executed (identical in both sessions):

1. Arabic label uses Arabic name without internal-name append — PASS (pure logic)
2. Arabic fallback English → identity, still no internal-name append — PASS
3. English session prefers English then Arabic — PASS
4. Labels are HTML-escaped (XSS) — PASS
5. Identity section renders on the open Account form — PASS (live)
6. Identity section text nodes are escaped (no raw HTML injection) — PASS (live)
7. Tree labels show Arabic without internal name — **SKIP (not on a tree page; see limitation below)**

## Live identity-section snapshot (GST - E, non-production test site)

- `ar` session: English cell `GST`, Arabic cell `ضريبة السلع والخدمات`,
  completeness caption itself localizes (`مفقود: code`), `boot_lang=ar`.
- `en` session: English cell `GST`, Arabic cell `ضريبة السلع والخدمات`,
  caption `Missing: code`, `boot_lang=en`.

## Honest limitations

1. **Tree live DOM check not executed in the browser.** The CoA tree route
   (`/app/account/view/tree`) does not complete its mount in the headless run:
   an unrelated, pre-existing vendor crash aborts the page render —
   `SidebarItem.get_path` throws `Cannot read properties of undefined
   (reading 'public')` on a missing `frappe.boot.workspaces` entry (desk
   bundle `6DET2CQ3`). This is site workspace-configuration drift, not part of
   the bilingual change. **The governed data path behind the tree labels was
   verified headlessly instead**: `get_account_tree_children` returns every
   child node with `account_name`/`account_number`/`account_name_ar` merged
   (e.g. `الأصول المتداولة`, `مصروفات مباشرة`, `إيرادات مباشرة`). The manual
   devtools paste of the same script on a rendered tree remains the one
   open manual step for full tree DOM evidence.
2. Login/boot steps within the runner timed out on some runs because the desk
   lands on `/index` and sockets keep the load state non-idle; the form checks
   themselves are unaffected (they wait on `cur_frm` directly).

## Session state restored

`Administrator.language` was temporarily set to `ar` then `en` for the two
sessions and restored to the original value (`en`). A temporary admin
password (`CtBrw-2026-tmp`) was set via `bench set-admin-password`;
**revocation of this temporary password is a pending owner action.**
