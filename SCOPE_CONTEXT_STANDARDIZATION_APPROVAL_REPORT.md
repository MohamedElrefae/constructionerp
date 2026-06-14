# Scope Context Standardization & 403 Elimination

## Manager Approval Report

| | |
|---|---|
| **Prepared for** | Head of Engineering / Engineering Manager |
| **Prepared by** | Construction ERP Engineering Team |
| **Date** | 2026-06-15 |
| **App** | `construction` (Frappe/ERPNext custom app) |
| **Branch** | `feature/vite-ui-v1` |
| **Status** | **Awaiting Approval** |

---

## Decision Summary (One Page)

### What We Are Asking You to Approve

Approval to complete a **2-engineer-day work package** that:
1. Finalizes the Scope Context system so the server is the single source of truth.
2. Fixes the last remaining cause of `403 Forbidden` errors for restricted users in the Construction app.
3. Establishes a repeatable policy so future DocTypes do not reintroduce the same bug.

### The Business Problem

Restricted users (Site Engineers, Accountants) currently see `403 Forbidden` errors in their browser when opening list/tree/form views. These errors occur because Frappe automatically initializes Link controls for any field marked `in_standard_filter: 1`, and these users do not have read permission on the `Project` DocType. This creates a poor user experience, pollutes support channels, and undermines confidence in the permission model.

### The Recommended Decision

**Approve Option 3: Full Standardization & 403 Elimination.**

This is the only option that permanently removes the root cause, locks the single-source-of-truth architecture, and prevents recurrence through a documented policy.

### Resource & Schedule

| Item | Estimate |
|------|----------|
| Engineering effort | **2 person-days** (1 senior backend engineer + 1 frontend engineer, partially parallel) |
| QA effort | **0.5 person-days** |
| Target start date | **TBD upon approval** |
| Target completion date | **2 business days after start** |
| UAT window | **1 business day after completion** |

### Key Risks & Mitigations

| Risk | Owner | Mitigation |
|------|-------|------------|
| Future DocType reintroduces `in_standard_filter: 1` on a scope field | Tech Lead | Add CI check + code-review checklist |
| `bench migrate` fails on a customized site | DevOps / Backend Lead | Validate on staging; inspect `tabDocField` post-migrate |
| Report breaks if a fieldtype is changed | Reporting Team | No fieldtype changes planned; any future change requires report audit |

### Success Metrics

1. **Zero 403 errors** for a restricted user navigating every Construction list, form, and tree view.
2. **All 14 scope-context integration tests pass** and the full app test suite passes.
3. **No direct `localStorage` scope reads** remain in the codebase.
4. **Future DocType checklist** is merged into `AGENTS.md` and enforced in code review.

### Approval Decision

☐ **Approve** — Proceed with Option 3 as described.  
☐ **Approve with changes** — See conditions in the sign-off section.  
☐ **Reject** — See conditions in the sign-off section.  
☐ **Defer** — See conditions in the sign-off section.

---

## 1. Problem Statement

### 1.1 Symptom

Restricted roles in the Construction app see `403 Forbidden` errors in the browser console and network tab when opening standard views. Example affected view: **BOQ Item Stage list**.

### 1.2 Root Cause

Frappe automatically creates a native `ControlLink` for any DocType field that has:

```json
"in_standard_filter": 1,
"fieldtype": "Link",
"options": "Project"
```

During list/tree load, this control immediately calls:

```
/api/method/frappe.desk.search.search_link?doctype=Project
```

Restricted users do not have read/select permission on the generic `Project` DocType, so the server returns `403 Forbidden`. Client-side patches cannot reliably stop this request because Frappe's filter instantiation happens earlier in the lifecycle.

### 1.3 Business Impact

| Impact Area | Effect |
|-------------|--------|
| User experience | Console errors and failed network calls erode trust in the system. |
| Support load | Help-desk tickets from Site Engineers and Accountants. |
| Security posture | Temptation to grant broad Project read permissions, which would break the dynamic scope model. |
| Release velocity | New DocTypes risk shipping with the same defect unless a policy exists. |

