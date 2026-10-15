# Construction ERP — Customer Onboarding

This guide takes a customer administrator from a delivered app to a working site. It
describes only supported, customer-visible behavior. Internal engineering evidence is
tracked separately and never ships with the app.

## 1. Installation (operator)

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app construction
```

Build: Flit via `pyproject.toml` (version 0.0.5). Canonical app entry after login:
`/app/construction`.

## 2. First login

1. Log in as Administrator.
2. Open **Construction Home** (`/app/construction`). You should see the work areas:
   Site execution, Estimating and commercial, Procurement and stores, Finance, Cost database.
3. Create your Company, then a Project, then a BOQ Header. Each next field unlocks after
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
