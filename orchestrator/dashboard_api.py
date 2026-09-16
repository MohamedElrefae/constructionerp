"""Subprocess API for Civil Engineer Dashboard.

Sole owner of execution.lock during mutations. Executes Engine operations,
runs action-specific preflight checks, deduplicates requests under lock,
and returns JSON to stdout.
"""

import argparse
import html
import json
import re
import sqlite3
import sys
import urllib.parse
import uuid
from pathlib import Path

# Ensure orchestrator package directory is in sys.path so both
# `python -m orchestrator.dashboard_api` and direct script execution work
_orchestrator_dir = Path(__file__).resolve().parent
if str(_orchestrator_dir) not in sys.path:
    sys.path.insert(0, str(_orchestrator_dir))

from core import (
    DuplicateKeyConflict,
    GrantReconciliationRequired,
    PreconditionError,
    RecoveryError,
    ValidationError as CoreValidationError,
    WorkflowError,
    canonical,
    execution_lock,
    within,
)
from engine import Engine
from preflight import (
    run_dispatch_preflight,
    run_display_checks,
    run_init_checks,
    run_owner_action_checks,
)

_PATH_RE = re.compile(r"(?<!\]\()(?<![:/\w])/(?:[\w\.\-]+/)+[\w\.\-]+")
_SECRET_KEYWORDS = (
    r"api[_-]?key|api[_-]?secret|access[_-]?token|auth[_-]?token|secret[_-]?key|"
    r"client[_-]?secret|private[_-]?key|password|passwd|secret|token|bearer"
)
_QUOTED_CREDENTIAL_PATTERN = re.compile(
    rf"""(?i)(?P<prefix>['"]?(?:{_SECRET_KEYWORDS})\b['"]?\s*[:=]\s*)(?P<quote>['"])(?P<secret>(?:\\.|(?!(?P=quote))[^\r\n])*?)(?P=quote)""",
    re.VERBOSE,
)
_UNQUOTED_CREDENTIAL_PATTERN = re.compile(
    rf"""(?i)(?P<prefix>\b(?:{_SECRET_KEYWORDS})\b\s*[:=]\s*)(?P<secret>[^\s'\",;}}\]\)>]+)""",
    re.VERBOSE,
)
_BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)(['\"]?)([^\s'\",;]+)(['\"]?)")
_HTML_TAG_RE = re.compile(
    r"</?\s*[a-zA-Z][^>]*>|<!(?:--[\s\S]*?--|[\s\S]*?)>|<\?[\s\S]*?\?>",
    re.IGNORECASE,
)
_MD_REF_DEF_RE = re.compile(
    r"^([ \t]*(?:[>]+\s*)*(?:(?:[-*+]|\d+\.)\s+)?\[[^\]]+\]:[ \t]*(?:\r?\n[ \t]*)?)(?:<(?P<url_angle>[^>\r\n]+)>|(?P<url_bare>\S+))(?P<tail>[^\r\n]*)$",
    re.MULTILINE,
)
_MD_REF_LINK_RE = re.compile(r"(!?\[[^\]]*\])\[([^\]]+)\]")
_MD_SHORTCUT_RE = re.compile(r"(?<!\])\[([^\]]+)\](?![\[\(])")


def strip_paths(text: str, root: Path | str | None = None) -> str:
    """Mask absolute host paths and external filesystem paths."""
    if not text:
        return ""
    if root:
        root_str = str(Path(root).resolve())
        text = text.replace(root_str, "[WORKTREE]")
    return _PATH_RE.sub("[PATH]", text)


def _is_safe_url(url: str) -> bool:
    url = url.strip()
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1].strip()
    unescaped = html.unescape(url)
    unquoted = urllib.parse.unquote(unescaped)
    cleaned = re.sub(r"[\x00-\x20\s]+", "", unquoted).lower()
    colon_pos = cleaned.find(":")
    if colon_pos != -1:
        scheme = cleaned[:colon_pos]
        if "/" not in scheme and "?" not in scheme and "#" not in scheme:
            if scheme not in {"http", "https", "mailto"}:
                return False
    return True


