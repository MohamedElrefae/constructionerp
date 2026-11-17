"""Prepare a fresh T3 data directory for OpenCode Go without handling credentials.

This helper writes only non-secret T3 settings. It never reads or copies an
existing settings/auth file and never starts OpenCode, T3, or a provider call.
The caller must run the returned login command interactively in the returned
isolated environment to authenticate the account in this data directory.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


class T3ProviderSetupError(RuntimeError):
    """Unsafe path or pre-existing data prevented isolated setup."""


T3_MANAGED_MARKER = ".codex-managed-t3"
T3_MANAGED_MARKER_CONTENT = "managed-t3-state/v1\n"
TARGET_INSTANCE_ID = "opencode"
TARGET_DRIVER = "opencode"
TARGET_MODEL = "opencode-go/deepseek-v4.1-flash"


@dataclass(frozen=True)
class OpenCodeGoSetup:
    """Non-secret paths and commands needed for a user-owned login step."""

    settings_path: Path
    auth_path: Path
    login_command: tuple[str, ...]
    login_environment: dict[str, str]


def prepare_opencode_go_deepseek(
    *,
    base_dir: str | Path,
    repository_root: str | Path,
    opencode_binary: str | Path,
) -> OpenCodeGoSetup:
    """Write an exact minimal provider selection into a new disposable T3 dir.

    T3 0.1.9 stores its server settings at ``<base-dir>/userdata/settings.json``.
    OpenCode's ``config.enabled`` defaults false, and the T3 instance-level
    ``enabled`` flag also defaults false for the ``opencode`` driver, so this
    writes both flags as true. The model selection uses the T3 instance id
    ``opencode`` and model slug ``opencode-go/deepseek-v4.1-flash``.

    Existing nonempty data is rejected without reading or merging it. The
    returned login environment redirects HOME/XDG paths so the user's
    interactive ``opencode auth login`` writes credentials only under this
    disposable data directory.
    """
    root_arg = Path(base_dir)
    repo_arg = Path(repository_root)
    binary_arg = Path(opencode_binary)
    for label, path in (
        ("base_dir", root_arg),
        ("repository_root", repo_arg),
        ("opencode_binary", binary_arg),
    ):
        if not path.is_absolute():
            raise T3ProviderSetupError(f"{label} must be an absolute path")

    repo = repo_arg.resolve(strict=True)
    root = root_arg.resolve()
    binary = binary_arg.resolve(strict=True)
    if not repo.is_dir():
        raise T3ProviderSetupError("repository_root must be a directory")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise T3ProviderSetupError("opencode_binary must be an executable regular file")
    if root == repo or repo in root.parents:
        raise T3ProviderSetupError("base_dir must be outside the repository checkout")
    if root_arg.is_symlink():
        raise T3ProviderSetupError("base_dir cannot be a symlink")
    if root.exists() and any(root.iterdir()):
        raise T3ProviderSetupError("base_dir must be new or empty; existing state will not be merged")

    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    marker = root / T3_MANAGED_MARKER
    marker.write_text(T3_MANAGED_MARKER_CONTENT)
    marker.chmod(0o600)

    userdata = root / "userdata"
    userdata.mkdir(mode=0o700)
    settings_path = userdata / "settings.json"
    settings = {
        "providerInstances": {
            TARGET_INSTANCE_ID: {
                "driver": TARGET_DRIVER,
                "enabled": True,
                "config": {
                    "enabled": True,
                    "binaryPath": str(binary),
                    "serverUrl": "",
                },
            }
        },
        "textGenerationModelSelection": {
            "instanceId": TARGET_INSTANCE_ID,
            "model": TARGET_MODEL,
        },
    }
    payload = (json.dumps(settings, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(settings_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())

    data_home = root / ".local" / "share"
    config_home = root / ".config"
    cache_home = root / ".cache"
    tmp_dir = root / "tmp"
    for directory in (data_home, config_home, cache_home, tmp_dir):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
    auth_path = data_home / "opencode" / "auth.json"
    login_environment = {
        "HOME": str(root),
        "XDG_CONFIG_HOME": str(config_home),
        "XDG_DATA_HOME": str(data_home),
        "XDG_CACHE_HOME": str(cache_home),
        "TMPDIR": str(tmp_dir),
        "PATH": str(binary.parent),
    }
    return OpenCodeGoSetup(
        settings_path=settings_path,
        auth_path=auth_path,
        login_command=(str(binary), "auth", "login"),
        login_environment=login_environment,
    )
