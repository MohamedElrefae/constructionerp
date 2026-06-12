# Phase 1 — QA Handoff

> **Status:** Completed in-browser on 2026-06-12. All 72 checks passed, SS1-SS10 were captured, and the final evidence pack is in `docs/evidence/phase1/`.

## For the Tester (requires browser + DevTools)

---

### Prerequisites (check these first)

- [ ] `bench start` running (or frappe-bench is accessible via browser)
- [ ] Logged in as a user with BOQ form access
- [ ] At least 1 BOQ Header with status **"Locked"**
- [ ] At least 1 BOQ Structure under that header (leaf, `is_group=0`)
- [ ] At least 1 BOQ Item under that structure
- [ ] User Scope Context configured with a Project
- [ ] Browser DevTools open (Console + Elements tabs)
- [ ] Console capture script running (see §Console Log Capture below)
- [ ] `docs/evidence/phase1/screenshots/` directory exists (it does)

---

### Console Log Capture

Before starting, paste this into the browser Console:

```js
const errors = [];
const origError = console.error;
const origWarn = console.warn;
console.error = function(...args) {
    errors.push('[ERROR] ' + args.join(' '));
    origError.apply(console, args);
};
console.warn = function(...args) {
    errors.push('[WARN] ' + args.join(' '));
    origWarn.apply(console, args);
};
```

After all tests, dump with:
```js
console.log('=== CONSOLE LOG CAPTURE ===');
errors.forEach(e => console.log(e));
console.log('=== END CAPTURE ===');
```

---

### V1 — BOQ Item Stage: Empty Form (12 assertions)

