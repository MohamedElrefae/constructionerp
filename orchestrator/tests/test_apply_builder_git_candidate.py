import base64
import hashlib
import shutil
import subprocess
import sys

import apply_builder_git_candidate as apply_candidate
import pytest
from core import WorkflowError
from validation_runner import can_unshare_net


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _checkout(root):
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "src").mkdir()
    (root / "src/app.py").write_text("VALUE = 'base'\n")
    _git(root, "add", "src/app.py")
    _git(root, "commit", "-qm", "base")
    root.chmod(0o700)
    return _git(root, "rev-parse", "HEAD"), _git(root, "branch", "--show-current")


def _bundle(path, before, after):
    return {"verdict": "PASS", "files": [{
        "path": path,
        "base_sha256": hashlib.sha256(before).hexdigest() if before is not None else None,
        "content_base64": base64.b64encode(after).decode("ascii"),
        "content_sha256": hashlib.sha256(after).hexdigest(),
    }]}


def test_clean_checkout_artifact_uses_native_freeze_and_validation(tmp_path):
    if not shutil.which("bwrap") or not can_unshare_net():
        pytest.skip("native offline validation requires working bubblewrap network isolation")
    checkout = tmp_path / "dedicated-checkout"
    base, branch = _checkout(checkout)
    original = (checkout / "src/app.py").read_bytes()
    changed = b"VALUE = 'builder'\n"
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    work_item = tmp_path / "work-item"
    work_item.mkdir()
    control = tmp_path / "control"
    control.mkdir()
    command = [sys.executable, "-c",
               "from pathlib import Path; assert Path('src/app.py').read_text() == \"VALUE = 'builder'\\n\""]

    result = apply_candidate.apply_builder_artifact(
        artifact=_bundle("src/app.py", original, changed),
        checkout=checkout,
        expected_base_commit=base,
        expected_branch=branch,
        allowed_paths=["src/"],
        validation_commands=[command],
        evidence_directory=evidence,
        work_item_root=work_item,
        control_root=control,
    )

    assert result["validation"]["complete"] is True
    assert result["validation"]["passed"] is True
    assert (evidence / "tested-candidate" / "tree.tar").is_file()
    assert (evidence / "tested-candidate" / "manifest.json").is_file()
    assert result["engine_acceptance"].startswith("not_wired")
    assert _git(checkout, "status", "--porcelain")


def test_dirty_checkout_is_rejected_before_artifact_staging(tmp_path):
    checkout = tmp_path / "dedicated-checkout"
    base, branch = _checkout(checkout)
    (checkout / "extra.txt").write_text("local change\n")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    work_item = tmp_path / "work-item"
    work_item.mkdir()
    control = tmp_path / "control"
    control.mkdir()
    with pytest.raises(WorkflowError, match="must be clean"):
        apply_candidate.apply_builder_artifact(
            artifact=_bundle("src/new.py", None, b"x\n"), checkout=checkout,
            expected_base_commit=base, expected_branch=branch,
            allowed_paths=["src/"], validation_commands=[[sys.executable, "-c", "pass"]],
            evidence_directory=evidence, work_item_root=work_item, control_root=control,
        )
    assert not (checkout / "src/new.py").exists()


def test_base_hash_mismatch_is_rejected_before_checkout_write(tmp_path):
    checkout = tmp_path / "dedicated-checkout"
    base, branch = _checkout(checkout)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    work_item = tmp_path / "work-item"
    work_item.mkdir()
    control = tmp_path / "control"
    control.mkdir()
    bad = _bundle("src/app.py", b"wrong base\n", b"VALUE = 'builder'\n")
    with pytest.raises(WorkflowError, match="Base content hash mismatch"):
        apply_candidate.apply_builder_artifact(
            artifact=bad, checkout=checkout, expected_base_commit=base,
            expected_branch=branch, allowed_paths=["src/"],
            validation_commands=[[sys.executable, "-c", "pass"]],
            evidence_directory=evidence, work_item_root=work_item, control_root=control,
        )
    assert (checkout / "src/app.py").read_text() == "VALUE = 'base'\n"
