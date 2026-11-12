# MEMORANDUM — Form Layout Engine (VFC): Risk Assessment & Recommendation

| | |
|---|---|
| **To** | General Manager |
| **From** | Head of Engineering |
| **Date** | 11 November 2026 |
| **Subject** | VFC form-layout feature — fix, retire, or gate? Recommendation for final approval |
| **Classification** | Internal — decision required |
| **Supporting docs** | `docs/ai/VFC_AND_UI_OVERRIDE_AUDIT_2026-11-11.md` (engineering audit, 22 findings)<br>`docs/ai/VFC_DECISION_KEEP_FIX_RETIRE_2026-11-11.md` (decision brief) |

---

## 1. Executive summary

The Form Layout Engine ("VFC") is a **partially built, customer-distributable feature** that is
currently attached to **every form in the ERP** but actively used on **8 of 492 forms**, and in
whose entire history **one user has hidden one field**.

Engineering's recommendation is **not** to rewrite it, **not** to delete it wholesale, and **not**
to keep it as-is. It is:

> **Gate it off by default, fix the three live defects, keep the backend, and retire the two
> subsystems nobody uses.** This converts an ERP-wide upgrade liability into a per-user preference,
> and it costs roughly one engineer-week to de-risk.

**Decision requested:** approve Phase 0 and Phase 1 (see §7). Both are low-risk, reversible, and
can ship in the next release cycle.

---

## 2. What I reviewed, and what I corrected

I did not forward the engineering audit unchanged. Three of its claims needed correction before
this memo could be relied on. I am flagging these because they materially change the risk picture
and you should not be quoted a stronger case than the evidence supports.

| Audit claim | My finding | Impact |
|---|---|---|
| "The engine can **hide** a field the user is allowed to see" (F4) | **Partly wrong.** The engine can make a *permission-restricted* field **visible**. The reverse does not happen. The value itself is **not leaked** — the server strips it (`apply_fieldlevel_read_permissions`, `document.py:959`). What leaks is the field's **existence and label**. | Downgraded from *data-exposure* to **UI permission regression**. Still a defect; not a security incident. |
| "`visible:false` fields are rendered twice" (F5) | **Wrong.** The engine skips the field and returns; it is not double-rendered, and the audit's claimed retry storm does **not** occur — the guard at `vfc_layout_engine.js:684` skips those fields. | Downgraded. The real F5 issue is narrower: `frm.toggle_display` is called and **never undone**, so a field hidden by a profile stays hidden for that document's lifetime. |
| "The Section editor's data-loss bug" (F13) | **Correct, and stronger than stated.** I reproduced it in the live database. See §3.2. | **Upgraded.** This is the most serious finding after the live-defect trio. |
| "202 test rows in production" (F7) | **Correct and verified** (202 rows). But the cause matters: the **test suite writes to the live site database**. That is a **CI/release-governance defect**, not just a VFC defect, and it needs its own workstream. | **Upgraded**, and reclassified as a release-engineering issue. |

**One audit claim I could not verify at all:** the tabbed-doctype misplacement (F3). It is a
code-path finding only. **I recommend we do not spend money "fixing" it until we have a browser
reproduction**, because a fix against an unverified mechanism risks breaking the 4 flat forms that
actually work today. This is now the first task in Phase 0.

---

## 3. The situation, in business terms

### 3.1 Exposure is 60× the usage

| Metric | Value |
|---|---|
| Non-child DocTypes on the site | **492** |
| DocTypes with a real layout profile | **8** |
| Forms that currently run the VFC engine and show a "Form Config" button | **every one of the 492** |
| Actual recorded user customisation in the site's whole history | **one field, by one user** |

There is **no site setting, no feature flag, and no per-doctype opt-out** anywhere in the code.
The feature is either "on for everyone" or "off for everyone". There is no middle position, which
is why an ERPNext UI update is a company-wide event rather than a routine upgrade.

### 3.2 The most serious engineering finding: the editor destroys the user's work

The "Sections" tab of the panel merges the saved layout with the doctype's native sections. The
merge routine **removes from the user's custom sections any field that also appears in a native
section**, then re-adds the native section.

I verified the result against the live database:

```
BOQ Item profile:
   sec_header_link  (user section)  →  0 fields
   sec_owner_refs   (user section)  →  0 fields
   sec_classification (user section) →  0 fields
   sec_quantities   (user section)  →  0 fields
   sec_pricing      (user section)  →  0 fields
   sb_identity      (native)        →  9 fields
   sb_quantity      (native)        →  8 fields
   sb_cost_estimation (native)      →  8 fields
   ...                                        ← every field in a native section
```

