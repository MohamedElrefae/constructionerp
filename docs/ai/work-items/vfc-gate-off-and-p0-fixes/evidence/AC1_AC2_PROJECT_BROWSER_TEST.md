# AC-1 / AC-2 Gate Test Evidence — Project Browser Test

| | |
|---|---|
| **Work item** | `vfc-gate-off-and-p0-fixes` |
| **Executed** | 2026-11-12 |
| **Site** | `v16.localhost` (DB `_6d52b48c328b294e`) |
| **Document** | `PROJ-0002` |
| **Actor** | Throwaway user, role `Projects User` (non-admin, ordinary allowed user per Standard §10) |
| **Verdict** | **P0-2 REPRODUCED — CONFIRMED defect. F3 NOT reproduced — tabs render correctly.** |

---

## 1. Environment baseline

| Check | Result |
|---|---|
| `schema_drift_checker.py` | PASS, exit 0 |
| `ai_context_check.py` | PASS, 11/11, exit 0 |
| HEAD | `9796c5f27bc899867699b81d3e89d6dd5c62710f` (branch `develop`, 0/0 vs origin) |
| Site HTTP | 200 |
| Redis 13000 / 11000 | PONG / PONG |
| MariaDB | running |

---

## 2. Finding A — the permlevel half of P0-2 is structurally unreachable

### A.1 `Desk User` is granted to every System User programmatically

`frappe/permissions.py:542-568`:

```python
roles += [ALL_USER_ROLE, GUEST_ROLE]
if is_system_user(user):
    roles.append(SYSTEM_USER_ROLE)      # SYSTEM_USER_ROLE = "Desk User"
```

`frappe/permissions.py:33-40`:

```python
GUEST_ROLE = "Guest"
ALL_USER_ROLE = "All"
SYSTEM_USER_ROLE = "Desk User"
AUTOMATIC_ROLES = (GUEST_ROLE, ALL_USER_ROLE, SYSTEM_USER_ROLE, ADMIN_ROLE)
```

`Desk User` is in `AUTOMATIC_ROLES`, so it is **filtered out of the stored query**
(`table.role.notin(AUTOMATIC_ROLES)`) and re-added for every System User.

**Consequence:** it never appears in `tabHas Role`. Verified:

```sql
SELECT parent, role FROM tabHas Role WHERE parent = 'vfc.p02.test@example.com';
-- -> only: Projects User
```

Yet `frappe.get_roles()` returned `['Projects User', 'Desk User', 'All', 'Guest']`.

### A.2 ERPNext core grants `Desk User` permlevel-1 read on Project

`apps/erpnext/erpnext/projects/doctype/project/project.json` permissions:

| role | permlevel | read |
|---|---|---|
| Projects Manager | 1 | 1 |
| **Desk User** | **1** | **1** |
| Projects User | 0 | 1 |

### A.3 Full matrix across all VFC-managed doctypes

```
VFC-managed doctypes (9): BOQ Header, BOQ Item, BOQ Item Stage, BOQ Structure,
                          Budget, Project, Task, User Scope Context, Variation Order

Auto-held by EVERY System User: ['Administrator', 'All', 'Desk User', 'Guest']

DOCTYPE               FIELD                PL   ROLES WITH READ=1        VERDICT
BOQ Header            (none)                -   -                        no permlevel fields
BOQ Item              (none)                -   -                        no permlevel fields
BOQ Item Stage        (none)                -   -                        no permlevel fields
BOQ Structure         (none)                -   -                        no permlevel fields
Budget                (none)                -   -                        no permlevel fields
Project               users,copied_from      1   Projects Manager,Desk User  UNREACHABLE - auto-held role ['Desk User']
Task                  (none)                -   -                        no permlevel fields
User Scope Context    (none)                -   -                        no permlevel fields
Variation Order       (none)                -   -                        no permlevel fields

REACHABLE permlevel gates: 0
```

**Only `Project` has permlevel fields, and its gate is auto-satisfied for any user
who can open the Desk at all.** The permlevel half of P0-2 cannot be triggered by
any user on this site — not even a purpose-built one.

### A.4 The throwaway user proved it

Created `vfc.p02.test@example.com` with role `Projects User` only, intending to sit
in the gap. Result:

```
has 'Projects User' : True
has 'Desk User'     : True   <-- auto-granted, no Has Role row
permlevel read access: [0, 1]
PERMLEVEL-1 READABLE : True  <-- gap does not exist
```

