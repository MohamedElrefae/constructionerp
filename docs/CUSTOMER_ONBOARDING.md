# Construction ERP — Customer Onboarding

This guide takes a customer administrator from a delivered app to a working site. It
describes only supported, customer-visible behavior. Internal engineering evidence is
tracked separately and never ships with the app.

## 1. Installation (operator)

```bash
cd $PATH_TO_YOUR_BENCH
SITE_NAME="<YOUR_SITE_NAME>"
APP_REPOSITORY="<APPROVED_CUSTOMER_REPOSITORY_URL>"
APP_RELEASE_REF="<QUALIFIED_RELEASE_REF>"
bench get-app --branch "$APP_RELEASE_REF" construction "$APP_REPOSITORY"
bench --site "$SITE_NAME" install-app construction
```

Use only the repository URL and release ref supplied for your customer delivery. The
local staging directory used to prepare that delivery is not an install source; the
engineering checkout and its development branch are not customer release channels.

Build: Flit via `pyproject.toml` (version 0.0.5). Canonical app entry after login:
`/app/construction`.

## 2. First login

Before using the app on a fresh site, complete the ERPNext Setup Wizard and create the
Company and other standard masters required for your operation. Confirm the standard
Warehouse Type **Transit**, UOMs **Nos**, **M3**, **Meter**, and **Kg**, and Item Group
**All Item Groups** exist; these are ERPNext setup data, not created by this app.

BOQ Excel import commit is disabled by default. After validating the import workflow and
confirming the responsible user permissions, an administrator may enable
`enable_boq_excel_import_commit` in **Construction Settings**. Keep it disabled until
the site is ready for committed imports.

1. Log in as Administrator and finish any remaining ERPNext setup wizard steps.
2. Open **Construction Home** (`/app/construction`). You should see the work areas:
   Site execution, Estimating and commercial, Procurement and stores, Finance, Cost database.
3. Confirm the Company and required standard masters are present, then create a Project
   and a BOQ Header. Each next field unlocks after
   the previous one is set (Project → BOQ Header → BOQ Structure → BOQ Item).

## 3. Roles

| Job | Native role | Sees |
|---|---|---|
| Site engineer | Site Engineer | Site execution work area, stages, timesheets |
| Estimator / PM | Project Manager | Estimating and commercial work area, BOQ, analyses, variations |
| Buyer | Purchase User | Procurement and stores |
| Storekeeper | Stock User | Procurement and stores |
| Accountant | Accounts User | Finance work area |
| Cost librarian | Cost Database Maintainer | Cost database work area |

A Construction role never replaces the native role for the same job: a buyer still needs
`Purchase User`, an accountant still needs `Accounts User`. Permissions are checked on the
server on every action; hiding a menu never grants access, and showing one never does either.

## 4. Languages and themes

Each user picks their language on their own User record (Arabic is fully supported,
right-to-left). Light and dark themes are available from the theme menu; the choice is
remembered per user. Column density on forms saves automatically; field-visibility changes
are staged until you press **Apply & Save** — the panel tells you when changes are unsaved
and warns before discarding them.

The release includes the authored theme stylesheets. Per-theme CSS and the login-theme
stylesheet are generated from installed theme records during app installation or theme
updates; they are runtime outputs, not release source files.

## 5. BOQ lifecycle (normal operation)

Draft → Locked → Certified quantities → variation orders for changes. An approved record is
permanent history: corrections go through a new revision or adjustment stage, never by
deleting the approved record. Your operator's backup schedule is the recovery path; ask them
for the restore procedure before you need it.

## 6. Support boundary

Report to your operator (not to end users): the exact page URL, what you clicked, the exact
error text, and the time. Screenshots of the message help. Do not share passwords in chat —
your operator rotates credentials through a separate channel.

Fresh-site role configuration must follow [Construction access setup](PERMISSION_SETUP.md) before the cost-maintainer and construction-report workflows are enabled. Rehearsal grants are not automatically customer grants.