---

## 2. Options Considered

### Option 1 — Do Nothing

**Description:** Leave the current code as-is.  
**Pros:** Zero immediate engineering cost.  
**Cons:**
- 403 errors persist for restricted users.
- New DocTypes will likely repeat the same bug.
- Security model is gradually weakened by workarounds.

**Recommendation:** Reject.

### Option 2 — Quick Patch (Grant Permissions or Hide with CSS)

**Description:** Grant restricted roles read/select permission on `Project`/`Company`/`Cost Center`, or rely on CSS / `ct_link_control.js` to hide the offending controls.

**Pros:** Fast to implement.
**Cons:**
- **Violates the security model.** Scope must be enforced dynamically through User Permissions, not through blanket DocType permissions.
- CSS and prototype patches are unreliable because the native control fires its request before our patches run.
- Does not establish a maintainable pattern for future DocTypes.

**Recommendation:** Reject.

### Option 3 — Full Standardization & 403 Elimination (Recommended)

**Description:**
1. Fix the remaining metadata violation (`BOQ Item Stage.project` has `in_standard_filter: 1`).
2. Lock the client-side Scope Context architecture (server = source of truth; `localStorage` = validated cache only).
3. Add a documented policy and CI gate so future DocTypes follow the same rules.

**Pros:**
- Permanently removes the 403 root cause.
- Strengthens the single-source-of-truth architecture.
- Creates a repeatable, enforceable standard.
- Low risk (2 days, well-defined scope).

**Cons:**
- Requires a small metadata change and migration on all sites.
- Requires discipline in future DocType reviews.

**Recommendation:** Approve.

---

## 3. Scope of Work

### 3.1 In Scope

1. Set `"in_standard_filter": 0` on `BOQ Item Stage.project`.
2. Run `bench migrate` on staging and verify `tabDocField` reflects the change.
3. Verify all client-side Scope Context consumers use `window.scopeContext.getValidatedCurrentScope()`.
4. Bump cache-buster versions in `hooks.py` if any JS file is modified.
5. Add the New-DocType Checklist to `AGENTS.md`.
6. Add a CI / code-review gate that fails if a scope-dimension Link field has `in_standard_filter: 1`.
7. Execute automated and manual verification.

### 3.2 Out of Scope

1. Changing existing `Link` fields to `Data` (not required; keeping `Link` with `in_standard_filter: 0` is sufficient).
2. Rewriting the BOQ Structure tree implementation (already fixed).
3. Modifying ERPNext core code.
4. Refactoring reports unless a fieldtype change becomes necessary.

### 3.3 Assumptions

1. The staging site `v16.localhost` accurately represents production metadata.
2. The restricted-user test account (Site Engineer) has no read/select permission on `Project`, `Company`, or `Cost Center`.
3. `bench migrate` can be executed during the scheduled maintenance window.

---

## 4. Technical Architecture (Brief)

The Scope Context system is already implemented. The remaining work is to close the last metadata gap and lock the standard.

```
Server: User Scope Context DocType  →  boot injection  →  client: window.scopeContext
                                                            ↓
                                    UI dropdowns / list filters / form defaults
```

**Rule:** Every JavaScript consumer reads scope through:

```javascript
window.scopeContext.getValidatedCurrentScope()
```

`localStorage` is only a validated cache and cross-tab sync channel; it never overrides boot data.

For full technical details, see **Appendix A**.

---

## 5. Detailed Execution Plan

### Phase 1 — Metadata Fix (0.5 day)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Update `boq_item_stage.json` to set `project.in_standard_filter = 0` | Backend Engineer | Commit with clear message |
| Run `bench migrate` on `v16.localhost` | Backend Engineer | Migration log; `tabDocField` verified |
| Verify no other Construction DocType violates the rule | Backend Engineer | Updated audit table |

