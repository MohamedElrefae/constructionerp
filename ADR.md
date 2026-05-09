# Architecture Decision Records (ADR)

## Construction ERP White-Label Theming System

---

## ADR-001: CSS Variable Token Architecture

**Status:** Accepted  
**Date:** 2026-04-15  
**Deciders:** Mohamed Elrefae, Engineering Team

### Context
Frappe/ERPNext uses hardcoded colors throughout its UI. We need a white-label theming system that allows complete visual customization without modifying core Frappe files.

### Decision
Implement a **CSS Variable Token Architecture** with three specificity levels:

1. **Level 1:** Root tokens ( `--primary`, `--bg`, `--text` )
2. **Level 2:** Theme-specific values ( `[data-theme="dark"]` )
3. **Level 3:** Frappe variable mapping ( `--blue-500: var(--primary) !important` )

### Consequences
- ✅ Complete visual override possible
- ✅ Runtime theme switching without page reload
- ✅ Consistent 54-token vocabulary across all components
- ⚠️ Requires `!important` for cascade victory
- ⚠️ Shadow DOM components need separate injection

---

## ADR-002: Server-Side Theme Resolution

**Status:** Accepted  
**Date:** 2026-04-20  
**Deciders:** Mohamed Elrefae

### Context
Client-side theme detection causes FOUC (Flash of Unstyled Content). User preferences need persistence across devices.

### Decision
Move theme resolution to **server-side** via:
- `boot_session` hook injects theme config into `frappe.boot`
- `User Desk Theme` DocType stores per-user preferences
- `Construction Theme` DocType stores site-wide defaults

### Consequences
- ✅ No FOUC - theme known at HTML render time
- ✅ Cross-device synchronization
- ✅ Admin-controlled default themes
- ⚠️ Additional database queries on boot
- ⚠️ Cache invalidation complexity

---

## ADR-003: TimestampMismatchError Prevention

**Status:** Accepted  
**Date:** 2026-04-22  
**Deciders:** Mohamed Elrefae

### Context
Frappe's `User` DocType uses optimistic locking. Concurrent theme switches from multiple tabs cause `TimestampMismatchError`.

### Decision
Use **direct database updates** for theme persistence:
```python
frappe.db.set_value("User", user, "desk_theme", value, update_modified=False)
```

Avoid ORM `doc.save()` for high-frequency user preference updates.

### Consequences
- ✅ No locking conflicts
- ✅ Silent background updates
- ⚠️ Bypasses Frappe's validation hooks
- ⚠️ Audit trail incomplete

---

## ADR-004: CSS Generation Strategy (Hybrid)

**Status:** Accepted  
**Date:** 2026-04-25  
**Deciders:** Mohamed Elrefae

### Context
Pure static CSS can't handle dynamic theme configuration. Pure dynamic CSS has performance cost and flash of unstyled content.

### Decision
**Hybrid Approach:**
1. **Static CSS files** (modern_theme_tokens.css, modern_theme_base.css) - immediate render
2. **Dynamic CSS injection** via API (theme_api.get_theme_css_variables) - customization layer
3. **Inline style injection** for runtime changes

### Consequences
- ✅ Fast initial render from static files
- ✅ Dynamic customization possible
- ✅ Graceful degradation if API fails
- ⚠️ Two CSS loading phases
- ⚠️ Potential specificity conflicts

---

## ADR-005: Shadow DOM Token Injection

**Status:** Accepted  
**Date:** 2026-04-28  
**Deciders:** Mohamed Elrefae

### Context
Frappe v16+ uses Web Components with Shadow DOM. CSS variables set on `:root` don't penetrate shadow boundaries.

### Decision
Implement **MutationObserver-based Shadow DOM piercing**:
- Watch for new elements with `shadowRoot`
- Inject `:host` style block with CSS variables
- Use `verifyLabCompliance()` for QA verification

### Consequences
- ✅ Shadow components receive theme tokens
- ✅ Runtime DOM changes handled
- ⚠️ Performance cost of MutationObserver
- ⚠️ Doesn't handle closed shadow roots

---

## ADR-006: White-Label Branding Strategy

**Status:** Accepted  
**Date:** 2026-05-01  
**Deciders:** Mohamed Elrefae

### Context
White-label requirements: hide Frappe branding, show client branding, customize login page.

### Decision
**Multi-Layer Branding Removal:**
1. **CSS hiding** (hideFrappeBranding) - immediate visual cleanup
2. **Template overrides** (navbar_brand.html) - structural branding
3. **Hook-based suppression** (ignore_update_popup) - feature disable
4. **Post-migrate cleanup** (whitelabel_patch) - database-level cleanup

### Consequences
- ✅ Comprehensive branding control
- ✅ Update-resistant (re-applies after Frappe updates)
- ⚠️ Fragile - depends on Frappe DOM structure
- ⚠️ Requires maintenance when Frappe updates

---

## ADR-007: Version Query String Strategy

**Status:** Accepted  
**Date:** 2026-05-02  
**Deciders:** Mohamed Elrefae

### Decision
All assets in hooks.py use version query strings (`?v=X`) for cache busting without filename hashing.

**Pattern:**
- Major features: `?v=3` (tokens CSS)
- Minor fixes: `?v=7`, `?v=9` (JS files)
- Components: `?v=4.5` (sub-versioning)

### Consequences
- ✅ Simple cache invalidation
- ✅ No build process required
- ⚠️ Manual version management
- ⚠️ No automatic cache-busting on file change

---

## Rejected Alternatives

### SASS/SCSS Compilation
**Rejected:** Adds build complexity, doesn't solve runtime theming.

### CSS-in-JS
**Rejected:** Incompatible with Frappe's server-rendered architecture.

### Frappe Theme Switcher Override Only
**Rejected:** Doesn't handle white-label requirements (branding removal).

---

*Last Updated: 2026-05-05*
