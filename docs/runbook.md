# Operations Runbook

## Construction ERP White-Label Theming System

---

## 0. Deployment Pre-Flight (MANDATORY before any migrate/deploy)

> Added 2026-08-21 per consultant handoff `CONSULTANT_HANDOFF_GM_2026-08-21.md` (risks R1, R2).
> **Never run `bench migrate` on a site without completing this section first.**

### 0.1 One-command check

```bash
bash apps/construction/scripts/preflight_check.sh <site-name>
```

The script verifies:
| Check | Why |
|-------|-----|
| `redis_cache` answers PING | App sessions/cache break silently if down; tests and UI fail with confusing errors (incident 2026-08-21) |
| `redis_queue` answers PING | Background jobs stall if down |
| Site directory exists | Catches typos before they hit the wrong site |
| Database backup < 24h old | Rollback point for schema migration (R2) |
| ≥ 2 GB free disk | Backups + migration need headroom |

Exit code `0` means these preflight checks passed. Deployment also requires a qualified candidate, the named site’s authorization, a recoverable backup and the applicable release decision. **Any FAIL/WARN = stop and fix first.** See the [documentation index](DOCUMENTATION_INDEX.md) and current operating profile.

### 0.2 Full deployment sequence

```bash
# 1. Pre-flight (must exit 0)
bash apps/construction/scripts/preflight_check.sh <site-name>

# 2. Fresh backup with files (if pre-flight flagged it stale)
bench --site <site-name> backup --with-files

# 3. Deploy
bench --site <site-name> migrate
bench build --app construction
bench restart

# 4. Post-deploy sanity: re-run pre-flight + one non-admin smoke test
bash apps/construction/scripts/preflight_check.sh <site-name>
```

### 0.3 If Redis is down at the client server

```bash
redis-server config/redis_cache.conf --daemonize yes
redis-server config/redis_queue.conf --daemonize yes
```

Then re-run the pre-flight script. If the client uses systemd/supervisor, enable those units instead so Redis survives reboots.

**Recovery symptoms (observed 2026-10-14 during F22 browser work):** Redis dying does not always present as a Redis error. It presented as
- intermittent `PermissionError`s that looked like permission defects, and
- `500 The page could not be built` on a workspace route, with a traceback ending in
  `Error 111 connecting to 127.0.0.1:13000`.

Confirm before diagnosing anything else:

```bash
redis-cli -p 13000 ping   # cache: must answer PONG
redis-cli -p 11000 ping   # queue: must answer PONG
```

Both instances must be up. A single live `redis-server` process on 6379 (a leftover system
instance) is not the bench's Redis. After restarting them, re-take any evidence gathered
while they were down — a permission or routing conclusion drawn from an outage is not
valid evidence.

---

## 0.4 Identifying which site served an HTTP request (MANDATORY before UI evidence)

`bench serve` binds **one** site at startup, chosen in this order: `--site`, then
`$FRAPPE_SITE`, then `default_site` in `sites/common_site_config.json`
(`frappe/utils/bench_helper.py` → `get_sites`). It does **not** re-read the setting per
request, and `dns_multitenant` does not change that: with `serve_default_site: true`,
`frappe.app.init_request` resolves the site from the bound `_site` **before** the Host
header is considered.

Consequences, all observed 2026-10-14:

- A `Host:` header or `X-Frappe-Site-Name` header does **not** select the site.
- A refused login does not identify the site: `f04-pm@v16rehearsal.local` was answered
  `Invalid login credentials` by `v16.localhost`, where that user does not exist, and the
  rehearsal site's own credentials worked server-side. **Never treat "Invalid login
  credentials" as evidence about credentials.**
- Changing `default_site` requires a server restart to take effect.

Verify the serving site first, then take UI evidence:

```bash
# 1. Which site is bound?
ps aux | grep '[b]ench_helper'                 # shows "frappe serve --port 8000"
grep default_site sites/common_site_config.json

# 2. Positive proof: log in a user that exists on exactly one site.
curl -s -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'usr=<user>@v16rehearsal.local&pwd=<password>' \
  http://127.0.0.1:8000/api/method/login
# {"message":"Logged In"} means that site is being served. 401 "Invalid login
# credentials" means either the wrong site or the wrong password — resolve which
# with a direct server-side check (frappe.auth.check_password) before concluding.

# 3. Or read the site's own log after a request:
ls -t sites/*/logs/frappe.log | head -3       # the freshest entry names the site
```