**Conclusion: the permlevel case is UNREACHABLE, not merely latent.**

---

## 3. Finding B — the `hide_empty_read_only_fields` half IS reproducible

### B.1 The mechanism

`frappe/public/js/frappe/form/controls/base_control.js:121-134`:

```js
// hide if no value
if (
    this.doctype && status === "Read" && !this.only_input &&
    is_null(value) &&
    frappe.defaults.is_enabled("hide_empty_read_only_fields") &&
    ![...].includes(this.df.fieldtype)
) {
    status = "None";
}
```

`base_control.js:138-143`:

```js
refresh() {
    this.disp_status = this.get_status();
    this.$wrapper &&
        this.$wrapper.toggleClass("hide-control", this.disp_status == "None") && ...
}
```

**The class is toggled on the wrapper. `df.hidden` is never set.**

VFC's skip-guard (`vfc_layout_engine.js:402-413`) tests only
`df.hidden || df.invisible || df.hidden_due_to_dependency` — **none of which is set**,
so the field is not skipped, is moved into a VFC cell, and
`_restoreVisibleFieldWrapper` (`vfc_layout_engine.js:853-879`) strips the class.

### B.2 How the setting reaches the client

```
System Settings.on_update()  ->  set_defaults()  ->  frappe.db.set_default(fieldname, value)
                                                       -> tabDefaultValue (parent='__default')
boot.py:49  bootinfo.sysdefaults = frappe.defaults.get_defaults()   # reads tabDefaultValue
desk.js:375 frappe.sys_defaults = frappe.boot.sysdefaults
sys_defaults.js:17  is_enabled(key) -> cint(get_global_default(key)) === 1
```

**Important operational note:** writing the `System Settings` singles value directly
with `frappe.db.set_value` does **not** reach the client — it bypasses `on_update()`,
so no `tabDefaultValue` row is created and `is_enabled()` keeps returning `false`.
This is exactly the direct-setter-bypasses-hooks hazard in Standard §7.

### B.3 Site state before the test

| Key | Original value |
|---|---|
| `tabSingles.hide_empty_read_only_fields` | `0` (JSON default is `"1"`) |
| `tabDefaultValue` row for that key | **absent** |
| client `frappe.defaults.is_enabled(...)` | `false` |

So the feature was **off** on this site — which is why no exposure was visible at first.

### B.4 At-risk set (read_only + no default + assigned in a VFC profile)

| Profile | At-risk fields |
|---|---|
| **Project-Default** | `actual_start_date`, `actual_time`, `actual_end_date`, `total_costing_amount`, `total_purchase_cost`, `total_sales_amount`, `total_billable_amount`, `total_billed_amount`, `total_consumed_material_cost`, `gross_margin`, `per_gross_margin` |
| Budget-Default | `amended_from`, `budget_distribution_total`, `revision_of` |
| Variation Order-Default | `project`, `vo_number`, `engineer_approval_date`, `client_approval_date`, `total_contract_delta` |
| BOQ Item-Default | 16 fields |
| Task-Default | *(profile does not exist)* |
| User Scope Context-Default | `last_active_at` |

---

## 4. The A/B experiment (decisive)

**Control:** setting enabled (`is_enabled` → `true`, confirmed in-page), same site,
same user, same document `PROJ-0002`. **Only variable: the VFC profile enabled flag.**

### VFC ON (profile `enabled=1`)

```
is_enabled("hide_empty_read_only_fields") : true
hide_control_count     : 18
vfc_managed_count      : 32
managed_with_hidecontrol: 0        <-- no VFC-managed field retains the class
```

| field | hide-control | display | vfc_managed | height |
|---|---|---|---|---|
| `actual_start_date` | **false** | **block** | `1` | **23** |
| `actual_end_date` | **false** | **block** | `1` | **23** |
| `expected_start_date` | false | block | `1` | 56 |
| `total_costing_amount` | false | block | `1` | 0 |
| `gross_margin` | false | block | `1` | 0 |

Control group — **not** VFC-managed, `hide-control=true`, `display:none`, height 0:
`__newname`, `naming_series`, `project_name_ar_norm`, `holiday_list`, `frequency`,
`from_time`, `to_time`, `first_email`, `second_email`, `daily_time_to_send`, …
(**16 fields**)

### VFC OFF (profile `enabled=0`)

```
hide_control_count     : 22        (+4)
vfc_managed_count      : 0
```

