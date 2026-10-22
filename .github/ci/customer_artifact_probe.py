"""Verify a staged customer Git root and the Bench checkout derived from it."""

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

MANIFEST_NAME = "DISTRIBUTION_MANIFEST.json"
RECOVERY_SITE = "c2_customer_site"
RECOVERY_TOKEN_RE = re.compile(r"[0-9a-f]{32}\Z")


def _recovery_record_path(site, token, runner_temp):
    if site != RECOVERY_SITE:
        raise ValueError(f"recovery probe is restricted to {RECOVERY_SITE}")
    if not isinstance(token, str) or not RECOVERY_TOKEN_RE.fullmatch(token):
        raise ValueError("recovery token must be a lowercase 32-character UUID hex value")
    temp_root = Path(runner_temp).resolve(strict=True)
    return temp_root, temp_root / f"c2-recovery-{token}.json"


def _recovery_marker_file_name(token):
    if not isinstance(token, str) or not RECOVERY_TOKEN_RE.fullmatch(token):
        raise ValueError("recovery token must be a lowercase 32-character UUID hex value")
    return f"c2-recovery-{token}-marker.txt"


def _native_recovery_context(frappe):
    site = frappe.local.site
    if os.environ.get("C2_EXPECTED_SITE") != RECOVERY_SITE or site != RECOVERY_SITE:
        raise ValueError(f"recovery probe is restricted to the exact {RECOVERY_SITE} site")
    runner_temp = os.environ.get("C2_RUNNER_TEMP", "")
    token = os.environ.get("C2_RECOVERY_TOKEN", "")
    temp_root, record_path = _recovery_record_path(site, token, runner_temp)
    app_root = Path(frappe.get_app_path("construction")).resolve(strict=True)
    if app_root == temp_root or app_root in temp_root.parents:
        raise ValueError("recovery record directory must remain outside the customer app")
    return site, token, temp_root, record_path


def _validate_recovery_record(record, site, token):
    if not isinstance(record, dict) or record.get("site") != site or site != RECOVERY_SITE:
        raise ValueError("recovery record is not bound to the exact disposable C2 site")
    if not isinstance(token, str) or not RECOVERY_TOKEN_RE.fullmatch(token) or record.get("token") != token:
        raise ValueError("recovery record token does not match this C2 run")
    expected_user = f"c2-recovery-{token}@example.invalid"
    expected_file_name = _recovery_marker_file_name(token)
    user = record.get("user")
    file_name = record.get("file_name")
    file_url = record.get("file_url")
    digest = record.get("sha256")
    if user != expected_user:
        raise ValueError("recovery record user is outside the exact token prefix")
    if file_name != expected_file_name:
        raise ValueError("recovery record file name does not match the exact token-bound marker")
    if file_url != f"/private/files/{expected_file_name}":
        raise ValueError("recovery marker must be a private site file")
    if not isinstance(record.get("file_docname"), str) or not record["file_docname"].strip():
        raise ValueError("recovery record file DocType name is missing")
    if not re.fullmatch(r"[0-9a-f]{64}", digest or ""):
        raise ValueError("recovery record file name or SHA-256 is invalid")
    return record


def _read_recovery_record(site, token, runner_temp):
    _, record_path = _recovery_record_path(site, token, runner_temp)
    if record_path.is_symlink() or not record_path.is_file():
        raise ValueError("C2 recovery record is missing or is a symlink")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    return _validate_recovery_record(record, site, token)


def prepare_recovery_marker():
    """Create one unique synthetic User and private File on the C2 site only."""
    import frappe

    site, token, _temp_root, record_path = _native_recovery_context(frappe)
    if record_path.exists() or record_path.is_symlink():
        raise ValueError("recovery record already exists; refusing to overwrite it")
    user_name = f"c2-recovery-{token}@example.invalid"
    file_name = _recovery_marker_file_name(token)
    file_path = Path(frappe.get_site_path("private", "files", file_name))
    payload = f"synthetic C2 recovery marker {token}\n".encode("ascii")
    if (
        frappe.db.exists("User", user_name)
        or frappe.db.exists("File", {"file_name": file_name})
        or file_path.exists()
    ):
        raise ValueError("token-prefixed C2 recovery marker already exists")

    try:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": user_name,
                "first_name": "C2 synthetic recovery marker",
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": file_name,
                "is_private": 1,
                "content": payload.decode("ascii"),
            }
        ).insert(ignore_permissions=True)
        if file_doc.file_name != file_name or file_doc.file_url != f"/private/files/{file_name}":
            raise RuntimeError("native File marker changed its exact token-bound filename")
        if (
            not file_path.is_file()
            or hashlib.sha256(file_path.read_bytes()).hexdigest() != hashlib.sha256(payload).hexdigest()
        ):
            raise RuntimeError("native File marker did not persist with the expected bytes")
        record = {
            "site": site,
            "token": token,
            "user": user.name,
            "file_name": file_doc.file_name,
            "file_docname": file_doc.name,
            "file_url": file_doc.file_url,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "payload_bytes": len(payload),
        }
        _validate_recovery_record(record, site, token)
        with record_path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        frappe.db.rollback()
        raise
    print(f"prepared synthetic C2 recovery markers: user={user.name}, file={record['file_url']}")