For rehearsal-site UI work, temporarily set `default_site` (disclosed in the work item),
restart `bench serve`, verify by step 2, and restore the previous value afterwards.

---

## 0.5 Cache-buster discipline and safe restarts (F25, 2026-10-14)

**After any `?v=` bump in `hooks.py`:** the `?v=` query defeats *browser* caching, but the
desk HTML embedding those URLs is itself server-cached. Always run, in order:

```bash
bench --site <site> clear-cache
# then verify the served HTML carries the new versions BEFORE browser evidence:
curl -s <desk-url> | grep -o "vite_layout_controls.js?v=[0-9.]*"
```

A passing `frappe.get_hooks` read is not proof the browser will receive it — the served
HTML is the proof.

**Restarting `bench serve`:** never `pkill -f` with a pattern that matches your own shell
command (observed 2026-10-14: `pkill -f "bench_helper frappe serve"` matched the shell
running it and killed the operator session along with the server). Use the port to find the
exact PID, or a bracket pattern that cannot self-match:

```bash
SS=$(ss -ltnp 2>/dev/null | grep ':8000' | grep -oP 'pid=\K[0-9]+' | head -1)
kill $SS
# or: pkill -f "[b]ench_helper frappe serve"
sleep 3
nohup /home/mohamed/.local/bin/bench serve --port 8000 > /tmp/opencode/<task>.log 2>&1 &
sleep 15; curl -s -o /dev/null -w "ping=%{http_code}\n" http://127.0.0.1:8000/api/method/frappe.ping
```

After any restart, re-verify Redis (`redis-cli -p 13000 ping`, `-p 11000 ping`) and the
serving site (§0.4) before resuming evidence.

---

## 0.6 Recovery rehearsal (F32 preparation — no execution here)

Backup integrity for the F02 baseline (`20261013_052916`, verified 2026-10-14 with
`gzip -t` / `tar -t`, all three archives OK):

- `sites/v16rehearsal.localhost/private/backups/20261013_052916-v16rehearsal_localhost-database.sql.gz` (68 MB)
- `...-files.tar`, `...-private-files.tar`

Restore rehearsal (operator with DBA access, isolated site only — never over a live site):

```bash
bench new-site <recovery>.localhost --admin-password '<from-operator-channel>'
bench --site <recovery>.localhost restore \
  sites/v16rehearsal.localhost/private/backups/20261013_052916-v16rehearsal_localhost-database.sql.gz \
  --with-private-files sites/v16rehearsal.localhost/private/backups/20261013_052916-v16rehearsal_localhost-private-files.tar \
  --with-public-files sites/v16rehearsal.localhost/private/backups/20261013_052916-v16rehearsal_localhost-files.tar
bench --site <recovery>.localhost install-app construction
bench --site <recovery>.localhost migrate
```

Rollback decision: if migration fails, the decision is restore-again vs fix-forward, made by
the operator with the engineer — never `--force` a migrate past a DDL error, and never
restore over the site the backup came from without a fresh backup first. The rehearsal must
record row counts (BOQ Header/Item/Structure, Cost Analysis, Quantity Revision, File) before
and after, plus the permission-reconciliation baseline diff.

---

## Quick Reference

| Task | Command/Location |
|------|------------------|
| Check theme status | `bench --site [site] console` → `check_themes.py` |
| Clear theme cache | `bench --site [site] clear-cache` |
| Rebuild assets | `bench build` |
| Force theme re-apply | Delete `construction_theme` from localStorage |
| View error logs | `bench --site [site] show-logs` |

---

## 1. Daily Operations

### 1.1 Verify System Themes Exist

```bash
cd frappe-bench
bench --site construction.local console
```

```python
# In console
import frappe
themes = frappe.db.sql("""
    SELECT name, is_system_theme, is_active, 
           is_default_light, is_default_dark, theme_type
    FROM `tabConstruction Theme`
""", as_dict=True)

for t in themes:
    print(f"{t['name']}: system={t['is_system_theme']}, active={t['is_active']}")
```