**Every field the user placed is gone; everything lives in a native section.** A user who spends an
hour arranging a BOQ form will find their work destroyed the next time they open the panel and save.
This alone is a reason to retire that subsystem — it has cost us credibility with anyone who tried
it.

### 3.3 It ships to customers — and the customer copy is already out of date

VFC is **inside the curated customer distribution** (`customer-dist/`), so it is customer-facing
code, not internal-only. Two consequences:

1. The permission-regression finding (§2, F4) is therefore a **customer-facing** concern, not just
   an internal one.
2. The customer copy **does not match the repository**:

   | File | Customer-dist date | Repo date | Drift |
   |---|---|---|---|
   | `vite_layout_controls.js` | 14 Oct 2026 | 23 Oct 2026 | **243 changed lines** |
   | `modern_theme.css` | 07 Oct 2026 | 09 Nov 2026 | **436 changed lines** |

   In other words: **what we have tested is not what ships**, and vice versa. This is a separate
   release-governance issue and it affects the theme work as much as VFC. I recommend it be raised
   as its own item rather than buried in this one.

---

## 4. Risk assessment

| # | Risk | Likelihood | Impact | Owner | Mitigation in plan |
|---|---|---|---|---|---|
| **R1** | 202 `_Test_*` profile rows are live in production and are served to real users by the resolver | **Certain** (verified) | Medium — a test profile can shadow a real layout for a doctype | Engineering | Phase 0.1 |
| **R2** | Test suite writes to the production database, so any future test run re-pollutes it | **Certain** (structural) | Medium — repeat of R1, plus unreliable tests | Engineering / Release | Phase 0.1 + new CI workstream |
| **R3** | Permission-regression: a `permlevel` field becomes visible to an under-privileged user (label + empty/masked control) | **Low today, high after any expansion** — unreachable only because the 4 seeded BOQ doctypes have no `permlevel` fields. Budget and Project profiles already exist and are ERPNext-core. | Medium — policy violation, not data loss | Engineering | Phase 0.2 |
| **R4** | Next Frappe/ERPNext UI update silently breaks form rendering for **all** users | **High over a 12-month horizon** — the engine re-parents Frappe's own DOM nodes and patches a vendor class; none of those internals are public API | **High** — site-wide form breakage | Engineering | Phase 1 (gate off by default) |
| **R5** | "Revert to Default / Native" reports success while doing nothing | Certain (verified) | Low — user confusion, lost trust | Engineering | Phase 0.3 |
| **R6** | Customer distribution is stale relative to the repository (VFC **and** theme) | Certain (verified) | Medium — untested code ships; tested code doesn't | Release / Engineering | New workstream (§7.4) |

**What is NOT at risk:** the theming/UI-override layer. It is CSS-only (126 selectors against Frappe
class names, **zero** references to Frappe JS internals) and is the system that delivers your
branding, Arabic RTL and dark mode. It is low-maintenance and should be explicitly excluded from any
VFC decision. I have seen this conflated before; it is a different system sharing a folder.

---

## 5. Options considered

| | Option A — Rebuild the frontend properly | Option B — Delete the feature | **Option C — Gate off + fix + freeze (recommended)** |
|---|---|---|---|
| **Cost** | 3–6 engineer-weeks, then recurring | ~1 week | **~1 engineer-week to de-risk** |
| **Risk** | High — every change touches the code where the permission defect lives | Medium — collateral damage to theming if scoped badly; loses the good backend | **Low — the risky code stops running for everyone by default** |
| **User value today** | Builds a feature with **no demonstrated demand** | Removes a feature with no demonstrated demand | **Preserves the option; costs nothing while unused** |
| **Upgrade exposure** | **Unchanged** — still coupled to Frappe internals | Zero | **Effectively zero** |
| **Decision quality** | Bet on future demand | Bet against all demand | **Defers the bet until there is data** |

**Why not A:** the rewrite inherits the same fragility, because *any* frontend that moves Frappe's DOM
nodes is coupled to those internals. It changes *when* we pay, not *whether*.

**Why not B (wholesale):** two things would be destroyed that should not be — the theming system
(separate, valuable, low-maintenance) and the VFC backend, which is the cleanest code in the feature
and the enabler for the opt-in path.