### Phase 2 — Client-Side Verification (0.5 day)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Verify `scope_context.js` hydration & validation logic | Frontend Engineer | Signed-off code review |
| Verify consumers use `getValidatedCurrentScope()` | Frontend Engineer | Audit checklist complete |
| Bump `hooks.py` cache busters if JS files change | Frontend Engineer | Updated `hooks.py` |

### Phase 3 — Policy & Process (0.5 day)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Add New-DocType Checklist to `AGENTS.md` | Tech Lead | Updated `AGENTS.md` |
| Add metadata lint check for `in_standard_filter: 1` on scope fields | DevOps / Tech Lead | `.github/workflows/` or pre-commit hook (see script below) |
| Update code-review template | Tech Lead | PR template updated |

**Metadata lint script (to be added to CI):**

```python
# scripts/lint_scope_metadata.py
import json, os, sys

BASE = "construction/construction/doctype"
SCOPE_FIELDS = {"project", "company", "cost_center", "department", "branch"}
EXIT_CODE = 0

for dt in sorted(os.listdir(BASE)):
    path = os.path.join(BASE, dt, f"{dt}.json")
    if not os.path.exists(path):
        continue
    with open(path) as f:
        doc = json.load(f)
    for field in doc.get("fields", []):
        if field.get("fieldname") in SCOPE_FIELDS and field.get("in_standard_filter"):
            print(f"FAIL: {dt}.json field '{field['fieldname']}' has in_standard_filter=1")
            EXIT_CODE = 1

sys.exit(EXIT_CODE)
```

This script parses each DocType JSON, checks only scope-dimension fields, and fails the build if any of them is exposed as a standard filter.

### Phase 4 — Testing & Validation (0.5 day)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Run `construction.tests.test_scope_context` | QA | 14/14 pass |
| Run full app test suite | QA | All pass |
| Manual restricted-user test across list/form/tree views | QA | Signed test log |
| Cross-browser check (Chrome, Edge, Firefox) | QA | Signed test log |

---

## 6. RACI Matrix

| Activity | Head of Engineering | Tech Lead | Backend Engineer | Frontend Engineer | QA | DevOps |
|----------|:-------------------:|:---------:|:----------------:|:-----------------:|:--:|:------:|
| Approve plan | A | R | C | C | C | I |
| Metadata change | I | A | R | C | I | I |
| Client verification | I | A | C | R | C | I |
| Policy / CI gate | A | R | C | C | I | R |
| Test execution | I | A | C | C | R | I |
| Staging deployment | I | A | C | C | R | R |
| Production deployment | A | R | C | C | R | R |

**Legend:** R = Responsible, A = Accountable, C = Consulted, I = Informed

---

## 7. Timeline

Assuming approval on **Day 0**:

| Day | Phase | Key Milestone |
|-----|-------|---------------|
| Day 0 | Approval | Manager sign-off received |
| Day 1 | Phase 1 + Phase 2 | Metadata fixed; migration verified; client code verified |
| Day 2 | Phase 3 + Phase 4 | Policy merged; CI gate active; tests pass |
| Day 3 | UAT | Restricted-user smoke test signed off |
| Day 4 | Deployment | Deployed to production during maintenance window |

---

## 8. Risk Matrix

| Risk | Likelihood | Impact | Risk Score | Owner | Mitigation / Contingency |
|------|:----------:|:------:|:----------:|-------|--------------------------|
| Future DocType reintroduces `in_standard_filter: 1` | Medium | High | **High** | Tech Lead | CI gate + mandatory checklist in PR template; code-review training |
| `bench migrate` does not reflect the change on a customized site | Low | High | Medium | Backend Lead | Validate on staging; inspect `tabDocField`; rollback plan ready |
| Fieldtype change breaks a custom report | Low | High | Medium | Reporting Team | No fieldtype changes planned; future changes require report audit |
| Client cache prevents immediate fix after deployment | Medium | Medium | Medium | Frontend Engineer | Bump all affected `?v=XX` cache busters; advise users to hard-refresh |
| Frappe upgrade changes filter lifecycle | Low | Medium | Low | Frontend Engineer | Keep patch minimal; add version-compat note to `AGENTS.md` |