**Expected Output:**
```
Light: system=1, active=1
Dark: system=1, active=1
Construction Light: system=1, active=1
Construction Dark: system=1, active=1
```

### 1.2 Check Default Themes Set

```python
# In console
has_default_light = frappe.db.exists("Construction Theme", 
    {"is_system_theme": 1, "is_default_light": 1})
has_default_dark = frappe.db.exists("Construction Theme", 
    {"is_system_theme": 1, "is_default_dark": 1})

print(f"Default Light: {has_default_light}")
print(f"Default Dark: {has_default_dark}")
```

**If missing:**
```python
frappe.db.set_value("Construction Theme", "Construction Light", "is_default_light", 1)
frappe.db.set_value("Construction Theme", "Construction Dark", "is_default_dark", 1)
frappe.db.commit()
```

---

## 2. Troubleshooting

### 2.1 Theme Not Applying

**Symptoms:** White background in dark mode, sidebar wrong color

**Checklist:**
1. ✅ CSS files loading (Network tab → look for 200 on modern_theme_*.css)
2. ✅ data-theme attribute set (DevTools → Elements → `<html>`)
3. ✅ data-modern-theme attribute set
4. ✅ No CSS 404 errors

**Quick Fix:**
```javascript
// In browser console
localStorage.removeItem("construction_active_theme");
localStorage.removeItem("construction_theme");
localStorage.removeItem("construction_mode");
location.reload();
```

### 2.2 Sidebar Text Invisible

**Symptoms:** Sidebar links not visible or wrong color

**Diagnosis:**
```javascript
// Check computed styles
const link = document.querySelector('.desk-sidebar .item-anchor');
console.log(getComputedStyle(link).color);
```

**Expected:** `rgb(232, 245, 233)` (light green-white for dark theme)

**Fix:**
```javascript
// Force color fix
document.querySelectorAll('.desk-sidebar a, .layout-side-section a').forEach(a => {
    a.style.color = '#e8f5e9';
});
```

**Permanent Fix:** Check `modern_theme_dark.css` has sidebar selectors.

### 2.3 Theme Resets After Page Change

**Symptoms:** Theme switches back to light when navigating

**Causes:**
1. localStorage cleared by Frappe (fixed in modern_theme_loader_v2.js with interceptor)
2. API returning wrong theme
3. MutationObserver conflict

**Diagnosis:**
```javascript
// Check interceptor is working
localStorage.setItem("test_key", "test_value");
localStorage.clear();
console.log("test_key after clear:", localStorage.getItem("test_key"));
// Should still exist due to interceptor
```

### 2.4 TimestampMismatchError

**Symptoms:** Error when switching themes rapidly

**Status:** Fixed in `save_user_mode()` using direct DB update

**If still occurring:**
```python
# Check user record
doc = frappe.get_doc("User", "user@example.com")
print(doc.modified)  # Should not change on theme switch
```

### 2.5 FOUC (Flash of Unstyled Content)

**Symptoms:** White flash before dark theme loads

**Fix:** Check `boot_session` is injecting theme early:
```python
# Verify boot injection
from construction.api.theme_api import add_theme_to_boot
bootinfo = {}
add_theme_to_boot(bootinfo)
print(bootinfo.get("construction_theme"))
```

---

## 3. Configuration Management

### 3.1 Change Default Site Theme

```python
# Set site-wide default
from frappe.utils import now

# For light mode default
frappe.db.set_value("Construction Theme", "Construction Light", {
    "is_default_light": 1,
    "modified": now()
})

# For dark mode default  
frappe.db.set_value("Construction Theme", "Construction Dark", {
    "is_default_dark": 1,
    "modified": now()
})

frappe.db.commit()
```

### 3.2 Create Custom Theme

1. Go to **Construction Theme** list
2. Click **New**
3. Set:
   - Theme Name: "Client Brand"
   - Theme Type: "Custom Light" or "Custom Dark"
   - Colors per specification
4. Check **Is Active**
5. Set as default if desired

### 3.3 Enable User Theme Overrides

1. Go to **Modern Theme Settings**
2. Check **Allow User Override**
3. Save

Users can then set personal themes in User Desk Theme.

### 3.4 Disable User Theme Overrides

