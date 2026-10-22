# VFC Layout Engine — Full App Coverage Status

## How It Works

The engine has **two layers of control**:

1. **`BLOCKED_DOCTYPES` blocklist** (JS) — blocks known core Frappe internal system/auth doctypes and child tables from being VFC-managed.
2. **`Form Layout Profile` record** (DB) — defines sections & field layout. Without one, the engine is a no-op (graceful fallback), but the **density slider still works**.

---

## Current Status — Stage 2 (Full ERPNext App Active) ✅

The VFC layout engine is now fully active across **all flat-layout forms in the entire ERPNext app**.

* **No disruption:** Forms without a Form Layout Profile record will look exactly as native Frappe (no layout shifting, no missing data).
* **On-Demand Layout Design:** To apply custom grid layout systems to any form in ERPNext (e.g. Purchase Order, Sales Invoice, Item, Customer, etc.):
  1. Open the document form.
  2. Click the **Form Config** button in the header.
  3. Arrange/drag fields into sections.
  4. Save the profile.
  5. The VFC engine instantly renders that layout for all users.
* **Density control:** The visual density slider (Layout settings) works immediately on every form (even without a profile saved).

---

## Blocked Doctypes (Excluded from VFC)

The following core system doctypes are explicitly excluded from VFC processing to ensure platform stability:
* DocType, DocField, DocPerm
* Custom Field, Property Setter
* Client Script, Server Script
* Report, Page, Workflow Actions
* Patch/Error Logs, Version, Tag
* System, website, domain settings
* All child table/grid-only doctypes (e.g. Direct Labor Designation)
* All tabbed doctypes containing **Tab Break** fields (engine skips these automatically to let native tabs render correctly).

---

## Verification & Deployment

1. **Deploy to Frappe Cloud:** Push the latest code. When the app is deployed or migrated, the hooks will compile.
2. **Local testing:** Try opening standard ERPNext forms. Notice the **Form Config** button is now present on all forms.
3. **Designing a layout:** Open a document, configure the sections, and save. Verify the visual layout shifts to 2/3 columns as chosen, while forms without profiles remain untouched.