**Risk scoring:** Low=1, Medium=2, High=3. Score = Likelihood × Impact.

---

## 9. Rollback Plan

If a critical issue is discovered after deployment:

1. **Immediate (0–30 min):** Revert the single-line JSON change in `boq_item_stage.json` and rerun `bench migrate`.
2. **Short-term (30 min–2 h):** If the issue is in client code, revert the relevant JS file changes and bump cache busters to `v=previous+1`.
3. **Communication:** Notify affected users via the `#construction-erp` channel and create a post-mortem ticket within 24 hours.
4. **Recovery:** Fix the root cause in a follow-up branch and redeploy through the normal review process.

---

## 10. Success Metrics (SMART)

| # | Metric | Target | Measurement Method | Owner |
|---|--------|--------|--------------------|-------|
| 1 | 403 errors for restricted users | 0 | Browser network tab audit on all Construction list/form/tree views | QA |
| 2 | Scope context integration tests | 14/14 pass | `bench --site v16.localhost run-tests --module construction.tests.test_scope_context` | QA |
| 3 | Full app test suite | 0 regressions | `bench --site v16.localhost run-tests --app construction` | QA |
| 4 | Direct `localStorage` scope reads | 0 | `grep -R "localStorage.getItem.*scope_context"` | Tech Lead |
| 5 | Policy adherence | 100% of new DocTypes reviewed | PR checklist + CI gate | Tech Lead |

---

## 11. Post-Deployment Monitoring

| Activity | Frequency | Owner | Trigger for Escalation |
|----------|-----------|-------|------------------------|
| Check server error logs for 403s | Daily for 1 week | DevOps | Any 403 from `search_link` on `Project`/`Company`/`Cost Center` |
| Review support tickets mentioning "permission" or "403" | Daily for 1 week | Support Lead | Ticket volume > 0 related to this change |
| Verify scope context diagnostics still function | Once | QA | Diagnostic log missing or incorrect |
| Validate cache busters cleared old assets | Once | Frontend Engineer | Reports of stale UI |

---

## 12. Communication Plan

| Audience | Message | Channel | Timing |
|----------|---------|---------|--------|
| Engineering team | Approval received; branch and task assignments | Slack / Email | Day 0 |
| QA team | Test plan and restricted-user credentials | Slack / Ticket | Day 1 |
| End users (restricted roles) | Brief notice that 403 errors are resolved; no action needed | In-app banner / Email | Day 4 (after production deploy) |
| Support team | Summary of change and expected behavior | Slack / Wiki | Day 4 |
| Management | Go-live confirmation and metrics | Email | Day 5 |

---

## 13. Approval Checklist for Manager

Before signing, please confirm:

- [ ] The problem statement and business impact are understood.
- [ ] Option 3 is accepted; Options 1 and 2 are rejected.
- [ ] Resource estimate (2 engineering days + 0.5 QA day) is acceptable.
- [ ] Timeline (2 business days + 1 UAT day) is acceptable.
- [ ] Risks and mitigations are understood.
- [ ] Rollback plan is acceptable.
- [ ] Success metrics are clear and measurable.
- [ ] RACI roles are assigned.

---

## 14. Sign-Off

**Suggested approval language for "Approve with conditions":**

> Proceed once the following conditions are met:
> 1. `BOQ Item Stage.project` metadata is updated to `"in_standard_filter": 0` and migrated.
> 2. `boq_item.js` is aligned to use `getValidatedCurrentScope()` (already done during this audit).
> 3. Migration is verified on `v16.localhost` by inspecting `tabDocField`.
> 4. The metadata lint script is added to CI / pre-commit.

| Role | Name | Decision | Date | Conditions / Notes |
|------|------|:--------:|:----:|--------------------|
| Head of Engineering / Engineering Manager | | ☐ Approve<br>☐ Approve with changes<br>☐ Reject<br>☐ Defer | | |
| Tech Lead / Architect | | ☐ Approve<br>☐ Approve with changes<br>☐ Reject<br>☐ Defer | | |
| QA Lead | | ☐ Approve<br>☐ Approve with changes<br>☐ Reject<br>☐ Defer | | |

