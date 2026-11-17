# Integration source consolidation

Snapshot: 17 November 2026. The continuation branch is `t3-integration-review-20261117`. Use this repository checkout for future T3 integration source changes. Production dispatch remains disabled.

## Clean source and Git boundary

The canonical local checkout was cloned directly from this public branch with `--single-branch --depth 1`; private branches, dangling objects and unpushed local history from the bench repository were not copied. The working tree contains the app's published source plus the integration candidate. Installed Frappe sites, database files, credentials, captured conversations, copied T3 profiles, package caches and recovery archives are outside this source checkout. `.gitignore` excludes new local runtime, site and environment-secret files.

A tracked-text scan covered 2,501 text files. Its 54 matches were reviewed as test-only credential/token strings, credential-redaction assertions or translated/display labels. The patterns found no private keys or JWTs. This is a bounded source check, not a claim that pattern scanning proves absence of every possible sensitive value. Existing published binary assets and historical material are inherited from the app baseline; this task did not rewrite public history.

## Recovered earlier work

The existing offline `orchestrator/engineering_control_contracts` package and seven associated test modules were recovered from the earlier integration worktree. They contain WP1 contract/store/provenance proof and WP2 enrollment/projection prototypes. They are standalone, test-only proof; this consolidation does not wire them into a production route.

Their verification reported **314 passed and 3 expected failures**. The three expected failures require the legacy `Engine.reconfigure_role_paused` API, absent from the current runtime. They remain strict expected failures limited to `AttributeError`; compatibility is unresolved and is not counted as passing. An earlier unknown-origin O04 guard file with known conflicts remains in the private recovery archive and is not adopted as an authoritative test.

The previously reviewed candidate also passed 80 focused supervisor/builder/attestation tests and 21 subtests (3 skips), 14 dashboard tests, 51 engine tests, and 40 service/verifier tests with 8 subtests. Those counts refer to the preceding review candidate; the recovered legacy modules were checked separately as stated above. No combined full-app or live production claim is made.

## Local cleanup boundary

Twenty-three historical integration roots were retired after a private archive verified 58,542 retained entries against source checksums: working copies, inactive release/rehearsal directories, integration outputs, synthetic pilots and two inactive integration worktrees. A separate verified Git bundle preserves their shared repository history. Generated caches and sockets are omitted from the recovery archive.

The currently running dashboard's installed releases, service configuration, credentials, canonical runtime state and bench application deployment remain operational. They are deployment dependencies, not development checkouts. Other worktrees for unrelated app tasks and unrelated uncommitted application changes are preserved. Do not delete sites, services or another task's working tree as routine source cleanup.

## Next development session

1. Check out this branch, read the owner/developer reports and the repository engineering instructions.
2. Keep local runtime and credentials outside the checkout. Run source and relevant isolated tests with a disposable environment; do not copy a live database or authentication profile into Git.
3. Resolve the working-provider/service boundary and authenticated real dashboard dispatch gaps identified in the developer report.
4. Reconcile any needed changes from the separately preserved bench application work before a deployment. Never treat an installed checkout or a historical archive as a competing source of new integration edits.