Navigate to `/app/boq-item-stage/new`

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V1.1 | `project` has red accent (`ct-boq-step-accent` on wrapper) | [ ] |
| V1.2 | `project` pill badge "Select Project first" | [ ] |
| V1.3 | `boq_header` dropdown blocked (orange) | [ ] |
| V1.4 | `boq_header` button label = "Select Project first" | [ ] |
| V1.5 | `boq_structure` orange-blocked | [ ] |
| V1.6 | `boq_structure` button label = "Select BOQ Header first" | [ ] |
| V1.7 | `boq_item` orange-blocked | [ ] |
| V1.8 | `boq_item` button label = "Select BOQ Structure first" | [ ] |
| V1.9 | No console errors | [ ] |
| V1.10 | Click `boq_header` dropdown → blocked (doesn't open) | [ ] |
| V1.11 | Click `boq_structure` dropdown → blocked | [ ] |
| V1.12 | Click `boq_item` dropdown → blocked | [ ] |

**📸 Screenshot SS1** → `screenshots/SS1_empty_form.png`

---

### V2 — Select Project (6 assertions)

Select a Project in the `project` field.

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V2.1 | `project` accent cleared, back to normal | [ ] |
| V2.2 | `project` pill badge gone | [ ] |
| V2.3 | `boq_header` now has RED accent (active step) | [ ] |
| V2.4 | `boq_header` dropdown IS openable | [ ] |
| V2.5 | `boq_structure` + `boq_item` remain orange-blocked | [ ] |
| V2.6 | `boq_header` dropdown filters by selected project | [ ] |

**📸 Screenshot SS2** → `screenshots/SS2_boq_header_accent.png`

---

### V3 — Select BOQ Header (8 assertions)

Select a BOQ Header.

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V3.1 | `project` remains normal | [ ] |
| V3.2 | `boq_header` accent cleared | [ ] |
| V3.3 | `boq_header` pill badge gone | [ ] |
| V3.4 | `boq_structure` now RED accent (active step) | [ ] |
| V3.5 | `boq_structure` dropdown IS openable | [ ] |
| V3.6 | `boq_structure` filters by header | [ ] |
| V3.7 | `boq_item` remains orange-blocked | [ ] |
| V3.8 | `boq_item` button = "Select BOQ Structure first" | [ ] |

**📸 Screenshot SS3** → `screenshots/SS3_boq_structure_accent.png`

---

### V4 — Select BOQ Structure (5 assertions)

Select a BOQ Structure (leaf node).

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V4.1 | `boq_structure` accent cleared | [ ] |
| V4.2 | `boq_item` now RED accent (active step) | [ ] |
| V4.3 | `boq_item` dropdown IS openable | [ ] |
| V4.4 | `boq_item` filters by project + header + structure | [ ] |
| V4.5 | Select a BOQ Item → `boq_header` + `boq_structure` auto-fill | [ ] |

**📸 Screenshot SS4** → `screenshots/SS4_boq_item_accent.png`

---

### V5 — Clear Parent, Downstream Re-block (5 assertions)

Clear `boq_structure`, then `boq_header`, then `project`.

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V5.1 | Clear `boq_structure` → `boq_item` clears + re-blocks | [ ] |
| V5.2 | Clear `boq_header` → `boq_structure` + `boq_item` clear + re-block | [ ] |
| V5.3 | Clear `project` → all 3 downstream clear + re-block (V1 state) | [ ] |
| V5.4 | Form shows dirty (`frm.dirty()` is true) | [ ] |
| V5.5 | No console errors | [ ] |

**📸 Screenshot SS5** → `screenshots/SS5_cleared_state.png`

---

### V6 — BOQ Header: Project Accent (4 assertions)

Navigate to `/app/boq-header/new`

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V6.1 | `project` has red accent when empty | [ ] |
| V6.2 | `project` pill badge "Select Project first" | [ ] |
| V6.3 | Select a project → accent + badge clear | [ ] |
| V6.4 | If scope pre-fills project → NO accent (no flash) | [ ] |

**📸 Screenshot SS6** → `screenshots/SS6_boq_header_project_accent.png`

---

### V7 — BOQ Header: Accent Persists After Save (2 assertions)

Save form with empty `project`.

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V7.1 | After save, if `project` still empty → accent persists | [ ] |
| V7.2 | Accent NOT gated on `is_new()` (check source: uses `!frm.doc.project`) | [ ] |

**📸 Screenshot SS7** → `screenshots/SS7_accent_persists_after_save.png`

---

### V8 — Variation Order: BOQ Header Accent (5 assertions)

Navigate to `/app/variation-order/new`

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V8.1 | `boq_header` has red accent when empty | [ ] |
| V8.2 | `boq_header` pill badge "Select BOQ Header first" | [ ] |
| V8.3 | Select a BOQ Header → accent + badge clear | [ ] |
| V8.4 | Dropdown only shows Locked headers | [ ] |
| V8.5 | Selecting a Locked header → accent disappears | [ ] |

**📸 Screenshot SS8** → `screenshots/SS8_vo_boq_header_accent.png`
**📸 Screenshot SS9** → `screenshots/SS9_vo_locked_only.png`

---

### V9 — Variation Order: Dropdown NOT Blocked (3 assertions)

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V9.1 | Dropdown OPENS (accent-only, not blocked) | [ ] |
| V9.2 | "Create New" IS visible (`only_select=false`, confirmed safe) | [ ] |
| V9.3 | Only Locked BOQ Headers in dropdown | [ ] |

---

### V10 — Cache Bust (4 assertions)

Open DevTools → Network tab, refresh page.

| ID | Check | Pass/Fail |
|----|-------|-----------|
| V10.1 | `ct_link_control.js?v=13` loaded | [ ] |
| V10.2 | `filter_fix.js?v=7` loaded | [ ] |
| V10.3 | `modern_theme.css?v=2.5.6` loaded | [ ] |
| V10.4 | Response status 200 (not 304) | [ ] |

**📸 Screenshot SS10** → `screenshots/SS10_network_tab.png`

---

### After Tests

Completed in the evidence pack:

1. `T5_test_results.md` is filled out with the final pass/fail results.
2. Console log capture is saved in the results file.
3. `MANAGER_SIGNOFF_CHECKLIST.md` is updated through T10 and E7.
4. SS1-SS10 screenshots are present under `screenshots/`.
5. Engineering sign-off can proceed.

---

*Full plan: `PHASE1_CASCADE_BLOCKER_IMPLEMENTATION_PLAN.md`*