def _scan_and_sanitize_inline_links(text: str) -> str:
    """Scan and sanitize Markdown inline links with arbitrary balanced parentheses.

    Handles nested parens such as [click](javascript:alert((1))) or
    [safe](https://example.com/a(b(c))) without regex backtracking or depth limits.
    """
    out = []
    i = 0
    n = len(text)
    last_end = 0
    while i < n:
        if text[i] == "[" or (text[i] == "!" and i + 1 < n and text[i + 1] == "["):
            start = i
            is_img = text[i] == "!"
            if is_img:
                i += 1
            bracket_depth = 1
            i += 1
            while i < n and bracket_depth > 0:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "[":
                    bracket_depth += 1
                elif text[i] == "]":
                    bracket_depth -= 1
                i += 1
            if bracket_depth == 0 and i < n and text[i] == "(":
                label = text[start:i]
                paren_start = i + 1
                paren_depth = 1
                i += 1
                while i < n and paren_depth > 0:
                    if text[i] == "\\":
                        i += 2
                        continue
                    if text[i] == "(":
                        paren_depth += 1
                    elif text[i] == ")":
                        paren_depth -= 1
                    i += 1
                if paren_depth == 0:
                    raw_dest = text[paren_start:i - 1].strip()
                    url = raw_dest
                    title = ""
                    if raw_dest.startswith("<"):
                        gt = raw_dest.find(">")
                        if gt != -1:
                            url = raw_dest[1:gt].strip()
                            title = raw_dest[gt + 1:].strip()
                    else:
                        parts = raw_dest.split(None, 1)
                        if parts:
                            url = parts[0]
                            if len(parts) > 1:
                                title = parts[1]
                    if "[" in label[1:]:
                        label = _scan_and_sanitize_inline_links(label)
                    out.append(text[last_end:start])
                    if not _is_safe_url(url):
                        title_suffix = f" {title}" if title else ""
                        out.append(f"{label}(#blocked{title_suffix})")
                    else:
                        out.append(f"{label}({raw_dest})")
                    last_end = i
                    continue
            i = start + 1
        else:
            i += 1
    out.append(text[last_end:])
    return "".join(out)


def _sanitize_md_links(text: str) -> str:
    text = _scan_and_sanitize_inline_links(text)

    def _replace_ref(match: re.Match) -> str:
        prefix = match.group(1)
        url = match.group("url_angle") or match.group("url_bare")
        tail = match.group("tail") or ""
        if not _is_safe_url(url):
            return f"{prefix}#blocked{tail}"
        return match.group(0)

    text = _MD_REF_DEF_RE.sub(_replace_ref, text)
    text = _MD_REF_LINK_RE.sub(
        lambda m: f"{m.group(1)}[#blocked]" if not _is_safe_url(m.group(2)) else m.group(0),
        text,
    )
    text = _MD_SHORTCUT_RE.sub(
        lambda m: "[#blocked]" if not _is_safe_url(m.group(1)) else m.group(0),
        text,
    )
    return text


def render_plan_as_safe_text_html(plan_text: str) -> str:
    """Render plan text as safe HTML using plain-text escaping.

    Contract: The plan output is explicitly plain text. Consuming dashboards and
    UIs MUST render this text using DOM textContent (or equivalent safe plain text
    DOM node insertion such as <pre class='plan-display'> with element.textContent = ...),
    and MUST NEVER render it via innerHTML, outerHTML, or raw HTML injection.
    """
    escaped = html.escape(plan_text, quote=True)
    return f"<pre class=\"plan-text-display\">{escaped}</pre>"