def delete_recovery_marker():
    """Delete only the exact marker identities recorded for this C2 run."""
    import frappe

    site, token, _, _ = _native_recovery_context(frappe)
    runner_temp = os.environ["C2_RUNNER_TEMP"]
    record = _read_recovery_record(site, token, runner_temp)
    if not frappe.db.exists("User", record["user"]) or not frappe.db.exists("File", record["file_docname"]):
        raise ValueError("expected C2 recovery markers are not both present before deletion")
    user = frappe.get_doc("User", record["user"])
    file_doc = frappe.get_doc("File", record["file_docname"])
    marker_path = Path(frappe.get_site_path("private", "files", record["file_name"]))
    if user.name != record["user"] or user.email != record["user"]:
        raise ValueError("refusing to delete a User that does not match the exact marker identity")
    if (
        file_doc.name != record["file_docname"]
        or file_doc.file_name != record["file_name"]
        or file_doc.file_url != record["file_url"]
        or not file_doc.is_private
        or not marker_path.is_file()
        or _sha256(marker_path) != record["sha256"]
    ):
        raise ValueError(
            "refusing to delete a File that does not match the exact private marker identity/hash"
        )
    frappe.delete_doc("File", record["file_docname"], ignore_permissions=True, force=True)
    frappe.delete_doc("User", record["user"], ignore_permissions=True, force=True)
    if frappe.db.exists("User", record["user"]) or frappe.db.exists("File", record["file_docname"]):
        raise RuntimeError("C2 recovery marker deletion did not persist")
    print("deleted only the token-bound synthetic C2 User and File markers")


def assert_recovery_marker():
    """Confirm same-version restore recovered the exact synthetic DB and file markers."""
    import frappe

    site, token, _, _ = _native_recovery_context(frappe)
    runner_temp = os.environ["C2_RUNNER_TEMP"]
    record = _read_recovery_record(site, token, runner_temp)
    if not frappe.db.exists("User", record["user"]):
        raise RuntimeError("same-version restore did not recover the synthetic User marker")
    file_doc = frappe.get_doc("File", record["file_docname"])
    if file_doc.file_url != record["file_url"] or not file_doc.is_private:
        raise RuntimeError("same-version restore did not recover the expected private File record")
    file_path = Path(frappe.get_site_path("private", "files", Path(file_doc.file_url).name))
    if not file_path.is_file() or _sha256(file_path) != record["sha256"]:
        raise RuntimeError("same-version restore did not recover the private File bytes")
    print(f"same-version C2 restore recovered synthetic User and private File sha256={record['sha256']}")


