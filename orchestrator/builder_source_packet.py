"""Bounded source context and local return conversion for T3 builder jobs.

The model sees only source files selected by the prepared job's explicit
allowed paths. It returns changed UTF-8 text; the coordinator computes every
hash and base64 encoding locally before existing artifact validation runs.
"""

import base64
import errno
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

from core import WorkflowError

SOURCE_PACKET_SCHEMA = "engine-builder-source-packet/v1"
MAX_SOURCE_FILES = 32
MAX_SOURCE_FILE_BYTES = 12_000
MAX_SOURCE_TOTAL_BYTES = 48_000
MAX_RETURN_FILES = 8
MAX_RETURN_FILE_BYTES = 12_000
MAX_RETURN_TOTAL_BYTES = 24_000
MAX_RETURN_JSON_CHARS = 50_000
_HEX = re.compile(r"^[0-9a-f]{64}$")
_BLOCKED_PARTS = {
    ".git",
    ".codex",
    ".agents",
    "private",
    "secrets",
    "credentials",
    "orchestrator/var",
    "state.json",
    "checkpoints.db",
    "launch_policy.json",
    "approval.json",
    "approvals",
    "owner-approval",
    "owner_approval",
    "dispatch-ledger.sqlite3",
    "dispatch-ledger.db",
}
_CREDENTIAL_NAME = re.compile(
    r"(?:^|[._-])(secret|credential|password|token|private[-_]?key)(?:$|[._-])", re.I
)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _relative(value):
    if not isinstance(value, str) or not value or len(value) > 240 or "\\" in value or "\x00" in value:
        raise WorkflowError("Invalid builder source path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(part in ("", ".", "..") for part in value.split("/"))
        or path.as_posix() != value
    ):
        raise WorkflowError("Builder source path must be normalized and relative")
    if _sensitive_path(value):
        raise WorkflowError("Git, control, and credential paths are excluded from builder source packets")
    return value


def _sensitive_path(value):
    parts = value.split("/")
    if any(part.startswith(".") for part in parts):
        return True
    lowered = value.lower()
    return (
        any(part.lower() in _BLOCKED_PARTS for part in parts)
        or "orchestrator/var" in lowered
        or any(part.lower().endswith((".pem", ".key")) for part in parts)
        or any(_CREDENTIAL_NAME.search(part) is not None for part in parts)
    )


def _allowed(path, allowed_paths):
    return any(
        path == prefix or (prefix.endswith("/") and path.startswith(prefix)) for prefix in allowed_paths
    )


def _walk_allowed(root, allowed_paths):
    """Yield regular source files without following symlinked directories."""
    found = set()
    for prefix in allowed_paths:
        path = _relative(prefix[:-1] if prefix.endswith("/") else prefix)
        target = root.joinpath(*path.split("/"))
        if prefix.endswith("/"):
            if target.is_symlink():
                raise WorkflowError("Symlink in builder allowed source path: " + prefix)
            if not target.exists() or not target.is_dir():
                continue
            for current, dirs, files in os.walk(target, followlinks=False):
                current_path = Path(current)
                rel_parent = current_path.relative_to(root).as_posix()
                kept_dirs = []
                for name in sorted(dirs):
                    if _sensitive_path(rel_parent + "/" + name):
                        continue
                    if (current_path / name).is_symlink():
                        raise WorkflowError(
                            "Symlink in builder source directory: "
                            + (current_path / name).relative_to(root).as_posix()
                        )
                    kept_dirs.append(name)
                dirs[:] = kept_dirs
                for name in sorted(files):
                    file_path = current_path / name
                    if file_path.is_symlink():
                        raise WorkflowError(
                            "Symlink in builder source directory: " + file_path.relative_to(root).as_posix()
                        )
                    if not file_path.is_file():
                        continue
                    relative = file_path.relative_to(root).as_posix()
                    if not _sensitive_path(relative):
                        found.add(relative)
        else:
            if target.is_symlink():
                raise WorkflowError("Symlink in builder allowed source path: " + path)
            if target.exists() and target.is_file():
                found.add(path)
    return sorted(found)


