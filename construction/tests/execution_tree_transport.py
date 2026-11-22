"""Bound HTTP transport harness for the Stage 1 execution tree.

Usage:
    python -m construction.tests.execution_tree_transport --binding <private-binding-path>

With only ``--binding`` the harness runs the fixed acceptance case catalog. The
binding is supplied privately at runtime. Credentials are read from the
environment variable named by the binding and are never printed.

The catalog is fixed: caller-supplied URLs or shell commands are never
executed. Dedicated RPC cases cover the six methods; a separate fixed generic
route catalog covers generic/share/lifecycle closure, post-commit revocation
and restoration, installed permission-metadata inventory and session cleanup.
Unsupported-profile metadata vectors are asserted by the offline suite and the
native module; this harness does not install forbidden customizations.

Transport execution is disabled until runtime binding, persisted-state observation,
and same-session two-worker revocation verification are implemented and
independently reviewed. Declared identities alone cannot authorize a run.
``verify_runtime_binding`` composes the existing checks into a point-in-time
proof; it deliberately does not enable transport.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path

_ALLOWED_METHODS = {
    "get_tree": "GET",
    "create_node": "POST",
    "update_node": "POST",
    "move_node": "POST",
    "set_disabled": "POST",
    "delete_node": "POST",
}
ALLOWED_METHODS = frozenset(_ALLOWED_METHODS)
ALLOWED_FIXTURES = frozenset(
    {
        "allowed_engineer",
        "allowed_manager",
        "system_manager",
        "project_outsider",
        "measurement_only",
        "administrator",
    }
)
ALLOWED_PHASES = frozenset({"fresh", "upgrade", "fixture"})
REQUIRED_BINDING_KEYS = frozenset(
    {
        "bench_root",
        "sites_path",
        "app_root",
        "site",
        "http_endpoint",
        "db_name",
        "db_socket",
        "redis_origin",
        "phase",
        "evidence_root",
        "project",
        "other_project",
        "other_company",
        "candidate_id",
        "candidate_manifest_path",
        "dependency_identities",
        "serving_process_identities",
        "serving_process_records",
        "fixtures",
        "credentials_env",
        "expected_manifest_path",
    }
)
# Identity keys the independently supplied expected manifest must bind. The
# binding cannot create its own expectation for any of these values.
EXPECTED_IDENTITY_KEYS = (
    "candidate_id",
    "dependency_identities",
    "serving_process_identities",
    "serving_process_records",
    "site",
    "http_endpoint",
    "bench_root",
    "sites_path",
    "app_root",
    "db_name",
    "db_socket",
    "redis_origin",
    "phase",
)

# Fixed acceptance catalog. Expected outcomes are specified here, not inferred
# from the response. ``$node`` values are captured from a successful create.
ACCEPTANCE_CASES = (
    {
        "name": "read_allowed_engineer",
        "fixture": "allowed_engineer",
        "method": "get_tree",
        "payload": {},
        "expect": "allow",
    },
    {
        "name": "read_denied_outsider",
        "fixture": "project_outsider",
        "method": "get_tree",
        "payload": {},
        "expect": "deny",
    },
    {
        "name": "read_denied_measurement_only",
        "fixture": "measurement_only",
        "method": "get_tree",
        "payload": {},
        "expect": "deny",
    },
    {
        "name": "create_denied_engineer",
        "fixture": "allowed_engineer",
        "method": "create_node",
        "payload": {"title": "Harness engineer denied", "is_group": True},
        "expect": "deny",
    },
    {
        "name": "create_denied_outsider",
        "fixture": "project_outsider",
        "method": "create_node",
        "payload": {"title": "Harness outsider denied", "is_group": False},
        "expect": "deny",
    },
    {
        "name": "create_allowed_manager",
        "fixture": "allowed_manager",
        "method": "create_node",
        "payload": {"title": "Harness root", "is_group": True},
        "expect": "allow",
        "capture": "node",
    },
    {
        "name": "create_child_allowed_manager",
        "fixture": "allowed_manager",
        "method": "create_node",
        "payload": {
            "title": "Harness child",
            "is_group": False,
            "parent_node": "$node",
            "expected_parent_modified": "$node_modified",
        },
        "expect": "allow",
        "capture": "child",
    },
    {
        "name": "update_denied_engineer",
        "fixture": "allowed_engineer",
        "method": "update_node",
        "payload": {"name": "$node", "expected_modified": "$node_modified", "title": "Denied"},
        "expect": "deny",
    },
    {
        "name": "update_allowed_manager",
        "fixture": "allowed_manager",
        "method": "update_node",
        "payload": {
            "name": "$node",
            "expected_modified": "$node_modified",
            "title": "Harness root updated",
        },
        "expect": "allow",
    },
    {
        "name": "update_stale_version_denied",
        "fixture": "allowed_manager",
        "method": "update_node",
        "payload": {
            "name": "$node",
            "expected_modified": "$stale_modified",
            "title": "Stale write",
        },
        "expect": "deny",
    },
    {
        "name": "move_denied_engineer",
        "fixture": "allowed_engineer",
        "method": "move_node",
        "payload": {"name": "$child", "expected_modified": "$child_modified", "parent_node": None},
        "expect": "deny",
    },
    {
        "name": "move_to_non_group_denied",
        "fixture": "allowed_manager",
        "method": "move_node",
        "payload": {
            "name": "$node",
            "expected_modified": "$node_modified",
            "parent_node": "$child",
            "expected_parent_modified": "$child_modified",
        },
        "expect": "deny",
    },
    {
        "name": "move_to_root_allowed_manager",
        "fixture": "allowed_manager",
        "method": "move_node",
        "payload": {
            "name": "$child",
            "expected_modified": "$child_modified",
            "parent_node": None,
        },
        "expect": "allow",
    },
    {
        "name": "set_disabled_denied_engineer",
        "fixture": "allowed_engineer",
        "method": "set_disabled",
        "payload": {"name": "$child", "expected_modified": "$child_modified", "disabled": True},
        "expect": "deny",
    },
    {
        "name": "set_disabled_allowed_manager",
        "fixture": "allowed_manager",
        "method": "set_disabled",
        "payload": {"name": "$child", "expected_modified": "$child_modified", "disabled": True},
        "expect": "allow",
    },
    {
        "name": "delete_denied_engineer",
        "fixture": "allowed_engineer",
        "method": "delete_node",
        "payload": {"name": "$child", "expected_modified": "$child_modified"},
        "expect": "deny",
    },
    {
        "name": "delete_denied_manager",
        "fixture": "allowed_manager",
        "method": "delete_node",
        "payload": {"name": "$child", "expected_modified": "$child_modified"},
        "expect": "deny",
    },
    {
        "name": "delete_allowed_system_manager",
        "fixture": "system_manager",
        "method": "delete_node",
        "payload": {"name": "$child", "expected_modified": "$child_modified"},
        "expect": "allow",
    },
    {
        "name": "create_after_denial_allocates_next_code",
        "fixture": "allowed_manager",
        "method": "create_node",
        "payload": {"title": "Continuity probe", "is_group": False},
        "expect": "allow",
        "capture": "probe",
    },
    {
        "name": "delete_probe_allowed_system_manager",
        "fixture": "system_manager",
        "method": "delete_node",
        "payload": {"name": "$probe", "expected_modified": "$probe_modified"},
        "expect": "allow",
    },
    {
        "name": "cross_project_parent_setup",
        "fixture": "allowed_manager",
        "method": "create_node",
        "payload": {"project": "$other_project", "title": "Other project root", "is_group": True},
        "expect": "allow",
        "capture": "other_node",
    },
    {
        "name": "cross_project_parent_denied",
        "fixture": "allowed_manager",
        "method": "create_node",
        "payload": {
            "title": "Foreign parent",
            "is_group": False,
            "parent_node": "$other_node",
            "expected_parent_modified": "$other_node_modified",
        },
        "expect": "deny",
    },
    {
        "name": "unknown_argument_denied",
        "fixture": "allowed_manager",
        "method": "get_tree",
        "payload": {"unexpected": "x"},
        "expect": "error",
    },
    {
        "name": "read_allowed_administrator",
        "fixture": "administrator",
        "method": "get_tree",
        "payload": {},
        "expect": "allow",
    },
)

# Fixed generic-route catalog. These routes are reviewed constants, never
# caller-supplied URLs. They assert generic/share/lifecycle closure, a real
# post-commit revocation and restoration through committed authority rows,
# installed permission-metadata inventory and session cleanup.
GENERIC_CASES = (
    {
        "name": "generic_list_denied_engineer",
        "fixture": "allowed_engineer",
        "http_method": "GET",
        "path": "/api/resource/Execution Breakdown Node",
        "expect": "deny",
    },
    {
        "name": "generic_read_denied_outsider",
        "fixture": "project_outsider",
        "http_method": "GET",
        "path": "/api/resource/Execution Breakdown Node/$node",
        "expect": "deny",
    },
    {
        "name": "generic_create_denied_manager",
        "fixture": "allowed_manager",
        "http_method": "POST",
        "path": "/api/resource/Execution Breakdown Node",
        "payload": {"doctype": "Execution Breakdown Node", "project": "$project", "title": "Generic"},
        "expect": "deny",
    },
    {
        "name": "generic_update_denied_manager",
        "fixture": "allowed_manager",
        "http_method": "PUT",
        "path": "/api/resource/Execution Breakdown Node/$node",
        "payload": {"title": "Generic update"},
        "expect": "deny",
    },
    {
        "name": "generic_delete_denied_system_manager",
        "fixture": "system_manager",
        "http_method": "DELETE",
        "path": "/api/resource/Execution Breakdown Node/$node",
        "expect": "deny",
    },
    {
        "name": "counter_list_denied_system_manager",
        "fixture": "system_manager",
        "http_method": "GET",
        "path": "/api/resource/Execution Code Counter",
        "expect": "deny",
    },
    {
        "name": "protected_share_denied_manager",
        "fixture": "allowed_manager",
        "http_method": "POST",
        "path": "/api/method/frappe.share.add",
        "payload": {
            "doctype": "Execution Breakdown Node",
            "name": "$node",
            "user": "$outsider",
            "read": 1,
        },
        "expect": "deny",
    },
    {
        "name": "company_change_denied_after_issue",
        "fixture": "allowed_manager",
        "http_method": "POST",
        "path": "/api/method/frappe.client.set_value",
        "payload": {
            "doctype": "Project",
            "name": "$project",
            "fieldname": "company",
            "value": "$other_company",
        },
        "expect": "deny",
    },
    {
        "name": "stock_docperm_inventory_empty",
        "fixture": "administrator",
        "http_method": "GET",
        "path": "/api/method/frappe.client.get_list",
        "payload": {
            "doctype": "DocPerm",
            "filters": json.dumps({"parent": "Execution Breakdown Node"}),
            "fields": json.dumps(["name"]),
        },
        "expect": "allow",
        "expect_empty": True,
    },
    {
        "name": "custom_docperm_inventory_empty",
        "fixture": "administrator",
        "http_method": "GET",
        "path": "/api/method/frappe.client.get_list",
        "payload": {
            "doctype": "Custom DocPerm",
            "filters": json.dumps({"parent": "Execution Breakdown Node"}),
            "fields": json.dumps(["name"]),
        },
        "expect": "allow",
        "expect_empty": True,
    },
    {
        "name": "revocation_insert_user_permission",
        "fixture": "administrator",
        "http_method": "POST",
        "path": "/api/method/frappe.client.insert",
        "payload": {
            "doc": {
                "doctype": "User Permission",
                "user": "$engineer",
                "allow": "Company",
                "for_value": "$other_company",
            }
        },
        "expect": "allow",
        "capture": "restriction",
    },
    {
        "name": "read_denied_after_revocation",
        "fixture": "allowed_engineer",
        "method": "get_tree",
        "payload": {},
        "expect": "deny",
    },
    {
        "name": "manager_unaffected_by_engineer_revocation",
        "fixture": "allowed_manager",
        "method": "create_node",
        "payload": {"title": "Revocation isolation probe", "is_group": False},
        "expect": "allow",
        "capture": "isolation_probe",
    },
    {
        "name": "delete_isolation_probe_allowed_system_manager",
        "fixture": "system_manager",
        "method": "delete_node",
        "payload": {"name": "$isolation_probe", "expected_modified": "$isolation_probe_modified"},
        "expect": "allow",
    },
    {
        "name": "revocation_remove_user_permission",
        "fixture": "administrator",
        "http_method": "POST",
        "path": "/api/method/frappe.client.delete",
        "payload": {"doctype": "User Permission", "name": "$restriction"},
        "expect": "allow",
    },
    {
        "name": "read_restored_after_cleanup",
        "fixture": "allowed_engineer",
        "method": "get_tree",
        "payload": {},
        "expect": "allow",
    },
    {
        "name": "logout_cleanup",
        "fixture": "allowed_engineer",
        "http_method": "POST",
        "path": "/api/method/logout",
        "expect": "allow",
    },
)


class BindingError(RuntimeError):
    pass


_TRANSPORT_DISABLED = (
    "Transport execution disabled: runtime identity and acceptance evidence are not verified"
)


def _require_verified_runtime():
    raise BindingError(_TRANSPORT_DISABLED)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _verify_candidate_files(app_root, manifest, expected_id):
    """Verify listed candidate files only; this does not attest a running site.

    The caller must obtain expected_id from an independently approved binding.
    A successful result does not establish the base tree, loaded modules,
    endpoint or worker identity and does not enable transport.
    """
    if not isinstance(manifest, dict) or manifest.get("kind") != "code":
        raise BindingError("Invalid candidate manifest.")
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    if not isinstance(expected_id, str) or hashlib.sha256(canonical).hexdigest() != expected_id:
        raise BindingError("Candidate manifest identity mismatch.")
    root = Path(app_root)
    if not root.is_absolute() or not root.is_dir() or root.resolve() != root:
        raise BindingError("Candidate root must be a resolved directory.")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise BindingError("Candidate manifest has no files.")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("kind") != "file":
            raise BindingError("Unsupported candidate entry.")
        name = entry.get("path")
        mode = entry.get("mode")
        if not isinstance(name, str) or not name or name.startswith("/") or "\\" in name:
            raise BindingError("Invalid candidate path.")
        parts = name.split("/")
        if any(part in ("", ".", "..") for part in parts) or name in seen:
            raise BindingError("Invalid or duplicate candidate path.")
        if mode not in ("100644", "100755"):
            raise BindingError("Unsupported candidate file mode.")
        seen.add(name)
        target = root
        for part in parts:
            target = target / part
            if target.is_symlink():
                raise BindingError("Candidate path contains a symlink.")
        if not target.is_file():
            raise BindingError("Candidate file is missing.")
        actual_mode = "100755" if target.stat().st_mode & 0o111 else "100644"
        if actual_mode != mode or hashlib.sha256(target.read_bytes()).hexdigest() != entry.get(
            "content_sha256"
        ):
            raise BindingError("Candidate file content or mode mismatch.")
    return {"candidate_id": expected_id, "verified_files": len(seen)}


def _verify_candidate_checkout(app_root, manifest, expected_id):
    """Check base HEAD and require a checkout free of ignored artifacts.

    This deliberately strict preflight rejects ignored files rather than
    deciding which generated artifacts are safe. It does not inspect Git's
    internal directory, loaded modules, workers, endpoints, or subsequent
    filesystem changes. Its result does not authorize transport.
    """
    result = _verify_candidate_files(app_root, manifest, expected_id)
    base = manifest.get("base_commit")
    if not isinstance(base, str) or len(base) != 40 or any(c not in "0123456789abcdef" for c in base):
        raise BindingError("Invalid candidate base commit.")
    root = Path(app_root)
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})

    def git(*args):
        try:
            return subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "-c",
                    "core.fsmonitor=false",
                    "-c",
                    "core.hooksPath=/dev/null",
                    *args,
                ],
                env=env,
                check=True,
                capture_output=True,
                timeout=30,
            ).stdout
        except (OSError, subprocess.SubprocessError) as error:
            raise BindingError("Unable to verify candidate checkout.") from error

    if Path(os.fsdecode(git("rev-parse", "--show-toplevel").strip())).resolve() != root:
        raise BindingError("Candidate root is not the repository root.")
    if git("rev-parse", "HEAD").strip().decode("ascii") != base:
        raise BindingError("Candidate base HEAD mismatch.")
    if git("ls-files", "--others", "--ignored", "--exclude-standard", "-z"):
        raise BindingError("Ignored checkout artifacts are not permitted.")
    if git("diff", "--cached", "--no-ext-diff", "--no-textconv", "--name-only", "-z", base, "--"):
        raise BindingError("Staged changes are not permitted during checkout verification.")
    for record in git("ls-files", "-v", "-z").split(b"\0"):
        if record and (record[:1].islower() or record[:1] == b"S"):
            raise BindingError("Checkout has assume-unchanged or skip-worktree index entries.")
    expected = {entry["path"] for entry in manifest["entries"]}
    # Git diff can trust index flags/stat data. Compare each non-candidate base
    # blob directly against the working file rather than trusting that index.
    for record in git("ls-tree", "-r", "-z", "--full-tree", base).split(b"\0"):
        if not record:
            continue
        try:
            meta, raw_path = record.split(b"\t", 1)
            mode, kind, object_id = meta.split(b" ")
            name = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise BindingError("Unsupported base-tree entry.") from error
        if name in expected:
            continue
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise BindingError("Unsupported non-candidate base-tree entry.")
        path = root
        for part in name.split("/"):
            path = path / part
            if path.is_symlink():
                raise BindingError("Non-candidate base path contains a symlink.")
        if not path.is_file():
            raise BindingError("Non-candidate base file is missing.")
        data = path.read_bytes()
        actual_mode = b"100755" if path.stat().st_mode & 0o111 else b"100644"
        blob_id = (
            hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest().encode("ascii")
        )
        if actual_mode != mode or blob_id != object_id:
            raise BindingError("Non-candidate base file differs from the recorded base.")
    tracked = git("diff", "--no-ext-diff", "--no-textconv", "--name-only", "-z", base, "--")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z")
    try:
        observed = {entry.decode("utf-8") for entry in (tracked + untracked).split(b"\0") if entry}
    except UnicodeDecodeError as error:
        raise BindingError("Candidate paths are not UTF-8.") from error
    if observed != expected:
        raise BindingError("Checkout changes differ from candidate manifest.")
    # Detect ordinary drift during the Git inspection; continuous protection
    # against later replacement is a separate runtime-verification requirement.
    _verify_candidate_files(app_root, manifest, expected_id)
    return {
        **result,
        "base_commit": base,
        "nonignored_change_set_verified": True,
        "ignored_artifacts_absent": True,
    }


def _verify_worker_process_records(proc_root, expected_workers):
    """Compare process metadata and socket descriptors against expected records.

    The records and proc_root must ultimately come from a separately trusted
    lab binding. This check does not establish HTTP routing, listening state,
    loaded code, database identity, or continued identity after this check.
    A caller-provided proc_root is supported for offline tests only; this
    function alone cannot grant permission to use transport.
    """
    if not isinstance(expected_workers, list) or len(expected_workers) != 2:
        raise BindingError("Two worker records are required.")
    seen = set()
    for worker in expected_workers:
        if not isinstance(worker, dict):
            raise BindingError("Invalid worker record.")
        pid, start, inode = worker.get("pid"), worker.get("start_ticks"), worker.get("socket_inode")
        exe, cwd = worker.get("exe"), worker.get("cwd")
        if (
            type(pid) is not int
            or pid <= 0
            or pid in seen
            or type(start) is not int
            or start <= 0
            or type(inode) is not int
            or inode <= 0
            or not isinstance(exe, str)
            or not os.path.isabs(exe)
            or not isinstance(cwd, str)
            or not os.path.isabs(cwd)
        ):
            raise BindingError("Invalid worker identity.")
        seen.add(pid)
        process = Path(proc_root) / str(pid)

        def read_start():
            text = (process / "stat").read_text(encoding="ascii")
            end = text.rfind(")")
            if end < 0 or text[: text.find(" ")] != str(pid):
                raise BindingError("Malformed worker stat.")
            fields = text[end + 1 :].split()
            if len(fields) < 20:
                raise BindingError("Malformed worker stat.")
            return int(fields[19])

        try:
            if read_start() != start:
                raise BindingError("Worker start identity mismatch.")
            if os.readlink(process / "exe") != exe or os.readlink(process / "cwd") != cwd:
                raise BindingError("Worker executable or cwd mismatch.")
            target = f"socket:[{inode}]"
            descriptors = [os.readlink(item) for item in (process / "fd").iterdir()]
            if target not in descriptors:
                raise BindingError("Worker socket descriptor missing.")
            if read_start() != start:
                raise BindingError("Worker changed during inspection.")
        except (OSError, ValueError) as error:
            raise BindingError("Unable to inspect worker identity.") from error
    return {"process_records_checked": len(seen)}


def _verify_worker_loopback_listeners(proc_root, expected_workers):
    """Match each worker socket descriptor to its own IPv4 loopback listener.

    This is a point-in-time process-record check, not proof of trusted procfs,
    exclusive routing, loaded application code or permission to send requests.
    It compares the calling thread and workers' network namespaces; a future
    adapter must perform requests on that same thread and prove HTTP routing.
    """
    _verify_worker_process_records(proc_root, expected_workers)

    def check_namespaces():
        try:
            current = os.readlink(Path(proc_root) / "thread-self" / "ns" / "net")
            if not (current.startswith("net:[") and current.endswith("]") and current[5:-1].isdigit()):
                raise BindingError("Malformed caller network namespace.")
            for worker in expected_workers:
                if os.readlink(Path(proc_root) / str(worker["pid"]) / "ns" / "net") != current:
                    raise BindingError("Worker and caller network namespaces differ.")
            return current
        except OSError as error:
            raise BindingError("Unable to inspect network namespace identity.") from error

    namespace = check_namespaces()
    ports, inodes = set(), set()
    for worker in expected_workers:
        endpoint = worker.get("endpoint")
        if not isinstance(endpoint, str):
            raise BindingError("Worker endpoint is missing.")
        try:
            parsed = urllib.parse.urlsplit(endpoint)
            port = parsed.port
        except ValueError as error:
            raise BindingError("Invalid worker endpoint.") from error
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or not port
            or parsed.netloc != f"127.0.0.1:{port}"
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise BindingError("Worker endpoint must be a direct IPv4 loopback URL.")
        inode = worker["socket_inode"]
        if port in ports or inode in inodes:
            raise BindingError("Workers require distinct listening sockets and ports.")
        ports.add(port)
        inodes.add(inode)
        try:
            lines = (
                (Path(proc_root) / str(worker["pid"]) / "net" / "tcp")
                .read_text(encoding="ascii")
                .splitlines()
            )
        except OSError as error:
            raise BindingError("Unable to inspect worker TCP listeners.") from error
        matches = []
        for line in lines[1:]:
            fields = line.split()
            if len(fields) < 10:
                raise BindingError("Malformed worker TCP record.")
            if fields[9] == str(inode):
                matches.append((fields[1].upper(), fields[3].upper()))
        if matches != [(f"0100007F:{port:04X}", "0A")]:
            raise BindingError("Worker socket is not the expected loopback listener.")
    _verify_worker_process_records(proc_root, expected_workers)
    if check_namespaces() != namespace:
        raise BindingError("Network namespace changed during inspection.")
    return {"loopback_listeners_checked": len(ports)}


def _verify_worker_database_connections(proc_root, expected_workers, db_socket):
    """Identify a pathname-associated socket in each worker's procfs table.

    This is a point-in-time procfs check. It does **not** prove that the worker is
    connected to the database, or that the server on that path is the bound
    database; it only shows an open socket whose associated path matches the
    bound path. It must not be used as connection-provenance proof.
    """

    if not isinstance(db_socket, str) or not os.path.isabs(db_socket):
        raise BindingError("A bound database socket path is required.")
    checked = 0
    for worker in expected_workers:
        pid = worker.get("pid") if isinstance(worker, dict) else None
        if type(pid) is not int or pid <= 0:
            raise BindingError("Invalid worker identity.")
        try:
            unix = (Path(proc_root) / str(pid) / "net" / "unix").read_text(encoding="ascii")
            inodes = {
                parts[6]
                for line in unix.splitlines()[1:]
                if len(parts := line.split()) >= 8 and parts[-1] == db_socket
            }
            if not inodes:
                raise BindingError("Worker has no socket for the bound database path.")
            descriptors = {os.readlink(item) for item in (Path(proc_root) / str(pid) / "fd").iterdir()}
            if not any(f"socket:[{inode}]" in descriptors for inode in inodes):
                raise BindingError("Worker database socket is not open.")
            checked += 1
        except (OSError, UnicodeDecodeError) as error:
            raise BindingError("Unable to inspect worker database connection.") from error
    return {"database_connections_checked": checked}


def _load_binding(path):
    data = _load_json(path)
    missing = sorted(REQUIRED_BINDING_KEYS - set(data))
    if missing:
        raise BindingError("Binding is missing required keys: " + ", ".join(missing))
    root = Path(data["bench_root"]).resolve()
    if not root.is_dir():
        raise BindingError("Bound bench root is unavailable.")
    if not Path(data["sites_path"]).resolve().is_dir():
        raise BindingError("Bound sites path is unavailable.")
    if not (Path(data["sites_path"]) / data["site"]).exists():
        raise BindingError("Bound site is unavailable.")
    if not Path(data["app_root"]).resolve().is_dir():
        raise BindingError("Bound app root is unavailable.")
    if data.get("phase") not in ALLOWED_PHASES:
        raise BindingError("Bound phase is outside the supported inventory.")
    for key in ("db_name", "redis_origin", "http_endpoint", "evidence_root"):
        if not isinstance(data.get(key), str) or not data.get(key):
            raise BindingError(f"Bound {key} is unavailable.")
    if not Path(data["evidence_root"]).is_absolute():
        raise BindingError("The evidence root must be an absolute path.")
    fixtures = data.get("fixtures") or {}
    if set(fixtures) != set(ALLOWED_FIXTURES):
        raise BindingError("Fixture aliases do not match the supported inventory.")
    dependencies = data.get("dependency_identities") or {}
    for key in ("frappe", "erpnext", "construction"):
        if not dependencies.get(key):
            raise BindingError("Missing dependency identity: " + key)
    serving = data.get("serving_process_identities") or []
    if not serving or any(not isinstance(item, str) or not item for item in serving):
        raise BindingError("Serving-process identities are unavailable.")
    candidate_manifest = Path(data["candidate_manifest_path"])
    if not candidate_manifest.is_absolute() or not candidate_manifest.is_file():
        raise BindingError("The candidate manifest is unavailable.")
    records = data.get("serving_process_records")
    if (
        not isinstance(records, list)
        or len(records) != 2
        or any(not isinstance(item, dict) for item in records)
    ):
        raise BindingError("Two serving-process records are required.")
    _verify_expected_manifest(data)
    endpoint = data["http_endpoint"]
    if urllib.parse.urlparse(endpoint).scheme not in ("http", "https"):
        raise BindingError("The HTTP endpoint is not a supported URL.")
    return data


def _same_manifest_value(expected, actual):
    """Type-strict structural comparison for nested identity values.

    ``json`` round-trips booleans as ``bool``, and Python treats ``True`` and
    ``1`` as equal; a plain ``!=`` would accept the substitution. Compare types
    first, then structure.
    """

    if type(expected) is not type(actual):
        return False
    if isinstance(expected, dict):
        return expected.keys() == actual.keys() and all(
            _same_manifest_value(expected[key], actual[key]) for key in expected
        )
    if isinstance(expected, list | tuple):
        return len(expected) == len(actual) and all(
            _same_manifest_value(left, right) for left, right in zip(expected, actual, strict=True)
        )
    return expected == actual


def _verify_expected_manifest(binding):
    """Compare the binding's observed identity with an independent manifest.

    The expected manifest is a separate private file; comparing two values read
    from the binding alone would let the binding create its own expectation.
    Site, origins, roots and phase are bound alongside the candidate and
    dependency/serving identities.
    """

    manifest_path = Path(binding["expected_manifest_path"])
    if not manifest_path.is_absolute() or not manifest_path.is_file():
        raise BindingError("The independently supplied expected manifest is unavailable.")
    expected = _load_json(manifest_path)
    if not set(EXPECTED_IDENTITY_KEYS) <= set(expected):
        raise BindingError("The expected manifest is incomplete.")
    for key in EXPECTED_IDENTITY_KEYS:
        if not _same_manifest_value(expected[key], binding.get(key)):
            raise BindingError(f"The bound {key} does not match the independent expectation.")


def verify_runtime_binding(binding_path, *, proc_root="/proc"):
    """Compose the binding checks into one point-in-time runtime proof.

    Runs, in order: binding shape against its independent expected manifest,
    candidate file and checkout verification, worker process records, and
    worker loopback listeners including caller/worker network-namespace
    equality. The candidate files are re-verified last so drift during the
    worker inspection is detected.

    A returned proof is evidence about this process at this instant. It does
    **not** enable transport: ``_require_verified_runtime`` still raises, and
    request routing to the intended worker, loaded application code, database
    connection provenance and persisted-state observation remain unverified.
    """
    binding = _load_binding(binding_path)
    manifest = _load_json(binding["candidate_manifest_path"])
    if not isinstance(manifest, dict):
        raise BindingError("Invalid candidate manifest.")
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    if hashlib.sha256(canonical).hexdigest() != binding["candidate_id"]:
        raise BindingError("Candidate manifest identity mismatch.")
    checkout = _verify_candidate_checkout(binding["app_root"], manifest, binding["candidate_id"])
    records = _verify_worker_process_records(proc_root, binding["serving_process_records"])
    listeners = _verify_worker_loopback_listeners(proc_root, binding["serving_process_records"])
    _verify_candidate_files(binding["app_root"], manifest, binding["candidate_id"])
    return {
        "candidate_id": binding["candidate_id"],
        "base_commit": checkout["base_commit"],
        "verified_files": checkout["verified_files"],
        "nonignored_change_set_verified": checkout["nonignored_change_set_verified"],
        "ignored_artifacts_absent": checkout["ignored_artifacts_absent"],
        "process_records_checked": records["process_records_checked"],
        "loopback_listeners_checked": listeners["loopback_listeners_checked"],
        "app_root": binding["app_root"],
        "proc_root": str(Path(proc_root)),
        "transport_enabled": False,
        "unverified": [
            "request routing to the intended worker",
            "loaded application code",
            "database connection provenance",
            "persisted-state observation",
        ],
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Unexpected redirect", headers, fp)


def _decode(payload):
    try:
        value = json.loads(payload.decode("utf-8") or "{}")
    except (UnicodeDecodeError, ValueError):
        return {"_unparsed_response": True}
    return value if isinstance(value, dict) else {"_unparsed_response": True}


def _open(opener, request):
    _require_verified_runtime()
    try:
        with opener.open(request, timeout=60) as response:
            return response.status, _decode(response.read())
    except urllib.error.HTTPError as error:
        return error.code, _decode(error.read())


def _request(endpoint, method, payload, headers, opener):
    url = endpoint + "/api/method/construction.api.execution_tree_api." + method
    if _ALLOWED_METHODS[method] == "GET":
        query = {key: value for key, value in payload.items() if value is not None}
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers=headers, method="GET")
    else:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
    return _open(opener, request)


def _generic_request(endpoint, http_method, path, payload, headers, opener):
    url = endpoint + path
    if http_method in ("GET", "DELETE"):
        query = {key: value for key, value in (payload or {}).items() if value is not None}
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers=headers, method=http_method)
    else:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload or {}).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json", "Accept": "application/json"},
            method=http_method,
        )
    return _open(opener, request)


def _login(endpoint, user, password, opener):
    _require_verified_runtime()
    body = urllib.parse.urlencode({"usr": user, "pwd": password}).encode("utf-8")
    request = urllib.request.Request(
        endpoint + "/api/method/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    with opener.open(request, timeout=60) as response:
        cookies = response.headers.get_all("Set-Cookie") or []
        return _decode(response.read()), cookies


def _csrf_from(cookies):
    for cookie in cookies:
        if cookie.startswith("csrf_token="):
            return cookie.split(";", 1)[0].split("=", 1)[1]
    return ""


def _redacted_error_body(data, allowed_types):
    """Only accept empty or explicitly typed error bodies as non-disclosing.

    Stack traces, server messages, payloads and other fields require a
    separately reviewed sanitization contract before they can count as denial.
    """
    if not isinstance(data, dict) or set(data) - {"exc_type"}:
        return False
    value = data.get("exc_type")
    return value is None or value in allowed_types


def _is_denied(status, data):
    if not _redacted_error_body(data, {"PermissionError", "frappe.exceptions.PermissionError"}):
        return False
    if status in (401, 403):
        return True
    if "Permission" in str(data.get("exc_type") or ""):
        return True
    return False


def _is_validation_error(status, data):
    if not _redacted_error_body(data, {"ValidationError", "frappe.exceptions.ValidationError"}):
        return False
    return status == 417 or "Validation" in str(data.get("exc_type") or "")


def _is_allowed(status, data):
    return status == 200 and not _is_denied(status, data) and "message" in data


def _resolve(value, context):
    if isinstance(value, str) and value.startswith("$"):
        return context.get(value[1:])
    if isinstance(value, dict):
        return {key: _resolve(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, context) for item in value]
    return value


def _resolve_path(template, context):
    if not template.startswith("/"):
        raise BindingError("Generic route must be an absolute path.")
    segments = []
    for segment in template.split("/")[1:]:
        value = _resolve(segment, context)
        if not isinstance(value, str) or value in ("", ".", ".."):
            raise BindingError("Generic route has a missing or invalid path segment.")
        segments.append(urllib.parse.quote(value, safe=""))
    return "/" + "/".join(segments)


def _tree_digest(binding, fixture, opener, headers, password):
    payload = {"project": binding["project"]}
    status, data = _request(binding["http_endpoint"], "get_tree", payload, headers, opener)
    if not _is_allowed(status, data):
        return None
    encoded = json.dumps(data.get("message"), sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _session(binding, fixture, opener):
    password = os.environ.get(binding["credentials_env"])
    if not password:
        raise BindingError("Runtime credentials are unavailable.")
    user = binding["fixtures"][fixture]
    login, cookies = _login(binding["http_endpoint"], user, password, opener)
    if not login or login.get("message") != "Logged In":
        raise BindingError("Fixture login failed.")
    headers = {"X-Frappe-CSRF-Token": _csrf_from(cookies), "Cookie": "; ".join(cookies)}
    return headers, password


def _code_number(code):
    if not isinstance(code, str) or not code.startswith("EBS-"):
        return None
    digits = code[4:]
    if not 4 <= len(digits) <= 19 or not digits.isascii() or not digits.isdigit():
        return None
    number = int(digits, 10)
    return number if 0 < number <= 2**63 - 1 else None


def _capture(context, key, message):
    if not isinstance(message, dict) or not message.get("name"):
        return
    context[key] = message.get("name")
    if message.get("modified"):
        context[f"{key}_modified"] = message.get("modified")
    if key == "node":
        context.setdefault("stale_modified", message.get("modified"))


def _assert_code_continuity(context, project, message, result):
    number = _code_number((message or {}).get("ebs_code"))
    key = f"expected_code_number:{project}"
    expected = context.get(key)
    if number is None:
        result["code_continuity"] = False
        return False
    if expected is not None and number != expected:
        # A denied create that advanced the counter without leaving a node
        # produces a gap here even though the tree digest stayed identical.
        result["code_continuity"] = False
        return False
    result["code_continuity"] = True
    context[key] = number + 1
    return True


def _nonblank_text(value):
    return isinstance(value, str) and bool(value.strip())


def _snapshot_flag(value):
    return type(value) in (int, bool) and value in (0, 1)


def _valid_node_snapshot_row(row):
    return (
        isinstance(row, dict)
        and all(_nonblank_text(row.get(field)) for field in ("company", "ebs_code", "title", "modified"))
        and "parent_node" in row
        and (row["parent_node"] in (None, "") or _nonblank_text(row["parent_node"]))
        and all(_snapshot_flag(row.get(field)) for field in ("is_group", "disabled"))
    )


def _valid_share_snapshot_row(row):
    return (
        isinstance(row, dict)
        and all(_nonblank_text(row.get(field)) for field in ("share_doctype", "share_name"))
        and all(_snapshot_flag(row.get(field)) for field in ("everyone", "read", "write", "share", "submit"))
        and "user" in row
        and (_nonblank_text(row["user"]) or (row["everyone"] and row["user"] in (None, "")))
    )


def _valid_node_snapshots(nodes, company, counter):
    if not isinstance(nodes, dict) or (nodes and counter is None):
        return False
    codes = set()
    for name, row in nodes.items():
        if not _nonblank_text(name) or not _valid_node_snapshot_row(row) or row["company"] != company:
            return False
        number = _code_number(row["ebs_code"])
        if number is None or number > counter or number in codes:
            return False
        codes.add(number)
    return True


def _valid_observer_snapshot(snapshot, project):
    """Validate offline evidence, including explicit empty query results.

    Nodes and shares are keyed by persisted document name. A null counter
    denotes an absent row. The runtime observer must establish the provenance
    and completeness of the reads separately.
    """
    if not _nonblank_text(project) or not isinstance(snapshot, dict) or snapshot.get("project") != project:
        return False
    if not _nonblank_text(snapshot.get("company")):
        return False
    if "counter" not in snapshot:
        return False
    counter = snapshot["counter"]
    if counter is not None and (type(counter) is not int or not 0 <= counter <= 2**63 - 1):
        return False
    project_row = snapshot.get("project_row")
    if (
        not isinstance(project_row, dict)
        or project_row.get("name") != project
        or project_row.get("company") != snapshot["company"]
    ):
        return False
    if "counter_row" not in snapshot:
        return False
    counter_row = snapshot["counter_row"]
    if counter is None:
        if counter_row is not None:
            return False
    elif (
        not isinstance(counter_row, dict)
        or not _nonblank_text(counter_row.get("name"))
        or counter_row.get("project") != project
        or type(counter_row.get("last_issued")) is not int
        or counter_row["last_issued"] != counter
    ):
        return False
    nodes = snapshot.get("nodes")
    shares = snapshot.get("shares")
    return (
        _valid_node_snapshots(nodes, snapshot["company"], counter)
        and isinstance(shares, dict)
        and all(_nonblank_text(name) and _valid_share_snapshot_row(row) for name, row in shares.items())
    )


def _read_persisted_snapshot(connection, *, project, expected_database):
    """Read an observer snapshot using a caller-owned, independent connection.

    The future runtime verifier must establish the origin of the connection,
    database/socket identity and private lab authorization before supplying it.
    This reader does not establish those facts and cannot enable transport.
    It always rolls back and closes the supplied connection.
    """
    cursor = None
    try:
        _require_verified_runtime()
        if not _nonblank_text(project) or not _nonblank_text(expected_database):
            raise BindingError("Observer Project and database must be specified.")
        cursor = connection.cursor()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        cursor.execute("SELECT DATABASE() AS database_name")
        identity = cursor.fetchone() or {}
        if identity.get("database_name") != expected_database:
            raise BindingError("Observer database identity mismatch.")
        tables = ("tabProject", "tabExecution Breakdown Node", "tabExecution Code Counter", "tabDocShare")
        cursor.execute(
            "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN (%s, %s, %s, %s)",
            tables,
        )
        engines = {row["TABLE_NAME"]: str(row.get("ENGINE") or "").lower() for row in cursor.fetchall()}
        if any(engines.get(table) != "innodb" for table in tables):
            raise BindingError("Observer requires all snapshot tables to use InnoDB.")
        cursor.execute("SELECT * FROM `tabProject` WHERE name=%s", (project,))
        projects = cursor.fetchall()
        if len(projects) != 1 or projects[0].get("name") != project:
            raise BindingError("Observer Project is missing or ambiguous.")
        cursor.execute(
            "SELECT * FROM `tabExecution Breakdown Node` WHERE project=%s ORDER BY name LIMIT 10001",
            (project,),
        )
        node_rows = cursor.fetchall()
        if len(node_rows) > 10000:
            raise BindingError("Observer node limit exceeded.")
        cursor.execute(
            "SELECT * FROM `tabExecution Code Counter` WHERE project=%s ORDER BY name LIMIT 2",
            (project,),
        )
        counters = cursor.fetchall()
        if len(counters) > 1:
            raise BindingError("Observer counter is ambiguous.")
        cursor.execute(
            "SELECT * FROM `tabDocShare` WHERE share_doctype IN (%s, %s) ORDER BY name",
            ("Execution Breakdown Node", "Execution Code Counter"),
        )
        shares = cursor.fetchall()
        nodes_by_name = {}
        for row in node_rows:
            row = dict(row)
            name = row.pop("name", None)
            if name in nodes_by_name:
                raise BindingError("Observer node identity is ambiguous.")
            row["modified"] = str(row["modified"]) if row.get("modified") is not None else None
            nodes_by_name[name] = row
        shares_by_name = {}
        for row in shares:
            row = dict(row)
            name = row.pop("name", None)
            if name in shares_by_name:
                raise BindingError("Observer share identity is ambiguous.")
            shares_by_name[name] = row
        snapshot = {
            "project": project,
            "company": projects[0].get("company"),
            "nodes": nodes_by_name,
            "counter": counters[0].get("last_issued") if counters else None,
            "shares": shares_by_name,
            "project_row": dict(projects[0]),
            "counter_row": dict(counters[0]) if counters else None,
        }
        if not _valid_observer_snapshot(snapshot, project):
            raise BindingError("Observer returned invalid or inconsistent persisted state.")
        return snapshot
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            try:
                connection.rollback()
            finally:
                connection.close()


def _exercise_revocation_sequence(adapter, *, project, access_input):
    """Exercise the sequencing contract; a runtime adapter is not yet provided.

    The future adapter must independently establish worker routing, session
    identity, committed authority changes, and observer provenance. This helper
    only enforces ordering and validates the adapter's reported outcomes.
    """
    _require_verified_runtime()
    allowed_inputs = {"role", "custom_docperm", "user_permission", "project_share", "active_scope"}
    if not _nonblank_text(project) or access_input not in allowed_inputs:
        raise BindingError("Invalid revocation fixture.")
    first, second = adapter.worker_identities()
    if not _nonblank_text(first) or not _nonblank_text(second) or first == second:
        raise BindingError("Two distinct workers are required.")
    session = adapter.login_on_worker(first)
    if session is None:
        raise BindingError("The warm session is unavailable.")
    try:
        if adapter.read(first, session, project) != "allow":
            raise BindingError("Warm request was not allowed.")
        before = deepcopy(adapter.snapshot(project))
        if not _valid_observer_snapshot(before, project):
            raise BindingError("Invalid before snapshot.")
        try:
            # Restore even when a response is lost after the change committed.
            if adapter.revoke_and_commit(second, access_input) is not True:
                raise BindingError("Revocation commit was not confirmed.")
            if adapter.read(first, session, project) != "deny":
                raise BindingError("Post-revocation read did not deny.")
            if adapter.mutate(first, session, project) != "deny":
                raise BindingError("Post-revocation mutation did not deny.")
            after = adapter.snapshot(project)
            if not _valid_observer_snapshot(after, project) or after != before:
                raise BindingError("Revocation mutation did not preserve persisted state.")
            if adapter.control_read(first, project) != "allow":
                raise BindingError("Unchanged control was not allowed.")
        finally:
            if adapter.restore_and_commit(second, access_input) is not True:
                raise BindingError("Revocation restoration was not confirmed.")
            if adapter.read(first, session, project) != "allow":
                raise BindingError("Restored session did not regain access.")
    finally:
        if adapter.logout(first, session) is not True:
            raise BindingError("Warm session cleanup was not confirmed.")
    return {"matched": True, "access_input": access_input}


def run_case(binding, case, context):
    _require_verified_runtime()
    fixture = case["fixture"]
    if fixture not in ALLOWED_FIXTURES:
        raise BindingError("Fixture alias is outside the fixed inventory.")
    payload = _resolve(case.get("payload") or {}, context)
    generic = "path" in case
    if generic:
        path = _resolve_path(case["path"], context)
    else:
        payload.setdefault("project", binding["project"])
    is_mutation = (
        (case.get("http_method") != "GET") if generic else (_ALLOWED_METHODS.get(case.get("method")) != "GET")
    )
    must_observe = is_mutation and case["expect"] == "deny"
    observer = context.get("_persisted_state_observer")
    if must_observe and not callable(observer):
        return {
            "name": case["name"],
            "matched": False,
            "actual": "not_run",
            "error": "independent persisted-state observer unavailable",
        }
    if must_observe:
        project = payload.get("project", binding["project"])
        if payload.get("doctype") == "Project":
            project = payload.get("name")
        before = deepcopy(observer(binding, case, payload))
        if not _valid_observer_snapshot(before, project):
            return {
                "name": case["name"],
                "matched": False,
                "actual": "not_run",
                "error": "before snapshot missing, incomplete or inconsistent",
            }
    opener = urllib.request.build_opener(_NoRedirect)
    headers, password = _session(binding, fixture, opener)
    if generic:
        http_method = case["http_method"]
        if http_method not in ("GET", "POST", "PUT", "DELETE"):
            raise BindingError("Generic HTTP method is outside the fixed inventory.")
        status, data = _generic_request(binding["http_endpoint"], http_method, path, payload, headers, opener)
        method = case.get("method") or http_method
    else:
        method = case["method"]
        if method not in ALLOWED_METHODS:
            raise BindingError("Method is outside the fixed RPC allowlist.")
        status, data = _request(binding["http_endpoint"], method, payload, headers, opener)
    allowed = _is_allowed(status, data)
    denied = _is_denied(status, data)
    errored = _is_validation_error(status, data)
    if generic:
        # A 404 cannot establish that the intended route and resource were reached.
        denied = status != 404 and (denied or errored)
    actual = "allow" if allowed else ("deny" if denied else "error")
    result = {
        "name": case["name"],
        "fixture": fixture,
        "method": method,
        "expected": case["expect"],
        "actual": actual,
        "status": status,
    }
    matched = actual == case["expect"]
    message = data.get("message") if allowed else None
    if allowed and case.get("expect_empty"):
        result["inventory_empty"] = message == []
        matched = matched and result["inventory_empty"]
    if allowed and case.get("capture"):
        _capture(context, case["capture"], message)
    if allowed and method == "create_node" and not generic:
        project = payload.get("project") or binding["project"]
        matched = _assert_code_continuity(context, project, message, result) and matched
    if must_observe:
        after = observer(binding, case, payload)
        after_valid = _valid_observer_snapshot(after, project)
        if not after_valid:
            result["error"] = "after snapshot missing, incomplete or inconsistent"
        result["state_unchanged"] = after_valid and before == after
        matched = matched and result["state_unchanged"]
    result["matched"] = matched
    if not matched and allowed:
        encoded = json.dumps(message, sort_keys=True, default=str).encode("utf-8")
        result["result_sha256"] = hashlib.sha256(encoded).hexdigest()
    elif not matched and denied:
        result["denial_reason"] = str(data.get("exc_type") or "PermissionError")[:100]
    return result


def _context_from_binding(binding):
    return {
        "project": binding["project"],
        "other_project": binding["other_project"],
        "other_company": binding["other_company"],
        "outsider": binding["fixtures"]["project_outsider"],
        "engineer": binding["fixtures"]["allowed_engineer"],
    }


def _missing_capture(value, context):
    if isinstance(value, dict):
        value = value.values()
    elif isinstance(value, str):
        return value.startswith("$") and _resolve(value, context) is None
    elif not isinstance(value, list):
        return False
    return any(_missing_capture(item, context) for item in value)


def run_catalog(binding, only=None):
    _require_verified_runtime()
    context = _context_from_binding(binding)
    results = []
    for case in ACCEPTANCE_CASES + GENERIC_CASES:
        if only and case["name"] != only:
            continue
        if _missing_capture(case.get("payload") or {}, context) or _missing_capture(
            case.get("path", "").split("/"), context
        ):
            results.append(
                {
                    "name": case["name"],
                    "matched": False,
                    "actual": "not_run",
                    "error": "missing captured node",
                }
            )
            continue
        results.append(run_case(binding, case, context))
    return results


def run(binding, fixture, method, payload):
    _require_verified_runtime()
    if method not in ALLOWED_METHODS:
        raise BindingError("Method is outside the fixed RPC allowlist.")
    if fixture not in ALLOWED_FIXTURES:
        raise BindingError("Fixture alias is outside the fixed inventory.")
    opener = urllib.request.build_opener(_NoRedirect)
    headers, _password = _session(binding, fixture, opener)
    request_payload = dict(payload)
    request_payload.setdefault("project", binding.get("project"))
    status, response = _request(binding["http_endpoint"], method, request_payload, headers, opener)
    message = response.get("message")
    encoded = json.dumps(message, sort_keys=True, default=str).encode("utf-8")
    return {
        "fixture": fixture,
        "method": method,
        "status": status,
        "allowed": _is_allowed(status, response),
        "denied": _is_denied(status, response),
        "result_sha256": hashlib.sha256(encoded).hexdigest(),
        "result_type": type(message).__name__,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bound execution tree transport harness")
    parser.add_argument("--binding", required=True)
    parser.add_argument("--fixture", choices=sorted(ALLOWED_FIXTURES))
    parser.add_argument("--method", choices=sorted(ALLOWED_METHODS))
    parser.add_argument("--payload-json", default=None)
    parser.add_argument("--case", default=None)
    args = parser.parse_args(argv)
    if (args.fixture is None) != (args.method is None):
        print(json.dumps({"ok": False, "error": "Supply both --fixture and --method, or neither"}))
        return 2
    # The older file-to-file binding comparison does not measure the running
    # server or processes. Refuse all HTTP until a separately reviewed runtime
    # verifier, independent persisted-state observer and two-worker session
    # test exist. This cannot be overridden by binding-file contents.
    print(json.dumps({"ok": False, "error": _TRANSPORT_DISABLED}))
    return 2


if __name__ == "__main__":
    sys.exit(main())