def validate_recovery_backup(backup_dir, record_path, output_path):
    """Validate local synthetic backup archives and emit their paths/checksums."""
    raw_record_path = Path(record_path)
    if raw_record_path.is_symlink():
        raise ValueError("C2 recovery record must not be a symlink")
    record_path = raw_record_path.resolve(strict=True)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    _validate_recovery_record(record, RECOVERY_SITE, record.get("token"))
    raw_backup_root = Path(backup_dir)
    if raw_backup_root.is_symlink():
        raise ValueError("C2 backup directory must not be a symlink")
    backup_root = raw_backup_root.resolve(strict=True)
    raw_output_path = Path(output_path)
    if raw_output_path.is_symlink():
        raise ValueError("backup validation output must not be a symlink")
    output_path = raw_output_path.resolve()
    if output_path.parent != backup_root or output_path.name != "validation.json" or output_path.exists():
        raise ValueError("backup validation output must be a new file inside its dedicated backup directory")
    expected_backup_name = f"c2-recovery-{record['token']}-backup"
    if backup_root.name != expected_backup_name or record_path.parent != backup_root.parent:
        raise ValueError("C2 backup and marker record must share the exact runner-temp token namespace")
    database = list(backup_root.glob(f"*-{RECOVERY_SITE}-database.sql.gz"))
    public = list(backup_root.glob(f"*-{RECOVERY_SITE}-files.tar")) + list(
        backup_root.glob(f"*-{RECOVERY_SITE}-files.tgz")
    )
    private = list(backup_root.glob(f"*-{RECOVERY_SITE}-private-files.tar")) + list(
        backup_root.glob(f"*-{RECOVERY_SITE}-private-files.tgz")
    )
    if len(database) != 1 or len(public) != 1 or len(private) != 1:
        raise ValueError("C2 backup must contain exactly one SQL gzip, public tar, and private tar archive")
    with gzip.open(database[0], "rb") as stream:
        while stream.read(1024 * 1024):
            pass
    private_name = record["file_name"]
    marker_seen = False
    for archive in (public[0], private[0]):
        with tarfile.open(archive, "r:*") as stream:
            members = stream.getmembers()
            if not members:
                raise ValueError(f"backup file archive is empty: {archive.name}")
            if archive == private[0]:
                matching = [member for member in members if Path(member.name).name == private_name]
                if len(matching) != 1 or not matching[0].isfile():
                    raise ValueError("private backup archive does not contain the exact C2 marker file")
                content = stream.extractfile(matching[0])
                if content is None or hashlib.sha256(content.read()).hexdigest() != record["sha256"]:
                    raise ValueError("private backup archive marker bytes do not match the recorded SHA-256")
                marker_seen = True
    if not marker_seen:
        raise ValueError("private C2 recovery marker was not verified inside the backup")
    result = {
        label: {"path": str(path), "sha256": _sha256(path)}
        for label, path in (("database", database[0]), ("public", public[0]), ("private", private[0]))
    }
    with output_path.open("x", encoding="utf-8") as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write("\n")
    print(json.dumps(result, sort_keys=True))


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_digest(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(row["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _manifest_rows(manifest):
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        raise ValueError("distribution manifest rows must be a list")

    paths = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("distribution manifest contains a malformed row")
        rel = row.get("path")
        digest = row.get("sha256")
        if not isinstance(rel, str) or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"distribution manifest contains an invalid row: {row!r}")
        path = PurePosixPath(rel)
        if (
            not rel
            or "\\" in rel
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.as_posix() != rel
            or rel == MANIFEST_NAME
        ):
            raise ValueError(f"distribution manifest path is not canonical: {rel!r}")
        paths.append(rel)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("distribution manifest paths must be unique and sorted")
    return rows


def _local_origin_path(value):
    parsed = urlparse(value)
    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            raise ValueError("customer artifact origin must be a local file URL")
        return Path(unquote(parsed.path)).resolve()
    if parsed.scheme:
        raise ValueError("customer artifact origin must be a local filesystem path")
    return Path(value).resolve()


def _matches_binding(result, binding):
    keys = {
        "source_head",
        "customer_commit",
        "manifest_sha256",
        "files",
        "artifact_tree_sha256",
    }
    return all(result.get(key) == binding.get(key) for key in keys)


def verify_checkout(
    repo,
    source_sha,
    expected_commit=None,
    expected_origin=None,
    binding=None,
    expected_remote="origin",
):
    repo = Path(repo).resolve(strict=True)
    root = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if root != repo:
        raise ValueError(f"Git root differs from requested repository: {root}")

    commit = _git(repo, "rev-parse", "HEAD")
    if expected_commit and commit != expected_commit:
        raise ValueError(f"unexpected customer artifact commit: {commit}")
    parents = _git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if parents != [commit]:
        raise ValueError("customer artifact Git history must contain a single root commit")

    status = _git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise ValueError(f"customer artifact worktree is not clean: {status.splitlines()[:8]}")

    manifest_path = repo / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("distribution manifest is missing or is a symlink")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("distribution manifest has an unsupported schema")
    if manifest.get("source_head") != source_sha:
        raise ValueError("distribution manifest source_head does not equal the candidate SHA")

    rows = _manifest_rows(manifest)
    payload_paths = {row["path"] for row in rows}
    if manifest.get("artifact_tree_sha256") != _tree_digest(rows):
        raise ValueError("distribution manifest tree digest is inconsistent")
    expected_paths = payload_paths | {MANIFEST_NAME}
    tracked_paths = {path for path in _git(repo, "ls-files", "-z").split("\0") if path}
    if tracked_paths != expected_paths:
        extra = sorted(tracked_paths - expected_paths)
        missing = sorted(expected_paths - tracked_paths)
        raise ValueError(f"Git inventory differs from manifest; extra={extra[:8]}, missing={missing[:8]}")
    if manifest.get("files") != len(payload_paths):
        raise ValueError("distribution manifest file count is inconsistent")

    for row in rows:
        path = repo / row["path"]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"manifest payload is missing or is not a regular file: {row['path']}")
        if _sha256(path) != row["sha256"]:
            raise ValueError(f"manifest payload hash mismatch: {row['path']}")

    origin_path = None
    if expected_origin is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", expected_remote):
            raise ValueError("expected customer artifact remote name is invalid")
        remotes = set(_git(repo, "remote").splitlines())
        if expected_remote not in remotes:
            raise ValueError(f"expected customer artifact remote is missing: {expected_remote}")
        origin = _git(repo, "remote", "get-url", expected_remote)
        origin_path = _local_origin_path(origin)
        if origin_path != Path(expected_origin).resolve(strict=True):
            raise ValueError(f"unexpected customer artifact origin: {origin_path}")

    result = {
        "source_head": source_sha,
        "customer_commit": commit,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "files": len(payload_paths),
        "artifact_tree_sha256": manifest.get("artifact_tree_sha256"),
        "origin": str(origin_path) if origin_path else None,
    }
    if binding is not None and not _matches_binding(result, binding):
        raise ValueError("customer checkout does not match the staged artifact binding")
    return result


def verify_import_path():
    """Bench execute target: confirm Frappe imports the installed customer app."""
    import frappe

    import construction

    expected = Path(os.environ["C2_EXPECTED_APP_PATH"]).resolve(strict=True)
    app_path = Path(frappe.get_app_path("construction")).resolve(strict=True)
    module_path = Path(construction.__file__).resolve(strict=True)
    if app_path != expected or module_path != expected / "__init__.py":
        raise RuntimeError(f"construction imported from {module_path}; expected {expected / '__init__.py'}")
    installed = set(frappe.get_installed_apps())
    missing = {"construction", "erpnext"} - installed
    if missing:
        raise RuntimeError(f"C2 site is missing installed apps: {sorted(missing)}")
    print(f"construction import verified: {module_path}")


def verify_generated_theme_assets():
    """Verify registered construction web assets and generated legacy login CSS."""
    import frappe

    bench_root = Path(frappe.utils.get_bench_path()).resolve(strict=True)
    app_package = Path(frappe.get_app_path("construction")).resolve(strict=True)
    customer_root = app_package.parent
    if not app_package.is_dir() or not (app_package / "__init__.py").is_file():
        raise RuntimeError("installed construction app package is missing")

    hooks = {
        "web_include_css": frappe.get_hooks("web_include_css", app_name="construction"),
        "web_include_js": frappe.get_hooks("web_include_js", app_name="construction"),
    }
    asset_urls = _construction_web_asset_urls(hooks)
    if not asset_urls:
        raise RuntimeError("construction has no registered web CSS or JavaScript assets")
    for url in asset_urls:
        _verify_served_customer_asset(bench_root, customer_root, url)

    themes = frappe.get_all(
        "Construction Theme",
        fields=["name", "modified", "is_system_theme", "is_default_light", "is_default_dark"],
        order_by="modified desc, name asc",
    )
    eligible = [
        theme
        for theme in themes
        if any(
            theme.get(field) in (True, 1, "1")
            for field in ("is_system_theme", "is_default_light", "is_default_dark")
        )
    ]
    if not eligible:
        raise RuntimeError("no eligible Construction Theme exists to generate the legacy login stylesheet")

    # on_update() writes this shared legacy cache for every system/default theme.
    # The most recently modified eligible theme is the best available last-writer
    # proxy; equal timestamps remain ambiguous, so accept only output matching one
    # of those tied native generators.
    last_writer_candidates = _latest_login_css_themes(eligible)
    expected_css = [
        frappe.get_doc("Construction Theme", theme["name"]).generate_login_css()
        for theme in last_writer_candidates
    ]
    login_asset = bench_root / "sites/assets/construction/css/login_theme.css"
    _verify_generated_login_css(login_asset, expected_css)
    print(f"construction web assets and generated legacy login CSS verified ({len(asset_urls)} assets)")


def _construction_web_asset_urls(hooks):
    """Return distinct construction-owned /assets URLs from the app's web hooks."""
    from urllib.parse import urlsplit

    urls = set()
    for hook_name in ("web_include_css", "web_include_js"):
        values = hooks.get(hook_name, [])
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"{hook_name} must be a path or a list of paths")
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{hook_name} contains an invalid asset path")
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or parsed.fragment:
                raise ValueError(f"{hook_name} contains a non-local asset path")
            if parsed.path.startswith("/assets/construction/"):
                urls.add(value)
    return sorted(urls)