def sanitize_plan_text(text: str, root: Path | str | None = None) -> str:
    """Sanitize plan text while preserving legitimate bilingual Arabic content.

    Output Contract:
    The plan output is explicitly plain text (format='plain_text', render_mode='text_content').
    Consuming dashboards and UIs MUST render this text using DOM textContent (or equivalent
    safe plain text DOM node insertion), and MUST NEVER interpret or inject it via innerHTML,
    outerHTML, or un-sanitized Markdown-to-HTML conversion.

    Defense-in-depth sanitization:
    - Redacts credentials in JSON, YAML, and key-value formats (quoted and unquoted).
    - Masks host absolute paths and worktree locations.
    - Disables raw HTML tags (including multiline tags, scripts, iframes, images).
    - Neutralizes Markdown links specifying unsafe URL schemes (javascript:, data:, vbscript:, etc.)
      across arbitrary nested parentheses, angle brackets, and reference definitions inside
      blockquotes and lists.
    - Preserves legitimate Arabic bilingual content and safe URLs.
    """
    if not isinstance(text, str):
        return ""
    sanitized = strip_paths(text, root=root)
    sanitized = _QUOTED_CREDENTIAL_PATTERN.sub(
        r"\g<prefix>\g<quote>[REDACTED_CREDENTIAL]\g<quote>", sanitized
    )
    sanitized = _UNQUOTED_CREDENTIAL_PATTERN.sub(
        r"\g<prefix>[REDACTED_CREDENTIAL]", sanitized
    )
    sanitized = _BEARER_PATTERN.sub(r"\1\2[REDACTED_CREDENTIAL]\4", sanitized)
    sanitized = _sanitize_md_links(sanitized)
    sanitized = _HTML_TAG_RE.sub(
        lambda m: m.group(0).replace("<", "&lt;").replace(">", "&gt;"), sanitized
    )
    return sanitized


def sanitize_error(exc: Exception, root: Path | str | None = None) -> dict:
    """Return fixed public error message with support ID and strip all paths."""
    support_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
    exc_type = type(exc).__name__

    if isinstance(exc, PreconditionError):
        msg = "Precondition check failed"
    elif isinstance(exc, (CoreValidationError, ValueError)):
        msg = "Invalid request or validation failed"
    elif isinstance(exc, DuplicateKeyConflict):
        msg = "Duplicate action or conflicting request"
    elif isinstance(exc, GrantReconciliationRequired):
        msg = "Grant reconciliation required"
    elif isinstance(exc, RecoveryError):
        msg = "Workflow recovery error"
    elif isinstance(exc, WorkflowError):
        msg = "Workflow execution error"
    else:
        msg = "An unexpected error occurred"

    msg = strip_paths(msg, root=root)

    return {
        "error": msg,
        "error_type": exc_type,
        "support_id": support_id,
    }


PUBLIC_PAUSE_CATEGORIES = {
    "OPERATOR_PAUSED",
    "BUDGET_EXHAUSTED",
    "GATE_PENDING",
    "VERIFICATION_FAILED",
    "EXECUTION_ERROR",
    "RECONCILIATION_REQUIRED",
    "ESCALATED",
    "MALFORMED_RESULT",
}


def categorize_pause_reason(raw_reason: str | None) -> str | None:
    """Project internal pause reasons into fixed public categories.

    Prevents leaking private operator instructions, credentials, or paths.
    """
    if not raw_reason:
        return None
    r_upper = str(raw_reason).strip().upper()
    if r_upper in PUBLIC_PAUSE_CATEGORIES:
        return r_upper
    r = str(raw_reason).lower()
    if any(k in r for k in ("reconcil", "grant")):
        return "RECONCILIATION_REQUIRED"
    if any(k in r for k in ("malform", "corrupt", "schema")):
        return "MALFORMED_RESULT"
    if any(k in r for k in ("escalat", "cycle", "loop")):
        return "ESCALATED"
    if any(k in r for k in ("budget", "cost", "token_limit", "max_iterations")):
        return "BUDGET_EXHAUSTED"
    if any(k in r for k in ("gate", "approval", "plan_review", "scope_review")):
        return "GATE_PENDING"
    if any(k in r for k in ("verify", "verification", "check_failed", "lint")):
        return "VERIFICATION_FAILED"
    if any(k in r for k in ("error", "exception", "halt", "crash", "failure")):
        return "EXECUTION_ERROR"
    return "OPERATOR_PAUSED"


