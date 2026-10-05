# Owner confidentiality and private CI policy

**Owner decision:** 2026-10-05 — “keep its implementation confidential”.

This is the owner's standing instruction for Construction development, release preparation, CI and agent sessions. It supersedes the earlier pending proposal to publish the customer-release candidate to a public repository. Routine local implementation, verification and consultant decisions remain authorized within the requested task.

## Mandatory publication boundary

- Keep unpublished Construction source, private findings, internal reports, customer/site records, credentials, encryption configuration and backups confidential.
- Do not push new app commits, patches or sensitive reports to a public repository, including a new branch or pull request in an existing public repository.
- Use local evidence and a specifically approved private destination for provider CI. Verify destination ownership, private visibility, collaborators and log/artifact access before the first upload. Record the exact repository and approved content scope.
- This preference does not itself authorize creating a remote repository, changing an existing repository's visibility, uploading to an unspecified account, merging, upgrading sites or deploying to customers. Prepare the concrete destination and outgoing candidate before requesting any missing final authority.
- Review all commits being uploaded, not only the working-tree diff. Local history may contain private documents; an approved code-only publication candidate must exclude them from newly uploaded history. Review tracked files, workflow inputs, logs and artifacts for secrets and private data.
- Inspect Git hooks and other automatic capture mechanisms. Do not send private source or commit metadata to external memory or connectors without an approved destination and scope. For local commits, disable transmitting hooks per command when needed; do not weaken global security settings.
- Do not use private source excerpts or customer records in public web searches, issues or support messages. Public upstream documentation and generic searches remain available.
- Preserve the boundary after a tool rejection. Do not obtain the same public disclosure through browser upload, an alternate remote, a PR or another transport.

## CI continuation — named authorization, 2026-10-05

The owner explicitly authorized: “create the private GitHub repository MohamedElrefae/constructionerp-private, upload the reviewed code-only candidate a6bc51c, and run CI. Keep private reports, credentials, backups and site data excluded.” This authorization persists for completing this candidate's CI at the named private destination, including bounded installation/test-harness corrections required to execute the existing checks. It does not approve unrelated future app candidates or arbitrary local Git history.

[MohamedElrefae/constructionerp-private](https://github.com/MohamedElrefae/constructionerp-private) was created under the named personal owner and observed **Private** before upload, without adding collaborators. The clean root snapshot `11c48b2d9223153c83a6523261f625e484506f30` contains 569 allowlisted source/build files byte-identical to `a6bc51c3172255a242674576fecf96c6cfb46ac4`. It excludes inherited history and 1,066 tracked files, including documentation/reports and stashed-code backups, as well as all untracked/site/private data. Its different SHA reflects this protective export, not a changed app. The initial root retained two obsolete 917-byte source fixture `.bak` templates without site records; these were subsequently removed from the current export, without rewriting historical Git. No private site backups were uploaded. Current export `116562f` contains 569 files; 566 original non-workflow files remain byte-identical, alongside bounded CI harness corrections, a gated installation diagnostic helper, and guarded synthetic CI business fixtures. The private branch is `codex/customer-release-ci-20261005`; never push the main or release checkout's document-bearing history there.

Actual CI execution is now authorized and occurred. Retain run URL, triggering ref, exact SHA and completed result in local release evidence. The first run failed at installation before tests; a bounded workflow-only correction was pushed as `2f054fec0796166016e41e1a9ec4c3ad032cd994`. See [private CI publication/run record](work-items/customer-release-gap-fixes/PRIVATE_CI.md) in the release worktree for current outcome, evidence and subsequent harness corrections. Do not equate authorization, a prepared workflow or a partial provider run with CI success.

Before any continuation upload, verify the named destination remains private and keep content/history within this reviewed scope. Do not publish local reports, credentials, backups, site records or external-memory metadata. Existing public remotes are outside this authorization. No merge, shared-site migration, customer deployment or public visibility change is granted.

## Source access and prior exposure

Changing this instruction or repository visibility does not recall copies of previously public code. Do not promise retroactive secrecy. Do not silently rewrite Git history, delete remotes or alter license files.

A customer who administers a self-hosted Frappe server can inspect its installed Python application source; browser-delivered JavaScript and CSS are inspectable. If keeping backend source under the owner's control is essential, assess an owner-managed hosted delivery model before promising confidentiality. Hosting, customer access and commercial licensing decisions remain separate.

## Agent context and evidence

The essential rules are also written directly in the mandatory Professional Engineering Standard so new engineering-startup snapshots carry them. Future sessions must honor them without repeatedly asking whether public publication is acceptable. Once a specific private destination and scope are approved, reuse that authorization for operations within its bounds; investigate changed visibility or content before proceeding.

Existing immutable governed job packets are not rewritten by this change. Reconcile older contexts through their workflow and refresh candidate-bound startup evidence when required. These are documented agent instructions, not a newly implemented automatic Git/network enforcement mechanism.

Recorded in the main app checkout and the isolated customer-release worktree. This local policy records the separately authorized private creation, code-only upload and CI execution. It grants no additional source integration, site mutation, customer deployment or public publication.