**Why C:** it is the only option that removes the ERP-upgrade pressure immediately, at low cost, and
without betting on demand. It also produces the information needed for a *correct* long-term decision
in one quarter.

---

## 6. Recommendation

**Approve Option C.** Specifically:

### Phase 0 — Stop the bleeding (target: week of 16 Nov 2026)

| # | Action | Why it cannot wait |
|---|---|---|
| 0.1 | Delete the 202 `_Test_*` rows from every site; make the VFC test suite run against a **disposable** database; block `_Test_`-prefixed names at the API | Live production data defect; will recur on the next test run |
| 0.2 | Stop stripping Frappe's `hide-control` class; skip fields whose display status is "None" | Permission regression; currently latent but one ERPNext doctype away from live |
| 0.3 | Make "Revert to Default / Native" truthful and functional | User-facing false-success message |
| 0.4 | **Browser-verify F3 and F4** (the two unverified claims) before any further work | We must not spend money fixing a mechanism we have not reproduced |

### Phase 1 — Gate it off by default (target: week of 23 Nov 2026)

| # | Action | Effect |
|---|---|---|
| 1.1 | Add a site setting **`enable_form_config`, default OFF** | With it off, **no** VFC code runs and **no** form is affected. Blast radius goes from 492 forms to zero. |
| 1.2 | Skip button injection and engine attachment when the setting is off | The upgrade pressure described in §4/R4 disappears |

**After Phase 1, this memo's primary concern is resolved.** Everything below is optional work on an
opt-in feature, at our own pace.

### Phase 2 — Make it per-user and honest (next release)

| # | Action |
|---|---|
| 2.1 | Per-user, per-doctype opt-in ("enable Form Config on this form") |
| 2.2 | Move column density out of browser `localStorage` into server-side user settings |
| 2.3 | Add a `__native__` personal-profile sentinel so "revert" truly restores native layout |
| 2.4 | Key the client profile cache by user |

### Phase 3 — Retire the two dead subsystems (deliberately)

| # | Action | Rationale |
|---|---|---|
| 3.1 | **Retire the Sections editor** — remove the tab, drag/drop, the merge routine and the `fld.visible` handling (~1,200 lines) | Unused; has the data-loss defect (§3.2); highest coupling to Frappe internals |
| 3.2 | **Retire tabbed-doctype support** until Frappe's tab DOM is stable | Unverified mechanism; currently misplaces sections |
| 3.3 | Delete orphaned `vfc_native_collapsed_sections` data | Already-dead feature's residue |

### Phase 4 — Decide on evidence (quarterly review)

With the feature gated, usage becomes measurable and honest. If users adopt it, consider rebuilding the
section editor **on Frappe's own `DocType Layout`** (per-doctype, maintained by Frappe) rather than on
a parallel DOM-surgery engine. If they do not, delete the feature cleanly — the backend included —
having spent nothing maintaining it.

---

## 7. Decisions I need from you

| # | Decision | Options | My recommendation |
|---|---|---|---|
| **D1** | Approve Phase 0 (four fixes) | Approve / defer / reject | **Approve** — these are live defects, independent of the feature's future |
| **D2** | Approve Phase 1 (site setting, default **OFF**) | Approve / default ON / reject | **Approve with default OFF** |
| **D3** | Authorise a production database cleanup (deleting 202 test rows) | Approve / require customer notice / reject | **Approve** — these are our own test artifacts, not customer data. I will take a backup first and give you the exact row list. |
| **D4** | Approve Phase 3 (retire Sections editor + tab support) | Approve / defer to Phase 4 / reject | **Approve** — unused and actively harmful |
| **D5** | Raise the stale customer distribution (§3.3) as a separate item | Approve / fold into this work / reject | **Approve as a separate item** — it affects theming too and needs its own owner |
| **D6** | Raise the "tests write to production" finding as a separate governance item | Approve / fold into 0.1 / reject | **Approve as a separate item** — it is a release-process defect, not a VFC defect |

---

## 8. If we do nothing

| Timeline | Consequence |
|---|---|
| **Now** | 202 test rows remain live and are returned to users on the affected doctypes |
| **Next test run** | The database is re-polluted |
| **Next Frappe/ERPNext UI update** | Possible site-wide form breakage. Because the engine touches every form, this is not scoped to the 8 used doctypes. |
| **Next time someone tries the Sections tab** | Their arrangement is destroyed and saved in destroyed form |
| **Next customer release** | The stale distribution ships VFC code that differs from what we have tested, and a permission defect ships if any customer doctype uses `permlevel` fields |