def _read_source_file(root, relative_path, max_file_bytes):
    """Read a regular file through no-follow descriptors for every component."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise WorkflowError("Safe no-follow source access is unavailable")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        parts = relative_path.split("/")
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            if index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            try:
                next_fd = os.open(part, flags, dir_fd=fd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise WorkflowError(
                        "Symlink or non-directory in builder source path: " + relative_path
                    ) from None
                raise WorkflowError("Builder source path cannot be opened: " + relative_path) from exc
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_file_bytes:
            raise WorkflowError("Builder source file exceeds regular-file size limits: " + relative_path)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(max_file_bytes + 1)
        if len(data) > max_file_bytes:
            raise WorkflowError("Builder source file exceeds regular-file size limits: " + relative_path)
        return data
    finally:
        os.close(fd)


def build_builder_source_packet(
    source_root,
    allowed_paths,
    *,
    max_files=MAX_SOURCE_FILES,
    max_file_bytes=MAX_SOURCE_FILE_BYTES,
    max_total_bytes=MAX_SOURCE_TOTAL_BYTES,
):
    """Capture bounded UTF-8 files and their base hashes for one builder job."""
    root = Path(source_root).resolve(strict=True)
    if not root.is_dir():
        raise WorkflowError("Builder source root must be a directory")
    if not isinstance(allowed_paths, list | tuple) or not allowed_paths:
        raise WorkflowError("Builder source packet requires explicit allowed paths")
    normalized = []
    for item in allowed_paths:
        if not isinstance(item, str) or not item:
            raise WorkflowError("Invalid builder allowed path")
        is_prefix = item.endswith("/")
        normalized.append(_relative(item[:-1] if is_prefix else item) + ("/" if is_prefix else ""))
    paths = _walk_allowed(root, normalized)
    # A specifically named, absent path is an authorized new file. Do not
    # infer arbitrary new names from directory-prefix scopes.
    from builder_intake import _source_state

    new_paths = []
    for path in normalized:
        if path.endswith("/") or path in paths or path in new_paths:
            continue
        exists, _ = _source_state(root, path)
        if exists:
            raise WorkflowError("Builder source is not a readable regular file: " + path)
        new_paths.append(path)
    if len(paths) + len(new_paths) > max_files:
        raise WorkflowError("Builder source packet exceeds file count limit")
    result = []
    total = 0
    for path in paths:
        if not _allowed(path, normalized):
            continue
        try:
            data = _read_source_file(root, path, max_file_bytes)
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkflowError("Builder source file is not UTF-8 text: " + path) from exc
        except OSError as exc:
            raise WorkflowError("Builder source file cannot be read: " + path) from exc
        # T3 transport redacts host paths from prompts. A rewritten source
        # packet would make the model edit different bytes from the captured
        # baseline, so refuse instead of silently changing source context.
        from t3_transport import redact_host_paths

        if redact_host_paths(content) != content:
            raise WorkflowError("Builder source would be altered by transport redaction: " + path)
        total += len(data)
        if total > max_total_bytes:
            raise WorkflowError("Builder source packet exceeds total size limit")
        result.append({"path": path, "base_sha256": _sha(data), "content": content})
    result.extend({"path": path, "base_sha256": None, "content": None} for path in new_paths)
    if not result:
        raise WorkflowError("Builder source packet has no readable files in allowed paths")
    return {"schema": SOURCE_PACKET_SCHEMA, "files": result}


def builder_output_instructions(job):
    """Return exact instructions for the model's hash-free file response."""
    if not isinstance(job, dict) or not isinstance(job.get("spec"), dict):
        raise WorkflowError("Builder output instructions require a prepared job")
    envelope = job["spec"].get("envelope")
    if not isinstance(envelope, dict) or job.get("role") != "builder":
        raise WorkflowError("Builder output instructions require a builder job")
    return (
        "\nBUILDER FILE RETURN CONTRACT:\n"
        "Return the existing result wire with exactly its normal string fields: "
        "result_json, explanation, plan_text, and builder_bundle_json. Set "
        "builder_bundle_json to compact JSON of this form: "
        '{"files":[{"path":"relative/path","content":"complete UTF-8 file text"}]}. '
        "Include only complete changed files from the supplied source packet; a null content "
        "and base hash marks an explicitly authorized new file. Do not emit "
        "hashes, base64, diffs, markdown fences, or additional fields; the runner computes "
        "hashes and encodings. Paths must exactly match files in that packet. Return at most "
        "8 files, 12000 UTF-8 bytes per file and 24000 bytes total. Keep the entire "
        "response under 50000 characters. If no safe change can be made, "
        "use a schema-valid BLOCKED result: status COMPLETE, verdict BLOCKED, "
        "failure_class null, and at least one blocking finding with the affected "
        "requirement ID and a concise explanation; do not invent evidence. Return "
        "one unchanged file from the source packet. Bind result_json to job "
        f"{envelope.get('job_id')}, candidate {envelope.get('candidate_id')}, and plan "
        f"{envelope.get('plan_revision_hash')}.\n"
    )


