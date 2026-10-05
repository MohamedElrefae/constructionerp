# Recommended first customer operating profile

This is the consultant's engineering recommendation, not a hosting purchase, support contract, release approval or promise of capacity. The owner has not yet selected delivery or a sold workload. Use this conservative profile when preparing a customer pilot; revise it with measured evidence before making commercial promises.

## Delivery and isolation

Start with a separate Frappe site and database for each customer. Keep development and synthetic/test records outside customer sites. Site separation reduces accidental cross-customer access; it does not isolate the shared app code, Python runtime, workers or host. Use a separate Bench/runtime for a customer requiring an independent upgrade schedule or stronger operational isolation. Never advertise a shared-site multi-company service before a complete access matrix has passed.

Pin Construction, Frappe and ERPNext commits and preserve the resolved dependency inventory and asset hashes with each release. The current qualification covers only the recorded Frappe 16.18.1 / ERPNext 16.18.3 commits on MariaDB 10.11 and the isolated Python 3.14 runtime. Do not advertise v15 or other database/runtime combinations from this evidence. A clean build and `pip check` establish installability and metadata consistency; unresolved advisories remain a separate release gate.

## Release procedure

1. Freeze a reviewed candidate and capture its source, dependencies, schema, tests and assets. Run actual provider CI for that candidate; keep its URL and commit identity. Local tests do not replace this evidence.
2. Inventory every site served by the Bench before switching its app checkout or environment. Back up database, public/private files and encryption configuration for each authorized affected site. Verify a restore into a separate disposable target before upgrade.
3. Enter a scheduled maintenance window; stop incoming work and drain workers before changing code or schema. Migrate each authorized site with the same candidate, build assets and clear caches. Restore traffic only after permission, pricing, report and attachment smoke checks pass.
4. For a failed schema/data upgrade, recover matching code, database, files and encryption configuration together. A Git revert alone cannot reverse a data migration. Preserve failure evidence and the pre-upgrade backup.
5. Keep the customer release withheld if security, correctness, authorization or restoration checks fail. Record which routes and versions were actually qualified.

The shared local Bench currently serves localhost, v16.localhost and v16rehearsal.localhost. Authority for v16.localhost does not grant authority to migrate the other two. Either obtain their explicit upgrade authorization or provision a separate Bench for v16; do not switch shared code while those sites retain incompatible schemas.

## Operations before paid customer use

Assign a named operator for backups, restoration, patching and incidents. Configure HTTPS, private database/Redis access, secret storage, least-privilege customer roles and monitoring for HTTP failures, worker/queue failures, disk growth and backup failures. Verify these on the selected hosting environment rather than inferring them from local tests.

Use encrypted off-host database/files/config backups with access controls and a documented retention policy. Select RPO/RTO with the owner and hosting operator, then rehearse recovery on representative data. Local recovery timings are observations, not contractual recovery objectives. Test a private attachment and encrypted secret after restoration, as well as commercial totals and immutable approval history.

Before a pilot, select one representative project and its BOQ, analysis, quantity revision, variation order, resource plan, export and Arabic/English print workflow. Run it with the intended estimator, project manager, accountant and restricted user roles. Verify expected values with the civil engineer; store synthetic or approved redacted fixtures for future regressions. Preserve owner-classified test remnants separately and exclude them from customer seed data.

## Support and capacity

Offer a defined pilot scope before promising unrestricted features, project sizes, concurrent users or a support SLA. Publish the supported version and known limitations. Measure the sold mix of reads, writes, reports, imports and PDF generation through the actual web/worker/proxy stack. Synthetic Administrator read measurements cannot establish customer write throughput or whole-system capacity.

An incident handover should identify the affected version/site, business impact, reproducible steps, safe workaround, recovery decision and follow-up correction. Financial or approval corrections need traceable revisions; direct SQL edits are not routine customer support. Any temporary security acceptance requires a documented affected path, effective mitigation, owner decision, expiry and vendor-upgrade plan. Unresolved findings cannot be relabeled as fixed because installation succeeds.

## Continuing development

Follow the repository Professional Engineering Standard and enforced engineering startup evidence. Use Luna for bounded inventory, documentation, fixtures and routine implementation; retain parent consultant review for financial semantics, permissions, migration strategy and release claims. Keep work isolated, test the actual lifecycle and denied path, review the final diff, and commit only the approved scope. A feature is maintainable when its business rule, authorization, migration behavior and meaningful regressions are understandable to the next session.
