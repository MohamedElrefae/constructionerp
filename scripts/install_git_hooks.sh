#!/usr/bin/env bash
# Install git hooks for auto-capturing memories on commits.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
POST_COMMIT="$HOOKS_DIR/post-commit"

cat > "$POST_COMMIT" << 'HOOK'
#!/usr/bin/env bash
# Auto-capture commit info to MemoryGraph MCP.

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMMIT_MSG="$(git log -1 --pretty=%B)"
COMMIT_HASH="$(git log -1 --pretty=%H)"
CHANGED_FILES="$(git diff-tree --no-commit-id --name-only -r HEAD | tr '\n' ' ')"
AUTHOR="$(git log -1 --pretty=%an)"

PYTHON="/home/mohamed/.local/share/pipx/venvs/memorygraphmcp/bin/python"

# Only store if commit message is meaningful (skip merge commits, etc.)
if [[ -n "$COMMIT_MSG" && ! "$COMMIT_MSG" =~ ^Merge\  && ! "$COMMIT_MSG" =~ ^Revert\  ]]; then
    "$PYTHON" "$REPO_ROOT/scripts/mcp_store.py" \
        --type "code_pattern" \
        --title "Commit $COMMIT_HASH: ${COMMIT_MSG:0:80}" \
        --content "Commit by $AUTHOR:\n$COMMIT_MSG\n\nFiles changed: $CHANGED_FILES" \
        --tag "git" --tag "commit" --tag "construction" \
        --importance 0.6 \
        --file "$CHANGED_FILES" 2>/dev/null || true
fi
HOOK

chmod +x "$POST_COMMIT"
echo "Installed post-commit hook to $POST_COMMIT"
