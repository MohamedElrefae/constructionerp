import json
import sys
from pathlib import Path

import pytest

from t3_provider_setup import T3ProviderSetupError, prepare_opencode_go_deepseek


def _setup(tmp_path: Path, *, base: Path | None = None):
    repository = tmp_path / "checkout"
    repository.mkdir()
    return prepare_opencode_go_deepseek(
        base_dir=(base or (tmp_path / "isolated-t3")).resolve(),
        repository_root=repository.resolve(),
        opencode_binary=Path(sys.executable).resolve(),
    )


def test_writes_minimal_nonsecret_settings_and_isolated_login_plan(tmp_path):
    plan = _setup(tmp_path)
    settings = json.loads(plan.settings_path.read_text())
    assert settings == {
        "providerInstances": {
            "opencode": {
                "driver": "opencode",
                "enabled": True,
                "config": {
                    "enabled": True,
                    "binaryPath": str(Path(sys.executable).resolve()),
                    "serverUrl": "",
                },
            }
        },
        "textGenerationModelSelection": {
            "instanceId": "opencode",
            "model": "opencode-go/deepseek-v4.1-flash",
        },
    }
    assert plan.login_command == (str(Path(sys.executable).resolve()), "auth", "login")
    assert str(plan.auth_path) == plan.login_environment["XDG_DATA_HOME"] + "/opencode/auth.json"
    assert plan.login_environment["HOME"] == str(plan.settings_path.parents[1])
    assert plan.login_environment["PATH"] == str(Path(sys.executable).resolve().parent)
    assert set(plan.login_environment) == {
        "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "TMPDIR", "PATH"
    }
    assert plan.settings_path.stat().st_mode & 0o777 == 0o600
    assert plan.settings_path.parent.stat().st_mode & 0o777 == 0o700
    assert plan.settings_path.parent.parent.stat().st_mode & 0o777 == 0o700
    assert not plan.auth_path.exists()


def test_refuses_existing_state_without_overwriting_it(tmp_path):
    base = tmp_path / "isolated-t3"
    base.mkdir()
    settings = base / "userdata" / "settings.json"
    settings.parent.mkdir()
    settings.write_text('{"keep":"unchanged"}\n')
    with pytest.raises(T3ProviderSetupError, match="will not be merged"):
        _setup(tmp_path, base=base)
    assert settings.read_text() == '{"keep":"unchanged"}\n'


def test_refuses_base_inside_repository(tmp_path):
    repository = tmp_path / "checkout"
    repository.mkdir()
    base = repository / "isolated"
    with pytest.raises(T3ProviderSetupError, match="outside the repository"):
        prepare_opencode_go_deepseek(
            base_dir=base,
            repository_root=repository,
            opencode_binary=Path(sys.executable).resolve(),
        )


def test_refuses_relative_paths(tmp_path):
    repository = tmp_path / "checkout"
    repository.mkdir()
    with pytest.raises(T3ProviderSetupError, match="base_dir must be an absolute path"):
        prepare_opencode_go_deepseek(
            base_dir="relative-state",
            repository_root=repository.resolve(),
            opencode_binary=Path(sys.executable).resolve(),
        )


def test_refuses_non_executable_provider_binary(tmp_path):
    repository = tmp_path / "checkout"
    repository.mkdir()
    binary = tmp_path / "not-executable"
    binary.write_text("synthetic")
    binary.chmod(0o600)
    with pytest.raises(T3ProviderSetupError, match="executable regular file"):
        prepare_opencode_go_deepseek(
            base_dir=(tmp_path / "isolated-t3").resolve(),
            repository_root=repository.resolve(),
            opencode_binary=binary.resolve(),
        )