def get_state_projection(root: Path | str) -> dict:
    """Dedicated read-only projection of workflow state.

    Does NOT instantiate Engine, acquire exclusive execution.lock, or mutate
    any files, checkpoints, or role mirrors.
    """
    root = Path(root).resolve()
    runtime_path = root / "orchestrator/var"
    checks = run_display_checks(runtime_path)
    failed = [c for c in checks if not c.ok]
    if failed:
        raise PreconditionError(f"Display preflight failed: {failed}")

    db_path = runtime_path / "checkpoints.db"
    if not db_path.exists():
        return {"status": "NOT_INITIALIZED"}

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        saver = SqliteSaver(conn)
        checkpoint = saver.get({"configurable": {"thread_id": "workflow"}})
        if not checkpoint or not checkpoint.get("channel_values"):
            return {"status": "NOT_INITIALIZED"}
        v = checkpoint["channel_values"]["view"]
    finally:
        conn.close()

    # Allowlisted projection: exclude host absolute paths, private tokens,
    # internal hashes, gate IDs, approval refs, and stage evidence
    gate_data = v.get("gate")
    gate_proj = None
    if isinstance(gate_data, dict):
        gate_proj = {"scope": gate_data.get("scope")}

    projected_stages = {}
    for stg_id, stg_data in (v.get("stages") or {}).items():
        if isinstance(stg_data, dict):
            projected_stages[stg_id] = {
                "status": stg_data.get("status"),
                "sub_status": stg_data.get("sub_status"),
                "historical": bool(stg_data.get("historical", False)),
            }
        else:
            projected_stages[stg_id] = {"status": str(stg_data)}

    raw_pause = v.get("pause_reason")
    sanitized_pause = categorize_pause_reason(raw_pause)

    return {
        "work_item": v.get("work_item"),
        "stage": v.get("stage"),
        "status": v.get("status"),
        "sub_status": v.get("sub_status"),
        "pause_reason": sanitized_pause,
        "resume_to": v.get("resume_to"),
        "gate": gate_proj,
        "plan_granted": bool(v.get("plan_granted")),
        "active_jobs": [
            {
                "role": j.get("role") if isinstance(j, dict) else None,
                "status": j.get("status") if isinstance(j, dict) else None,
            }
            for j in (v.get("active_jobs") or [])
        ],
        "stages": projected_stages,
        "next_roles": v.get("next_roles", []),
    }


def get_plan_projection(root: Path | str) -> dict:
    """Dedicated read-only projection of the workflow's approved plan text.

    Output Contract:
    The returned plan projection is explicitly plain text (format='plain_text',
    render_mode='text_content'). Consuming dashboards and UIs MUST render plan_text
    using DOM textContent (e.g. element.textContent = result.plan_text), and MUST NEVER
    render or inject it via innerHTML, outerHTML, or raw Markdown-to-HTML conversion.

    Does NOT accept request-supplied file paths, instantiate Engine, acquire
    exclusive execution.lock, or mutate any files. Resolves ONLY the workflow's
    approved plan artifact from checkpoints metadata.
    """
    root = Path(root).resolve()
    runtime_path = root / "orchestrator/var"
    checks = run_display_checks(runtime_path)
    failed = [c for c in checks if not c.ok]
    if failed:
        raise PreconditionError(f"Display preflight failed: {failed}")

    db_path = runtime_path / "checkpoints.db"
    if not db_path.exists():
        return {
            "plan_text": "",
            "plan_path": "",
            "format": "plain_text",
            "render_mode": "text_content",
        }

    plan_art = None
    plan_cfg_path = ""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM workflow_meta WHERE key='plan_artifact'").fetchone()
        if row:
            plan_art = json.loads(row[0]) if row[0].startswith('"') else row[0]
        cfg_row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
        if cfg_row:
            cfg = json.loads(cfg_row[0])
            plan_cfg_path = cfg.get("plan_path", "")
    finally:
        conn.close()

    rel_path = plan_art or plan_cfg_path
    if not rel_path:
        return {
            "plan_text": "",
            "plan_path": "",
            "format": "plain_text",
            "render_mode": "text_content",
        }

    # Reject absolute paths, directory traversal, and symlink escapes before reading
    try:
        full_path = within(root, str(rel_path), allow_leaf_symlink=False)
        if full_path.is_symlink() or not full_path.resolve().is_relative_to(root):
            raise PreconditionError(f"Unsafe plan_path: {rel_path} escapes worktree boundary")
    except (WorkflowError, ValueError) as exc:
        raise PreconditionError(f"Unsafe plan_path: {rel_path} escapes worktree boundary") from exc

    if not full_path.exists():
        return {
            "plan_text": "",
            "plan_path": str(full_path.relative_to(root)),
            "format": "plain_text",
            "render_mode": "text_content",
        }

    raw_text = full_path.read_text(encoding="utf-8", errors="replace")
    clean_text = sanitize_plan_text(raw_text, root=root)

    return {
        "plan_text": clean_text,
        "plan_path": str(full_path.relative_to(root)),
        "format": "plain_text",
        "render_mode": "text_content",
    }