def _latest_login_css_themes(eligible_themes):
    """Return all eligible themes tied for latest modification, without arbitrary selection."""
    if not eligible_themes:
        raise ValueError("no eligible Construction Theme exists to generate the legacy login stylesheet")
    modifications = [theme.get("modified") for theme in eligible_themes]
    if any(modified is None for modified in modifications):
        raise ValueError("eligible Construction Theme has no modification timestamp")
    newest_modified = max(modifications)
    return [theme for theme in eligible_themes if theme.get("modified") == newest_modified]


def _verify_served_customer_asset(bench_root, customer_root, url):
    """Check a registered construction asset maps to nonempty, exact customer bytes."""
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    prefix = "/assets/construction/"
    if not parsed.path.startswith(prefix):
        raise ValueError(f"asset is outside the construction namespace: {url}")
    relative = PurePosixPath(parsed.path[len(prefix) :])
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError(f"invalid construction asset path: {url}")

    app_package = (customer_root / "construction").resolve(strict=True)
    source = app_package.joinpath("public", *relative.parts).resolve(strict=True)
    served = (bench_root / "sites" / "assets" / "construction" / Path(*relative.parts)).resolve(strict=True)
    if not source.is_relative_to(customer_root) or not served.is_relative_to(customer_root):
        raise ValueError(f"construction asset resolves outside the customer checkout: {url}")
    if not source.is_file() or not served.is_file():
        raise ValueError(f"construction asset is missing from source or served assets: {url}")
    source_bytes = source.read_bytes()
    served_bytes = served.read_bytes()
    if not source_bytes or not served_bytes:
        raise ValueError(f"construction asset is empty: {url}")
    if hashlib.sha256(source_bytes).digest() != hashlib.sha256(served_bytes).digest():
        raise ValueError(f"served construction asset differs from customer source: {url}")


