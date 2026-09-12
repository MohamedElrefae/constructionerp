"""Native transport only: tools keep separate processes, sessions and reasoning."""

import json
import os
from pathlib import Path

from core import WorkflowError
from sandbox import command as sandbox_command

WIRE_SCHEMA = {
    "type": "object",
    "properties": {
        "result_json": {"type": "string"},
        "explanation": {"type": "string"},
        "plan_text": {"type": "string"},
    },
    "required": ["result_json", "explanation", "plan_text"],
    "additionalProperties": False,
}


def invocation(spec):
    tool, binary = spec["tool"], spec["binary"]
    prompt = spec["prompt"]
    env = os.environ.copy()
    # Agents receive no owner token, DB path override, or trace-export settings.
    for key in list(env):
        if key.startswith(("WORKFLOW_", "LANGSMITH_", "LANGCHAIN_")):
            env.pop(key)
    if tool == "codex":
        argv = [
            binary,
            "exec",
            "--ignore-user-config",
            "--sandbox",
            "workspace-write" if spec["role"] == "builder" else "read-only",
            "--cd",
            spec["root"],
            "--model",
            spec["model"],
            "--json",
            "--output-schema",
            spec["wire_schema"],
        ]
        if spec.get("probe"):
            argv += ["--skip-git-repo-check", "--ephemeral"]
        if spec.get("effort"):
            argv += ["-c", "model_reasoning_effort=" + json.dumps(spec["effort"])]
        argv += [prompt]
        writable = [Path.home() / ".codex"]
    elif tool == "opencode":
        permissions = {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow"}
        if spec["role"] == "builder":
            permissions.update(bash="allow", edit="allow")
        elif spec["role"] == "proposer":
            permissions.update(edit="allow")
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(
            {"permission": permissions, "share": "disabled", "autoupdate": False}
        )
        argv = [
            binary,
            "--pure",
            "run",
            "--format",
            "json",
            "--dir",
            spec["root"],
            "--model",
            spec["model"],
            prompt,
        ]
        writable = [
            Path.home() / ".local/share/opencode",
            Path.home() / ".cache/opencode",
            Path.home() / ".local/state/opencode",
        ]
    elif tool == "antigravity":
        raise WorkflowError("agy adapter disabled until its installed version passes a probe")
    else:
        raise WorkflowError("Unknown native tool")
    read_files = [spec["wire_schema"], *spec.get("read_artifacts", [])]
    hidden = [spec.get("control_root", str(Path(spec["runtime"]).parents[1])), spec["work_item_root"]]
    if spec.get("private_root"):
        hidden.append(spec["private_root"])
    return sandbox_command(
        argv,
        spec["root"],
        spec["work_item_root"],
        writable,
        hidden_roots=hidden,
        read_files=read_files,
        writable_source=spec["role"] == "builder",
        neutral_mounts=spec.get("neutral_mounts", ()),
    ), env


def session_from(event, tool):
    if tool == "codex" and event.get("type") == "thread.started":
        return event.get("thread_id")
    if tool == "opencode":
        return event.get("sessionID")
    return None


def parse_output(text, tool):
    session, messages, events = None, [], []
    message_ids = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        events.append(event)
        session = session or session_from(event, tool)
        if (
            tool == "codex"
            and event.get("type") == "item.completed"
            and event.get("item", {}).get("type") == "agent_message"
        ):
            messages.append(event["item"].get("text", ""))
        elif tool == "opencode" and event.get("type") == "text":
            part = event.get("part", {})
            messages.append(part.get("text", ""))
            message_ids.append(part.get("messageID"))
    if not session or not messages:
        raise WorkflowError("MALFORMED_RESULT: missing native identity or final message")
    try:
        final = messages[-1]
        if tool == "opencode":
            if all(message_ids):
                groups = []
                for identity, fragment in zip(message_ids, messages, strict=True):
                    if groups and groups[-1][0] == identity:
                        groups[-1][1] += fragment
                    else:
                        if any(g[0] == identity for g in groups):
                            raise ValueError("interleaved messages")
                        groups.append([identity, fragment])
                candidates = [g[1] for g in groups]
            else:
                # Metadata-free traces must contain a complete final text event.
                candidates = messages
            for earlier in candidates[:-1]:
                if earlier.lstrip().startswith(("{", "[")):
                    raise ValueError("ambiguous result messages")
            final = candidates[-1]
        wire = json.loads(final)
        if set(wire) != {"result_json", "explanation", "plan_text"}:
            raise ValueError("wire fields")
        if not all(isinstance(wire[k], str) for k in wire):
            raise ValueError("wire values must be strings")
        body = json.loads(wire["result_json"])
        if not isinstance(body, dict):
            raise ValueError("result must be an object")
    except (ValueError, TypeError) as exc:
        raise WorkflowError("MALFORMED_RESULT: invalid wire envelope") from exc
    return session, body, wire, events


def classify_failure(text, timeout=False):
    if timeout:
        return "TIMEOUT"
    text = text.lower()
    if any(
        s in text
        for s in (
            "unauthorized",
            "authentication",
            "not logged in",
            "login required",
            "invalid api key",
            "401",
        )
    ):
        return "AUTH_FAILURE"
    if any(
        s in text for s in ("permission denied", "denied action", "read-only file system", "access denied")
    ):
        return "DENIED_ACTION"
    return "MALFORMED_RESULT"