def deduplicate_action(
    action_id: str | None,
    request_hash: str,
    token_id: str | None,
    submitted_token: dict | None,
    store=None,
    engine=None,
) -> dict | None:
    """Called under execution.lock before executing any mutation."""
    if store is None and engine is not None:
        store = engine.store

    # --- Approval deduplication ---
    if token_id and submitted_token is not None:
        # Validate lookup key matches token's own token_id before any DB access.
        if submitted_token.get("token_id") != token_id:
            raise CoreValidationError(
                f"submitted_token['token_id']={submitted_token.get('token_id')!r} "
                f"does not match lookup token_id={token_id!r}"
            )

        # Inspect BOTH records independently before any early return
        grant_row = store.lookup_grant(token_id)

        grant_event = None
        for event in store.events():
            if (
                event["kind"] == "grant"
                and event["payload"].get("token_id") == token_id
            ):
                grant_event = event
                break

        # Neither present -> genuinely new request; proceed with execution
        if grant_row is None and grant_event is None:
            return None

        # One without the other -> inconsistent state; cannot auto-recover
        if grant_row is None and grant_event is not None:
            raise GrantReconciliationRequired(
                f"Grant event for token_id={token_id!r} exists without a "
                "corresponding grant row. Manual reconciliation required."
            )
        if grant_row is not None and grant_event is None:
            raise GrantReconciliationRequired(
                f"Grant row for token_id={token_id!r} exists without a "
                "corresponding grant event. "
                "_synchronize_checkpoint() cannot create missing events. "
                "Manual reconciliation required."
            )

        # Both present — canonical equality: submitted token vs stored token
        stored_token = grant_row["data"]
        if submitted_token != stored_token:
            differing = sorted(
                f
                for f in set(submitted_token) | set(stored_token)
                if submitted_token.get(f) != stored_token.get(f)
            )
            raise DuplicateKeyConflict(
                f"token_id reused with changed approval bindings: {differing}. "
                f"submitted={submitted_token!r}, stored={stored_token!r}"
            )

        # Verify event payload consistent with stored token
        event_payload = grant_event["payload"]
        if event_payload != stored_token:
            differing = sorted(
                f
                for f in set(event_payload) | set(stored_token)
                if event_payload.get(f) != stored_token.get(f)
            )
            raise GrantReconciliationRequired(
                f"Grant row and event are inconsistent: {differing}. "
                f"row={stored_token!r}, event={event_payload!r}"
            )

        engine._synchronize_checkpoint()
        return {
            "status": "already_complete",
            "source": "grant_event",
            "event_id": grant_event["event_id"],
        }

    # --- Non-approval deduplication via action_id in workflow_events.payload ---
    if action_id:
        for event in store.events():
            if event["payload"].get("action_id") == action_id:
                stored_hash = event["payload"].get("request_hash")
                if not stored_hash:
                    raise DuplicateKeyConflict(
                        "Stored event missing request_hash — rejecting"
                    )
                if stored_hash != request_hash:
                    raise DuplicateKeyConflict(
                        "action_id reused with different request contents"
                    )
                engine._synchronize_checkpoint()
                return {
                    "status": "already_complete",
                    "event_id": event["event_id"],
                }

    return None


