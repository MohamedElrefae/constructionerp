# Construction ERP — Site Maintenance

This guide is for the customer’s Frappe site administrator. Use the approved customer
repository and qualified release ref provided with your delivery. Do not update an
installed site from an engineering checkout or development branch.

## Before an update

1. Schedule a maintenance window and notify users.
2. Take a full site backup and confirm that the database and files backup completed.
3. Record the current app version and the exact customer release ref being installed.
4. Confirm that the target Frappe and ERPNext versions satisfy the app’s release
   requirements in `pyproject.toml`.

## Install an approved release

```bash
cd $PATH_TO_YOUR_BENCH
APP_REPOSITORY="<APPROVED_CUSTOMER_REPOSITORY_URL>"
APP_RELEASE_REF="<QUALIFIED_RELEASE_REF>"
SITE_NAME="<YOUR_SITE_NAME>"
bench get-app --branch "$APP_RELEASE_REF" construction "$APP_REPOSITORY"
bench --site "$SITE_NAME" install-app construction
```

For an update to an existing site, retrieve the approved release using the operator’s
established Bench update procedure, then run:

```bash
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```

Do not run migration on a customer site until the backup has been verified and the
release notes identify the update as qualified for that site’s current versions.

## If an update fails

Stop further migrations or manual database edits. Preserve the command output and time,
then contact the operator or implementation partner. Follow the site’s tested restore
procedure if service recovery is required; do not restore a backup over a live site
without the owner’s incident approval.

## Compatibility and app behavior

The installed app package contains the application modules, DocType definitions, hooks,
patches, public assets, and runtime translation and glossary data. Bench manages Frappe
and ERPNext; app dependencies and supported framework versions are declared in
`pyproject.toml` and `requirements.txt`. The customer release notes are authoritative for
the exact framework versions qualified with a particular app release.

For role setup, follow [Permission Setup](PERMISSION_SETUP.md). For normal operator
workflows, follow [Customer Onboarding](CUSTOMER_ONBOARDING.md) and [Bilingual Task
Guides](BILINGUAL_TASK_GUIDES.md).
