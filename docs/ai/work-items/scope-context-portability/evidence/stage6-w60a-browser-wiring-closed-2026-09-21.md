# W6-0a — browser wiring diagnosis + live DOM verification closed (2026-09-21)

Owner decision (2026-09-21): green-light the W6-0a browser wiring
investigation and live DOM re-verification; W6-0b deferred.

## Root causes (two real environmental faults, both corrected)

1. **Bench Redis instances were dead.** The managed cache/queue servers on
   ports 13000/11000 had stopped (only the OS-level redis on 6379
   remained). Consequences observed end-to-end:
   - desk pages intermittently rendered with an effectively empty
     `__messages` payload (silent English rendering even in an `ar`
     session);
   - at the deeper point, the desk page 500s (`Connection refused` from
     redis inside `www/desk.py get_context`).
   Fix: restarted the managed redis servers from the bench configs
   (`redis-server config/redis_cache.conf` + `redis_queue.conf`); desk
   page HTTP 200 again; `bench clear-cache` invalidated boot/translation
   caches.
2. **Session language and boot-content coherence.** The Desk page embeds
   `frappe.boot["__messages"]` (= `get_messages_for_boot()` = the merged
   per-session-language dictionary; ~10,752 entries for `ar`, 44
   country-only entries for `en` — i.e. the boot payload follows the
   current session language correctly). My earlier English results were
   probes where (a) the session had booted as an `en`-language Administrator
   (my own restore step) or (b) Redis was degraded. Both are environment
   states, not batch defects.

## Live Desk `ar`-session verification (decisive, completed)

Real Desk session (Administrator, `frappe.boot.lang=ar`):

- `frappe._messages` **10,752 entries** loaded at boot (includes the W6-0a batch);
- in-page `__()` resolution of representative W6-0a rows:
  - `Add / Remove Columns` → `إضافة / إزالة الأعمدة`
  - `Bulk PDF Export` → `تصدير PDF جماعي`
  - `Invalid Filter` → `عامل تصفية غير صالح`
  - `Report {0} saved` → `حُفِظ التقرير TB-01`
  - `Duplicate Entry` → `مدخل مكرر`
  - `Add {0}` → `إضافة Role` (glossary-consistent noun retention)
  - `Cancel All` → `إلغاء الكل` · `Copy Link` → `نسخ الرابط`
- **rendered-DOM check**: actual rendered Arabic in the live Desk page
  (sidebar/workspace labels): `الفوترة`, `بحث`, `إشعار`, `الرئيسية`,
  `لوحة المعلومات`, `دليل الحسابات`, `المستحقات للغير…`, `العميل`.

## Status update

- W6-0a is now **visually complete on the test site**: the shipped
  overrides reach and render in a real Desk `ar` session (dictionary
  wiring, boot payload, and DOM text all verified).
- No code or catalog change was needed (pure environmental restoration);
  therefore no gate re-run or additional evidence re-pin was required by
  this fix. The surviving strict-gate HEAD-pin mismatch remains the
  expected single item until the next catalog event.
- Site restored after the run: temp admin password revoked (unrecorded
  replacement), Administrator language back to `en`.

## Operational note (owner action recommended)

Ensure the bench-managed Redis (cache 13000 + queue 11000 + web 9000 if
used) is kept running/restarted with the bench process; a silent redis
death degrades Desk boot content without failing other flows.