def execute_action(root: Path, action: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    root = Path(root).resolve()
    runtime_path = root / "orchestrator/var"

    # Read-only display actions do not acquire execution.lock and do not construct Engine
    if action == "state":
        return get_state_projection(root)
    elif action == "plan":
        return get_plan_projection(root)

    lock_path = runtime_path / "execution.lock"

    with execution_lock(lock_path, timeout=10):
        # 1. Preflight check selection per mutating action
        if action in ("pause", "resume", "reset_budget", "reconfigure_role"):
            cfg = None
            if (runtime_path / "checkpoints.db").exists():
                conn = sqlite3.connect(f"file:{runtime_path / 'checkpoints.db'}?mode=ro", uri=True)
                try:
                    row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
                    if row:
                        cfg = json.loads(row[0])
                finally:
                    conn.close()
            checks = run_owner_action_checks(runtime_path, root, cfg)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Owner action preflight failed: {failed}")
        elif action == "initialize":
            proposed_branch = None
            if isinstance(payload.get("config"), dict):
                proposed_branch = payload["config"].get("branch")
            if not proposed_branch:
                proposed_branch = payload.get("branch")
            checks = run_init_checks(root, expected_branch=proposed_branch)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Init preflight failed: {failed}")
        elif action in ("run", "approve_plan", "adopt_scope"):
            cfg = None
            if (runtime_path / "checkpoints.db").exists():
                conn = sqlite3.connect(f"file:{runtime_path / 'checkpoints.db'}?mode=ro", uri=True)
                try:
                    row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
                    if row:
                        cfg = json.loads(row[0])
                finally:
                    conn.close()
            checks = run_dispatch_preflight(cfg, runtime_path, root)
            failed = [c for c in checks if not c.ok]
            if failed:
                raise PreconditionError(f"Dispatch preflight failed: {failed}")

        # 2. Initialize Engine for mutation
        engine = Engine(root)
        try:
            # 3. Deduplication under lock
            token_id = payload.get("token_id")
            submitted_token = payload.get("submitted_token") or payload.get("token")
            action_id = payload.get("action_id")
            request_hash = payload.get("request_hash", "")

            dedup = deduplicate_action(
                action_id=action_id,
                request_hash=request_hash,
                token_id=token_id,
                submitted_token=submitted_token,
                store=engine.store,
                engine=engine,
            )
            if dedup is not None:
                return dedup

            # 4. Dispatch action
            if action == "initialize":
                config = payload["config"]
                return engine.initialize(config)
            elif action == "run":
                return engine.run()
            elif action == "approve_plan":
                if not submitted_token:
                    raise CoreValidationError("approve_plan requires submitted_token or token in payload")
                return engine.approve(submitted_token)
            elif action == "adopt_scope":
                scope = payload["scope"]
                implementation_stages = payload["implementation_stages"]
                return engine.adopt_scope(
                    scope=scope,
                    implementation_stages=implementation_stages,
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "pause":
                reason = payload.get("reason", "Paused by operator")
                return engine.owner_decision(
                    "pause",
                    {"reason": reason},
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "resume":
                body = {
                    k: v
                    for k, v in payload.items()
                    if k not in ("action_id", "request_hash", "submitted_token", "token")
                }
                if "reason" not in body:
                    body["reason"] = "Resumed by operator"
                return engine.owner_decision(
                    "resume",
                    body,
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "reset_budget":
                return engine.owner_decision(
                    "resume",
                    {"reason": "reset_budget", "reset_budget": True},
                    action_id=action_id,
                    request_hash=request_hash,
                )
            elif action == "reconfigure_role":
                role = payload["role"]
                tool = payload["tool"]
                model = payload["model"]
                effort = payload.get("effort", None)
                reason = payload.get("reason", "Owner role reconfiguration")
                return engine.reconfigure_role(
                    role=role,
                    tool=tool,
                    model=model,
                    effort=effort,
                    reason=reason,
                    action_id=action_id,
                    request_hash=request_hash,
                )
            else:
                raise WorkflowError(f"Unknown action: {action}")
        finally:
            engine.close()


def main():
    parser = argparse.ArgumentParser(description="Dashboard Subprocess API")
    parser.add_argument("--root", type=Path, required=True, help="Worktree root directory")
    parser.add_argument("--action", type=str, required=True, help="Action to execute")
    parser.add_argument("--payload", type=str, default=None, help="JSON payload string")
    parser.add_argument("--payload-file", type=Path, default=None, help="JSON payload file")
    args = parser.parse_args()

    payload = {}
    if args.payload:
        payload = json.loads(args.payload)
    elif args.payload_file and args.payload_file.exists():
        payload = json.loads(args.payload_file.read_text())
    elif not sys.stdin.isatty():
        content = sys.stdin.read().strip()
        if content:
            payload = json.loads(content)

    try:
        res = execute_action(args.root, args.action, payload)
        output = {"ok": True, "result": res}
        print(json.dumps(output, default=str))
        sys.exit(0)
    except Exception as exc:
        err = sanitize_error(exc, args.root)
        output = {
            "ok": False,
            "error": err["error"],
            "error_type": err["error_type"],
            "support_id": err["support_id"],
        }
        print(json.dumps(output, default=str))
        sys.exit(1)


if __name__ == "__main__":
    main()
