import base64
import hashlib
import shutil

import builder_candidate_prototype as prototype
import pytest
from core import WorkflowError


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _entry(path, base, content):
    return {
        "path": path,
        "base_sha256": _sha(base) if base is not None else None,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "content_sha256": _sha(content),
    }


def _synthetic_source(path):
    path.mkdir()
    (path / prototype.SYNTHETIC_MARKER).write_bytes(prototype.SYNTHETIC_MARKER_VALUE)
    (path / "src").mkdir()
    (path / "src/base.py").write_text("VALUE = 'base'\n")
    (path / "README.txt").write_text("unchanged context\n")
    return path


def test_prepares_full_copy_and_refuses_validation_without_net_namespace(tmp_path, monkeypatch):
    source = _synthetic_source(tmp_path / "source")
    base = (source / "src/base.py").read_bytes()
    bundle = {"files": [_entry("src/base.py", base, b"VALUE = 'proposed'\n")]}
    monkeypatch.setattr(prototype, "_network_boundary_available", lambda: False)

    result = prototype.prepare_and_validate(
        source,
        bundle,
        tmp_path / "candidate",
        ["src/"],
        [["/usr/bin/python3", "-c", "raise SystemExit(0)"]],
    )

    candidate = tmp_path / "candidate"
    assert (candidate / "README.txt").read_text() == "unchanged context\n"
    assert (candidate / "src/base.py").read_bytes() == b"VALUE = 'proposed'\n"
    assert (source / "src/base.py").read_bytes() == base
    assert result["validation_status"] == "refused"
    assert result["validation_complete"] is False
    assert result["validation_passed"] is False
    assert result["records"] == []
    assert result["refusal_reason"] == "bubblewrap network namespace unavailable"


def test_refuses_unmarked_or_repository_source(tmp_path):
    source = tmp_path / "unmarked"
    source.mkdir()
    with pytest.raises(WorkflowError, match="marked synthetic"):
        prototype.prepare_and_validate(
            source,
            {"files": [_entry("new", None, b"x")]},
            tmp_path / "out",
            ["new"],
            [["/usr/bin/python3", "-c", "pass"]],
        )
    (source / prototype.SYNTHETIC_MARKER).write_bytes(prototype.SYNTHETIC_MARKER_VALUE)
    (source / ".git").mkdir()
    with pytest.raises(WorkflowError, match="repository roots"):
        prototype.prepare_and_validate(
            source,
            {"files": [_entry("new", None, b"x")]},
            tmp_path / "out",
            ["new"],
            [["/usr/bin/python3", "-c", "pass"]],
        )


def test_refuses_commands_supplied_as_shell_text(tmp_path, monkeypatch):
    source = _synthetic_source(tmp_path / "source")
    monkeypatch.setattr(prototype, "_network_boundary_available", lambda: False)
    with pytest.raises(WorkflowError, match="absolute argv arrays"):
        prototype.prepare_and_validate(
            source,
            {"files": [_entry("new", None, b"x")]},
            tmp_path / "candidate",
            ["new"],
            ["/bin/sh -c true"],
        )


@pytest.mark.skipif(not shutil.which("bwrap"), reason="bubblewrap binary unavailable")
def test_actual_offline_validation_runs_only_when_namespace_probe_succeeds(tmp_path):
    if not prototype._network_boundary_available():
        pytest.skip("kernel denies user network namespace creation")
    source = _synthetic_source(tmp_path / "source")
    base = (source / "src/base.py").read_bytes()
    bundle = {"files": [_entry("src/base.py", base, b"VALUE = 'validated'\n")]}
    result = prototype.prepare_and_validate(
        source,
        bundle,
        tmp_path / "candidate",
        ["src/"],
        [
            [
                "/usr/bin/python3",
                "-c",
                "from pathlib import Path; assert \"validated\" in Path('src/base.py').read_text()",
            ],
            [
                "/usr/bin/python3",
                "-c",
                "import socket; s=socket.socket(); s.settimeout(1); assert s.connect_ex(('198.51.100.1',443)) != 0",
            ],
        ],
    )
    assert result["validation_status"] == "complete"
    assert result["validation_complete"] is True
    assert result["validation_passed"] is True
    assert result["records"][0]["exit_code"] == 0
    assert result["records"][1]["exit_code"] == 0
