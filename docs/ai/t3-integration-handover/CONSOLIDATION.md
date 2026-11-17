# Integration source consolidation

Snapshot: 17 November 2026. Production builder dispatch remains disabled.

## One development checkout

The bench application's `apps/construction` checkout is the local source of truth. The reviewed public integration commits were merged into that app after a separate checkpoint preserved its existing application changes. The local continuation branch is `local/app-consolidated-20261117`. Dashboard and orchestrator source belong inside this app; they are functional components, not disposable duplicate folders.

The public `t3-integration-review-20261117` branch is the sanitized sharing branch for external agents. It excludes the app's private local commits and unrelated unpublished work. Do not push the local consolidation branch, its complete Git history, private archives, credentials or installed state to the public repository. The temporary publication clone is retired after synchronization; it is not a second development checkout.

## Runtime and cleanup

The five formerly scattered top-level T3 dashboard directories were consolidated into `runtime/dashboard` under the bench. This is installed runtime and private state, not an editable development checkout. Its immutable dashboard snapshot and canonical state remain in use. The merged app candidate has not been rebuilt and qualified as the live production release.

The startup supervisor, restart helper, catalogue publisher and credential-maintenance source now live in the app's `dashboard/operations`, with the shared allowlist file helper in `dashboard/catalog_files.py`. Their active services use that source. The obsolete alternate dashboard service and superseded tool copies were retired. No model was run during cleanup.

An additional 27 role-debug folders and all ten working copies under the bench's `worktrees` directory were removed after a private archive verified 28,549 entries. Generated dependency environments and caches were excluded from that archive. One idle draft dashboard task referring to a retired worktree was unregistered; its history and pre-change registry were preserved. There were no executing or recovering dashboard actions. Account-file bytes were unchanged.

Earlier cleanup retired 23 historical integration roots after verifying 58,542 archive entries. Another verified archive preserves the pre-relocation dashboard and service configuration (6,093 entries). Verified private Git bundles preserve original and consolidated local history. Recovery archives can contain secrets and private work: keep them outside Git and do not restore old runtime databases over current state.

Frappe sites and customer databases, active credentials and unrelated hidden feature worktrees are outside this cleanup. Historical design documents describe earlier experiments; the current handover reports define the integration status. Preserving a document does not make it a second active plan.

## Verification

The merged actual app passed **86 focused engine/builder/result tests and two subtests**, plus five dashboard dispatch-control tests. Schema drift validation passed; the host context checker passed all 12 checks, including 183 JavaScript regressions. Its first restricted-sandbox invocation failed two subprocess-based test files; the host rerun passed without code changes. The relocated guarded startup was observed ready, the dashboard returned HTTP 200, and unauthenticated task access returned 401. The catalogue refresh and metadata-only expiry services completed successfully. Catalogue output allowlisting, private output permissions, the four expiry-warning levels and the relocated rotation-command path were checked. Credential issuance/rotation and a real reboot were not exercised by this cleanup.

Previously recovered standalone WP1/WP2 contract, enrollment and projection tests reported 314 passed and three strict expected failures limited to the absent legacy `Engine.reconfigure_role_paused` API. These prototypes remain test-only. Earlier candidate test counts and real-model pilot limits remain in the developer report; they are not evidence of production isolation or authenticated live builder dispatch.

## Sanitization boundary

The earlier published source scan covered 2,501 text files and reviewed its matches as synthetic fixtures, redaction assertions or display labels. Added operational source contains no copied credential values or runtime records. Pattern scanning is bounded evidence, not proof that every possible sensitive value is absent. Existing published binary assets and public history were not comprehensively rewritten. The actual app's private local Git history remains private even though the sharing branch is sanitized.

## Continue here

Use the app checkout for local edits and this handover for current status. Use the public sharing branch for online agents. Follow the developer report's remaining provider/service-boundary and authenticated dashboard-dispatch checks before enabling production work. Keep private runtime outside versioned source; do not create another competing full app copy.