**Cost of Phase 0 + Phase 1:** approximately **one engineer-week**.
**Cost of doing nothing:** unbounded, and it is the one scenario in which this memo's subject becomes a
production incident rather than a maintenance decision.

---

## 9. Resource requirement

| Phase | Effort | Who | Notes |
|---|---|---|---|
| 0 | ~3 engineer-days | 1 engineer | Includes the browser verification (0.4) |
| 1 | ~2 engineer-days | 1 engineer | Site setting + two early-exit guards |
| 2 | ~4 engineer-days | 1 engineer | Persistence consolidation |
| 3 | ~3 engineer-days | 1 engineer | Mostly deletion |
| 4 | — | Owner decision | No engineering cost |

No new infrastructure, no new dependencies, no customer-facing migration. Phase 3 is net **code
removal**.

---

## 10. Closing

The honest position is that this feature was built with a good backend and an optimistic frontend,
and the frontend was never finished to the standard the backend deserved. The right response is not
to throw away the good half, nor to keep paying for the fragile half. It is to **switch the fragile
half off, fix what is actively broken, and let the people who actually use it decide whether it is
worth finishing.**

I am confident in the technical diagnosis and in the Phase 0/1 plan. I want to be equally honest
about what I am **not** confident about: whether the section editor is worth rebuilding at all. That
question should not be answered by engineering preference. It should be answered by the quarterly
usage review in Phase 4 — after the feature is safe to leave switched on.

I recommend approval of **D1, D2, D3, D4, D5 and D6**.

---

## Appendix A — Evidence

Reproduce any figure in this memo with the commands in
`docs/ai/VFC_DECISION_KEEP_FIX_RETIRE_2026-11-11.md` §9. Key ones:

```bash
# Exposure vs usage
mysql -u root -proot -h localhost -e "
  SELECT COUNT(*) non_child_doctypes FROM \`_6d52b48c328b294e\`.\`tabDocType\` WHERE istable=0;   -- 492
  SELECT COUNT(DISTINCT reference_doctype) doctypes_with_profile
    FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\` WHERE profile_name NOT LIKE '\_Test\_%'; -- 8
  SELECT SUM(for_user IS NOT NULL) personal, SUM(for_role IS NOT NULL) role_rows
    FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`;                                              -- 0, 0"

# Actual customisation in the site's history
mysql -u root -proot -h localhost -e "
  SELECT JSON_EXTRACT(data,'\$.\"vfc_hidden_fields\"') hf,
         JSON_EXTRACT(data,'\$.\"vfc_preset\"') preset, COUNT(*)
    FROM \`_6d52b48c328b294e\`.\`__UserSettings\` WHERE data LIKE '%vfc%'
    GROUP BY hf, preset;"
#   →  vfc_hidden_fields = []  (×2),  ["description"] (×1),  preset = "Default" (×2)

# The Section editor's destruction of user work (live data)
mysql -u root -proot -h localhost -N -e "
  SELECT sections_json FROM \`_6d52b48c328b294e\`.\`tabForm Layout Profile\`
   WHERE name='BOQ Item-Default';" | python3 -m json.tool | head -40

# No gate exists anywhere
grep -rn "enable_vfc\|vfc_enabled\|allow_vfc" apps/construction/construction/ \
  --include=*.py --include=*.js | grep -v enable_vfc_debug_logging
#   → no matches

# The customer distribution is stale
diff apps/construction/construction/public/js/vite_layout_controls.js \
     customer-dist/construction/public/js/vite_layout_controls.js | grep -c "^[<>]"   # 243
diff apps/construction/construction/public/css/modern_theme.css \
     customer-dist/construction/public/css/modern_theme.css        | grep -c "^[<>]"   # 436

# The permission defect (F4)
grep -n "hide-control" apps/construction/construction/public/js/vfc_layout_engine.js
grep -n "hide-control" apps/frappe/frappe/public/js/frappe/form/controls/base_control.js

# validate_layout is implemented, tested, and never called by the UI
grep -rn "validate_layout" apps/construction/construction/public/js/   # no matches
```

---

*Prepared by the Head of Engineering for the General Manager's decision. Phase 0 and Phase 1 are
safe to begin immediately upon approval; Phase 2 onwards changes behaviour and should follow the
owner's confirmation of scope.*