**Conditions / Notes from Approver:**

________________________________________________________________________________

________________________________________________________________________________

________________________________________________________________________________

---

## Appendix A — Technical Background

### A.1 Why `in_standard_filter: 1` Causes 403s

When a DocType field is marked `in_standard_filter: 1` and `fieldtype: "Link"`, Frappe renders it as a standard filter on list/tree views. During initialization, the native `ControlLink` calls `frappe.desk.search.search_link` for the target DocType. If the user lacks read/select permission on that DocType, the server returns `403 Forbidden`. Client-side patches cannot intercept this request because filter creation happens before our scripts run.

### A.2 Current Audit Results

A live audit of the `feature/vite-ui-v1` branch found:

| File | Status |
|------|--------|
| `construction/public/js/scope_context.js` | ✅ Implemented correctly |
| `construction/api/scope_context_api.py` | ✅ Sentinel pattern supports explicit `None` clears |
| `construction/boot.py` | ✅ Injects scope context into boot |
| `construction/tests/test_scope_context.py` | ✅ 14 tests |
| All known scope consumers | ✅ Use `getValidatedCurrentScope()` (including `boq_item.js`, aligned during this audit) |
| `BOQ Item Stage.project` | ⚠️ `in_standard_filter: 1` — must be fixed |

### A.3 New-DocType Checklist (to be added to `AGENTS.md`)

For every new transactional DocType:

1. Review `project`, `company`, `cost_center`, `department` fields.
2. If display-only / derived: `fieldtype: "Link"`, `"read_only": 1`, `"in_standard_filter": 0`.
3. If user-selectable: `"in_standard_filter": 0`; drive selection via Scope Context or a scoped whitelisted API.
4. Never call `frappe.db.get_value("Project", ...)` from client scripts.
5. Bump `hooks.py` cache busters for any modified JS files.

### A.4 Audit Commands

```bash
# Find all scope-dimension fields in Construction DocTypes
python3 - <<'PY'
import json, os
base = '/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype'
fields = ['project','company','cost_center','department','branch']
for dt in sorted(os.listdir(base)):
    path = os.path.join(base, dt, f'{dt}.json')
    if os.path.exists(path):
        data = json.load(open(path))
        for f in data.get('fields', []):
            if f.get('fieldname') in fields:
                print(f"{dt} | {f.get('fieldname')} | in_standard_filter={f.get('in_standard_filter')} | fieldtype={f.get('fieldtype')} | read_only={f.get('read_only')}")
PY

# Find direct localStorage scope_context reads
bash -c 'grep -R "localStorage.getItem.*scope_context" apps/construction/construction/public/js/ apps/construction/construction/construction/doctype/ || true'

# Find direct Project/Company db.get_value calls in client scripts
bash -c 'grep -R "frappe.db.get_value.*Project" apps/construction/construction/public/js/ apps/construction/construction/construction/doctype/ || true'
bash -c 'grep -R "frappe.db.get_value.*Company" apps/construction/construction/public/js/ apps/construction/construction/construction/doctype/ || true'
```

### A.5 Relevant Files

| Category | Path |
|----------|------|
| Scope Context core | `construction/public/js/scope_context.js` |
| Scope UI | `construction/public/js/scope_context_ui.js` |
| Form defaults | `construction/public/js/scope_context_form_defaults.js` |
| List filters | `construction/public/js/scope_context_list_filter.js` |
| BOQ filters | `construction/public/js/boq_filters.js` |
| Link control override | `construction/public/js/overrides/ct_link_control.js` |
| BOQ Structure tree | `construction/construction/doctype/boq_structure/boq_structure_tree.js` |
| Server API | `construction/api/scope_context_api.py` |
| Boot injection | `construction/boot.py` |
| Metadata registration | `construction/hooks.py` |
| Tests | `construction/tests/test_scope_context.py` |
| DocType JSONs | `construction/construction/doctype/*/*.json` |
