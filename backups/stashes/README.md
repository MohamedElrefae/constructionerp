# Stash Backups

Local git stashes cannot be pushed to a remote, so they are exported here as
patch files to keep the online repository a complete backup.

| Patch | Original stash | Base | Contents |
|---|---|---|---|
| `stash-0-feat-integrate-broader-app-work.patch` | `stash@{0}` | 3bffdae (feat/integrate-broader-app-work, PR #9 merge) | 12 files, +3206/−34 — scope-context docs/evidence (EV-068 WP2 finish, Option B design) |
| `stash-1-develop-unrelated-option-a-plus.patch` | `stash@{1}` | develop (pre-Option A+) | 2 files — hooks.py tweak + typography_settings.js rework |
| `stash-2-release-v6.8-unrelated.patch` | `stash@{2}` | release/v6.8 | 2 files — install.py additions + notes |

Exported: 2026-08-19

## Restoring a stash from a patch

```bash
git apply --3way backups/stashes/stash-0-feat-integrate-broader-app-work.patch
```

The `--3way` flag allows git to fall back to a three-way merge using the blob
SHA references embedded in the patch, so it applies even if the base commits
have diverged. Review the result with `git diff` before committing.

These stashes predate the Phase 1/Phase 2 cost-engine work and are likely
stale; they are preserved for reference only.