def _verify_generated_login_css(asset, expected_css):
    """Require the legacy cache to match the latest eligible native generator output."""
    if not expected_css or not all(isinstance(css, str) for css in expected_css):
        raise ValueError("eligible theme generator output is missing or invalid")
    asset = Path(asset)
    if asset.is_symlink() or not asset.is_file():
        raise ValueError("generated legacy login stylesheet is missing or is a symlink")
    actual = asset.read_bytes()
    expected = {css.encode("utf-8") for css in expected_css}
    if actual not in expected:
        raise ValueError("generated legacy login stylesheet does not match eligible theme output")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo")
    parser.add_argument("--source-sha")
    parser.add_argument("--expected-commit")
    parser.add_argument("--expected-origin")
    parser.add_argument("--expected-remote", default="origin")
    parser.add_argument("--write-binding")
    parser.add_argument("--expected-binding")
    parser.add_argument("--validate-recovery-backup", action="store_true")
    parser.add_argument("--backup-dir")
    parser.add_argument("--recovery-record")
    parser.add_argument("--backup-validation-output")
    args = parser.parse_args(argv)

    try:
        if args.validate_recovery_backup:
            if not all((args.backup_dir, args.recovery_record, args.backup_validation_output)):
                parser.error(
                    "backup validation requires --backup-dir, --recovery-record, and --backup-validation-output"
                )
            validate_recovery_backup(args.backup_dir, args.recovery_record, args.backup_validation_output)
            return 0
        if not args.repo or not args.source_sha:
            parser.error("checkout verification requires --repo and --source-sha")
        result = verify_checkout(
            args.repo,
            args.source_sha,
            expected_commit=args.expected_commit,
            expected_origin=args.expected_origin,
            expected_remote=args.expected_remote,
        )
        if args.expected_binding:
            binding_path = Path(args.expected_binding).resolve(strict=True)
            if binding_path.is_relative_to(Path(args.repo).resolve()):
                raise ValueError("binding file must remain outside the customer repository")
            binding = json.loads(binding_path.read_text(encoding="utf-8"))
            if not _matches_binding(result, binding):
                raise ValueError("customer checkout does not match the original staged artifact binding")
        if args.write_binding:
            binding_path = Path(args.write_binding).resolve()
            if binding_path.is_relative_to(Path(args.repo).resolve()):
                raise ValueError("binding file must remain outside the customer repository")
            binding_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        tarfile.TarError,
        EOFError,
    ) as exc:
        print(f"customer artifact verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
