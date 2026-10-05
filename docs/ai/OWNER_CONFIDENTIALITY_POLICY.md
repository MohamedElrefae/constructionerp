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

## CI continuation

The prepared code-only release candidate `a6bc51c3172255a242674576fecf96c6cfb46ac4` remains local. Its former proposed public branch `codex/customer-release-ci-20261005` is no longer the authorized publication route. The owner chose confidentiality, not permission to retry that public push. Provider CI remains pending until a named private destination and upload scope are approved.

For an approved private destination, verify visibility and outgoing content, upload only the approved candidate, then retain the actual CI run URL, triggering ref, exact SHA, result and failures in local release evidence. Local tests or a prepared workflow do not establish provider CI success. No private destination has been selected or created by this documentation change.

## Source access and prior exposure

Changing this instruction or repository visibility does not recall copies of previously public code. Do not promise retroactive secrecy. Do not silently rewrite Git history, delete remotes or alter license files.

A customer who administers a self-hosted Frappe server can inspect its installed Python application source; browser-delivered JavaScript and CSS are inspectable. If keeping backend source under the owner's control is essential, assess an owner-managed hosted delivery model before promising confidentiality. Hosting, customer access and commercial licensing decisions remain separate.

## Agent context and evidence

The essential rules are also written directly in the mandatory Professional Engineering Standard so new engineering-startup snapshots carry them. Future sessions must honor them without repeatedly asking whether public publication is acceptable. Once a specific private destination and scope are approved, reuse that authorization for operations within its bounds; investigate changed visibility or content before proceeding.

Existing immutable governed job packets are not rewritten by this change. Reconcile older contexts through their workflow and refresh candidate-bound startup evidence when required. These are documented agent instructions, not a newly implemented automatic Git/network enforcement mechanism.

Recorded in the main app checkout and the isolated customer-release worktree. Only instruction/session/release documentation changes; no app code, site data, remote settings, publication, CI execution or deployment is implied.