def build_bound_builder_bundle(files_json, job, source_packet):
    """Convert model file text into the existing hash-bound bundle format.

    ``source_packet`` must be the exact immutable packet captured for this job.
    Only paths in that packet can be returned, which keeps this compact output
    contract focused on modifications to supplied files.
    """
    if not isinstance(files_json, str) or not files_json or len(files_json) > MAX_RETURN_JSON_CHARS:
        raise WorkflowError("Builder file return is missing or exceeds text bound")
    try:
        returned = json.loads(files_json)
    except (TypeError, ValueError) as exc:
        raise WorkflowError("Builder file return JSON is malformed") from exc
    if not isinstance(returned, dict) or set(returned) != {"files"}:
        raise WorkflowError("Builder file return has an invalid shape")
    files = returned["files"]
    if not isinstance(files, list) or not files or len(files) > MAX_RETURN_FILES:
        raise WorkflowError("Builder returned file count outside bounds")
    if not isinstance(source_packet, dict) or source_packet.get("schema") != SOURCE_PACKET_SCHEMA:
        raise WorkflowError("Builder source packet is missing or unsupported")
    source_files = source_packet.get("files")
    if not isinstance(source_files, list):
        raise WorkflowError("Builder source packet has an invalid file list")
    bases = {}
    for item in source_files:
        if not isinstance(item, dict) or set(item) != {"path", "base_sha256", "content"}:
            raise WorkflowError("Builder source packet entry is malformed")
        path = _relative(item["path"])
        absent = item["content"] is None and item["base_sha256"] is None
        valid_existing = (
            isinstance(item["content"], str)
            and isinstance(item["base_sha256"], str)
            and _HEX.fullmatch(item["base_sha256"]) is not None
            and _sha(item["content"].encode("utf-8")) == item["base_sha256"]
        )
        if (not absent and not valid_existing) or path in bases:
            raise WorkflowError("Builder source packet hash mismatch or duplicate path: " + path)
        bases[path] = item["base_sha256"]
    if not isinstance(job, dict) or job.get("role") != "builder":
        raise WorkflowError("Builder file return requires a builder job")
    envelope = job.get("spec", {}).get("envelope") if isinstance(job.get("spec"), dict) else None
    if not isinstance(envelope, dict):
        raise WorkflowError("Builder job envelope is missing")

    bound = []
    seen = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            raise WorkflowError("Builder returned file entry has an invalid shape")
        path = _relative(item["path"])
        if path in seen:
            raise WorkflowError("Builder returned a duplicate path: " + path)
        seen.add(path)
        if path not in bases:
            raise WorkflowError("Builder returned a path absent from source packet: " + path)
        if not isinstance(item["content"], str):
            raise WorkflowError("Builder returned content must be UTF-8 text: " + path)
        content = item["content"].encode("utf-8")
        if len(content) > MAX_RETURN_FILE_BYTES:
            raise WorkflowError("Builder returned file exceeds size bound: " + path)
        total += len(content)
        if total > MAX_RETURN_TOTAL_BYTES:
            raise WorkflowError("Builder returned files exceed total size bound")
        bound.append(
            {
                "path": path,
                "base_sha256": bases[path],
                "content_base64": base64.b64encode(content).decode("ascii"),
                "content_sha256": _sha(content),
            }
        )
    bundle = {
        "schema": "engine-builder-bundle/v1",
        "job_id": envelope.get("job_id"),
        "candidate_id": envelope.get("candidate_id"),
        "plan_revision_hash": envelope.get("plan_revision_hash"),
        "files": bound,
        "bundle_sha256": _sha(
            json.dumps(bound, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ),
    }
    encoded = json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded) > MAX_RETURN_JSON_CHARS:
        raise WorkflowError("Converted builder bundle exceeds text bound")
    return encoded


def normalize_builder_artifact_wire(assistant_text, job, source_packet):
    """Replace the model's hash-free file return with the existing bound bundle.

    The outer T3 wire and its ``builder_bundle_json`` key remain unchanged, so
    callers can pass the returned text through the existing strict result
    decoder and artifact intake without teaching the model to calculate hashes.
    """
    if not isinstance(assistant_text, str) or len(assistant_text) > 50_000:
        raise WorkflowError("T3 builder response exceeds result text bound")
    from t3_result import BUILDER_BUNDLE_KEY

    marker = "ENGINE-T3-RESULT " + str(job.get("job_id", ""))
    if marker not in assistant_text:
        raise WorkflowError("T3 builder result marker is missing")
    decoder = json.JSONDecoder()
    offset = 0
    wire = None
    while True:
        offset = assistant_text.find("{", offset)
        if offset < 0:
            break
        try:
            value, end = decoder.raw_decode(assistant_text, offset)
        except ValueError:
            offset += 1
            continue
        offset = end
        if (
            isinstance(value, dict)
            and set(value) == {"result_json", "explanation", "plan_text", BUILDER_BUNDLE_KEY}
            and all(
                isinstance(value.get(key), str)
                for key in ("result_json", "explanation", "plan_text", BUILDER_BUNDLE_KEY)
            )
        ):
            wire = value
            break
    if wire is None:
        raise WorkflowError("T3 builder response has no complete artifact result wire")
    wire[BUILDER_BUNDLE_KEY] = build_bound_builder_bundle(wire[BUILDER_BUNDLE_KEY], job, source_packet)
    return marker + "\n" + json.dumps(wire, separators=(",", ":"), ensure_ascii=False)