```python
# Force all users to site default
settings = frappe.get_doc("Modern Theme Settings")
settings.allow_user_override = 0
settings.save()

# Optional: Clear user preferences
frappe.db.sql("""
    UPDATE `tabUser Desk Theme` 
    SET inherit_from_site = 1
""")
frappe.db.commit()
```

---

## 4. Performance Optimization

### 4.1 Check CSS File Sizes

```bash
cd frappe-bench/apps/construction/construction/public

# Check raw sizes
ls -la css/

# Check gzipped sizes
gzip -c css/modern_theme_tokens.css | wc -c
gzip -c css/modern_theme_base.css | wc -c
gzip -c js/theme_loader.js | wc -c
```

**Targets:**
- CSS tokens: < 10KB gzipped
- CSS base: < 10KB gzipped
- JS loader: < 15KB gzipped

### 4.2 Clear Theme Cache

```python
# Clear all theme-related cache
frappe.cache().delete_key("construction_theme:*")
frappe.cache().delete_key("bootinfo")

# Clear per-user cache
for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
    frappe.cache().hdel("bootinfo", user)
```

### 4.3 Optimize CSS Delivery

If files are too large:
1. Split by component (already done)
2. Lazy-load non-critical CSS
3. Use `media` queries for conditional loading

---

## 5. Security Considerations

### 5.1 Sanitize User Input

Theme names are validated against allowed characters:
- Alphanumeric
- Spaces (converted to underscores)
- No HTML/script tags

### 5.2 XSS Prevention

CSS injection points:
- ✅ `injectCSS()` uses `textContent` (not `innerHTML`)
- ✅ API validates theme names
- ✅ No user-generated CSS allowed (only admin-defined themes)

### 5.3 Permission Checks

| Function | Permission Required |
|----------|-------------------|
| save_modern_theme_settings | Modern Theme Settings: write |
| save_user_theme_settings | Self-only (if_owner) |
| get_modern_theme_settings | Modern Theme Settings: read |

---

## 6. Monitoring

### 6.1 Key Metrics

| Metric | How to Check | Target |
|--------|--------------|--------|
| Theme load time | Performance API in browser | < 200ms |
| CSS file size | Network tab | < 50KB total |
| FOUC incidents | Visual inspection | 0 |
| API error rate | Error logs | < 1% |

### 6.2 Log Analysis

```bash
# View theme-related errors
bench --site construction.local show-logs | grep -i "theme\|construction"

# View API calls
bench --site construction.local console
```

```python
# Query error log
errors = frappe.get_all("Error Log", 
    filters={"method": ["like", "%theme%"]},
    fields=["method", "error"],
    order_by="creation desc",
    limit=10
)
```

---

## 7. Disaster Recovery

### 7.1 Theme System Broken

**Restore from fixtures:**
```bash
bench --site construction.local export-fixtures
bench --site construction.local import-fixtures
```

**Or recreate system themes:**
```python
from construction.install import create_system_themes
create_system_themes()
frappe.db.commit()
```

### 7.2 Complete Reset

```bash
# 1. Clear all theme data
bench --site construction.local console
```

```python
# Delete user preferences
frappe.db.sql("DELETE FROM `tabUser Desk Theme`")

# Reset to Frappe default
frappe.db.sql("UPDATE `tabUser` SET desk_theme = 'Light'")

# Clear cache
frappe.cache().flushall()
frappe.db.commit()
```

```bash
# 2. Rebuild
bench build
bench --site construction.local migrate
```

---

## 8. Upgrade Procedures

### 8.1 Before Frappe Update

```bash
# Export current themes
bench --site construction.local export-fixtures

# Backup custom themes
mysqldump -u root -p [database] --tables `tabConstruction Theme` > theme_backup.sql
```

### 8.2 After Frappe Update

```bash
# Run migration (applies whitelabel_patch)
bench --site construction.local migrate

# Verify themes still work
bench --site construction.local console
```

```python
# Verify
from construction.api.theme_api import get_effective_desk_theme
print(get_effective_desk_theme("dark"))
```

---

## 9. Contact & Escalation

| Issue | Contact |
|-------|---------|
| Theme not applying | Check this runbook → Clear cache |
| CSS bugs | Engineering Team |
| Feature requests | Product Team |
| Critical production issue | On-call engineer |

---

*Last Updated: 2026-08-21 (added §0 Deployment Pre-Flight)*