| field | hide-control | display | height |
|---|---|---|---|
| `actual_start_date` | **true** | **none** | **0** |
| `actual_end_date` | **true** | **none** | **0** |
| `expected_start_date` | false | block | 0 |
| `total_costing_amount` | false | block | 0 |
| `holiday_list` | true | none | 0 |

### Verdict

| | VFC ON | VFC OFF |
|---|---|---|
| `actual_start_date` (read-only, null) | **visible** | **hidden** |
| `actual_end_date` (read-only, null) | **visible** | **hidden** |
| `hide-control` count | 18 | 22 |

**Same setting, same user, same document. Turning VFC off makes Frappe's hidden
state reappear. The engine is stripping `hide-control` from fields Frappe hid.**

### Negative controls (confirm the mechanism precisely)

| Field | Why it should NOT be hidden | VFC ON | VFC OFF |
|---|---|---|---|
| `expected_start_date` | writable → `status === "Write"`, rule requires `"Read"` | visible | visible |
| `total_costing_amount` | read-only but value `0`; `is_null(0)` is **false** | visible | visible |

Both behave identically with VFC on and off — exactly as the code predicts.
This rules out "VFC just hides/shows things arbitrarily".

### Additional control already present in the data

`copied_from` (Project, permlevel 1, `hidden: 1` in DocType JSON) **retained** its
`hide-control` and is **not** `vfc_managed`. The skip-guard works when `df.hidden`
is set — which is precisely why the two cases differ.

---

## 5. AC-2 — F3 (tabbed doctype) NOT reproduced

`Project` has 4 `Tab Break` fields: `costing_tab`, `monitor_progress_tab`,
`more_info_tab`, `connections_tab`. `Task` has 2.

Browser observation as non-admin `Projects User`:

```
tablist "Tab list" [5 items]
  tab "Details"   tab "Costing"   tab "Progress"   tab "More Info"   tab "Connections"
```

All five tabs render, `SKIP_TYPES` includes `"Tab Break"`
(`vfc_layout_engine.js:311-317`), and the engine did not break tab navigation.
VFC's own host element (`vfc-tab-pane-host`) is guarded at `vfc_layout_engine.js:164`.

**F3 is NOT reproduced on `Project`.** Per the GM's instruction
("do not fix it until reproduced"), **F3 should be struck with this evidence**
unless a reproduction appears on another doctype.

---

## 6. Environment restoration (all verified)

| Item | State |
|---|---|
| `Project-Default.enabled` | `1` (restored) |
| `tabSingles.hide_empty_read_only_fields` | `0` (original value restored) |
| `tabDefaultValue` row for that key | **absent** (row I created removed; it did not exist before) |
| Throwaway user `vfc.p02.test@example.com` | **deleted** |
| `Has Role` rows for that user | `0` |
| `Form Layout Profile` total | `210` (unchanged) |
| `_Test_*` rows (`profile_name`) | **`202` — intact, P0-1 not touched** |
| Real profiles (8 doctypes) | `8` — intact |
| Redis / MariaDB / site | still running |

> **Query correction:** an intermediate verification query used `name LIKE '\_Test\_%'`
> and returned `0`, which is wrong — `name` is prefixed by the doctype
> (`Task-_Test_01a1a7`), while `profile_name` holds the `_Test_*` value.
> Re-run against `profile_name` returns **202**. No data was deleted at any point.

---

## 7. Effect on the plan

| Item | Was | Now |
|---|---|---|
| **P0-2 permlevel case** | "Live — Project confirmed affected today" | **UNREACHABLE** — `Desk User` auto-granted; 0 reachable gates across 9 doctypes |
| **P0-2 hide-empty case** | "LIKELY" / assumed live | **CONFIRMED, reproduced in browser** — but only when `hide_empty_read_only_fields` is on |
| **P0-2 overall** | disputed | **CONFIRMED defect.** Fix is correct and required. |
| **F3** | `LIKELY`, unverified | **NOT reproduced** → strike pending new evidence |
| **Fix rule** | "don't strip on permlevel fields" | **Never strip `hide-control` on any field** — confirmed correct and sufficient |

**Why the fix still matters even though this site had the setting off:** the DocType
JSON default for `hide_empty_read_only_fields` is `"1"`. A fresh install has it **on**.
This site had it explicitly set to `0`, so it was non-representative.

---

*AC-1 and AC-2 complete. Gate satisfied — Phase 1 fixes may be written.*
