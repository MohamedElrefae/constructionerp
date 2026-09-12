import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def require_guard_for_every_python_subprocess(monkeypatch):
    """Fail retained CLI tests if a new child omits isolation or observation."""
    real_run = subprocess.run

    def guarded_run(args, **kwargs):
        is_python = str(args[0]) == PYTHON
        if is_python:
            env = kwargs.get("env", {})
            assert env.get("PYTHONPATH") == str(ROOT / "tests_offline")
            assert env.get("PYTHONNOUSERSITE") == "1"
            observation = Path(env["OFFLINE_IMPORT_OBSERVATION"])
            assert not observation.exists(), "each CLI needs a fresh import observation"
        result = real_run(args, **kwargs)
        if is_python:
            assert observation.is_file(), "child import guard did not report"
        return result

    monkeypatch.setattr(subprocess, "run", guarded_run)


@pytest.fixture
def context_checker():
    return load_module("offline_ai_context_check", ROOT / "scripts" / "ai_context_check.py")


@pytest.fixture
def metadata_linter():
    return load_module("offline_scope_linter", ROOT / "scripts" / "lint_scope_metadata.py")


def test_context_checker_import_is_quiet_and_safe(capsys):
    load_module("offline_import_only", ROOT / "scripts" / "ai_context_check.py")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_context_checker_json_cli_passes_from_unrelated_cwd(tmp_path):
    env = offline_subprocess_env(tmp_path)
    result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "ai_context_check.py"), "--repo-root", str(ROOT), "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["repo_root"] == str(ROOT)
    assert payload["failed"] == 0
    assert {check["id"] for check in payload["checks"]} == {
        "SCP-C1", "SCP-C2", "SCP-C3", "SCP-C4", "SCP-C5", "SCP-C6", "SCP-C7", "SCP-C8", "SCP-C8B", "SCP-C9", "SCP-C10"
    }
    assert json.loads((tmp_path / "imports.json").read_text(encoding="utf-8")) == []


def test_context_checker_help_and_invalid_cli_exit_without_checks(tmp_path):
    help_result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "ai_context_check.py"), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=offline_subprocess_env(tmp_path / "help-run"),
        check=False,
    )
    invalid_result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "ai_context_check.py"), "--unknown"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=offline_subprocess_env(tmp_path / "invalid-run"),
        check=False,
    )
    assert help_result.returncode == 0
    assert "--repo-root" in help_result.stdout
    assert invalid_result.returncode == 2
    assert json.loads((tmp_path / "help-run" / "imports.json").read_text(encoding="utf-8")) == []
    assert json.loads((tmp_path / "invalid-run" / "imports.json").read_text(encoding="utf-8")) == []


def offline_subprocess_env(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT / "tests_offline"),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "OFFLINE_IMPORT_OBSERVATION": str(tmp_path / "imports.json"),
        }
    )
    return env


@pytest.mark.parametrize(
    "label,value,diagnostic",
    [
        ("malformed", "{", "JSONDecodeError"),
        ("array", "[]", "expected a JSON object"),
        ("null", "null", "expected a JSON object"),
        ("string", '\"not an object\"', "expected a JSON object"),
        ("invalid-fields", '{"fields": [null]}', "TypeError"),
        ("missing", None, "FileNotFoundError"),
    ],
)
def test_context_checker_malformed_and_missing_inputs_are_cli_failures(
    tmp_path, label, value, diagnostic
):
    """Focused input fixtures; these do not replace the real copied-checkout gate."""
    test_root = tmp_path / label
    boq_item = test_root / "construction" / "construction" / "doctype" / "boq_item"
    boq_item.mkdir(parents=True)
    if value is not None:
        (boq_item / "boq_item.json").write_text(value, encoding="utf-8")
    result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "ai_context_check.py"), "--repo-root", str(test_root), "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=offline_subprocess_env(tmp_path / "run"),
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    failure = next(check for check in payload["checks"] if check["id"] == "SCP-C3")
    assert failure["status"] == "FAIL"
    assert diagnostic in " ".join(failure["details"])
    assert payload["failed"] > 0
    assert "Traceback" not in result.stderr
    assert json.loads((tmp_path / "run" / "imports.json").read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("value", ["[]", "null", '"not an object"'])
def test_context_checker_structurally_invalid_json_is_recorded_failure(context_checker, tmp_path, value):
    path = tmp_path / "invalid.json"
    path.write_text(value, encoding="utf-8")
    result = context_checker._check("T", "bad", lambda: (True, [context_checker._read_json(path)]))
    assert not result.passed
    assert "expected a JSON object" in result.details[0]


def test_context_checker_repeated_main_has_no_accumulated_state(context_checker, capsys, monkeypatch):
    result = context_checker.CheckResult("TEST", "test", True, ["ok"])
    monkeypatch.setattr(context_checker, "run_checks", lambda root: [result])
    assert context_checker.main(["--json"]) == 0
    assert context_checker.main(["--json"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [json.loads(line)["passed"] for line in lines] == [1, 1]


def test_schema_drift_passes_selected_root_and_records_child_failure(context_checker, tmp_path, monkeypatch):
    calls = []

    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Completed()

    monkeypatch.setattr(context_checker.subprocess, "run", fake_run)
    passed, details = context_checker._schema_drift(tmp_path)
    assert passed
    assert calls[0][0] == [context_checker.sys.executable, str(tmp_path / "scripts" / "schema_drift_checker.py")]
    assert calls[0][1]["cwd"] == tmp_path

    class Failed:
        returncode = 1
        stdout = "drift"
        stderr = ""

    monkeypatch.setattr(context_checker.subprocess, "run", lambda *args, **kwargs: Failed())
    passed, details = context_checker._schema_drift(tmp_path)
    assert not passed
    assert "drift" in details[0]

    def launch_failure(*args, **kwargs):
        raise FileNotFoundError("child unavailable")

    monkeypatch.setattr(context_checker.subprocess, "run", launch_failure)
    passed, details = context_checker._schema_drift(tmp_path)
    assert not passed
    assert "could not launch" in details[0]


@pytest.mark.parametrize("child_mode", ["nonzero", "missing", "exception"])
def test_context_checker_cli_records_drift_child_failures(tmp_path, child_mode):
    test_root = tmp_path / child_mode
    scripts = test_root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "ai_context_check.py", scripts / "ai_context_check.py")
    if child_mode == "nonzero":
        (scripts / "schema_drift_checker.py").write_text(
            "import sys\nsys.stderr.write('drift child failed\\n')\nsys.exit(3)\n",
            encoding="utf-8",
        )

    elif child_mode == "exception":
        (scripts / "schema_drift_checker.py").write_text(
            "raise RuntimeError('drift child failed')\n", encoding="utf-8"
        )

    observation = tmp_path / f"{child_mode}-imports.json"
    env = offline_subprocess_env(tmp_path / f"{child_mode}-run")
    env["OFFLINE_IMPORT_OBSERVATION"] = str(observation)
    result = subprocess.run(
        [PYTHON, str(scripts / "ai_context_check.py"), "--repo-root", str(test_root), "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    drift = next(check for check in payload["checks"] if check["id"] == "SCP-C8B")
    assert drift["status"] == "FAIL"
    assert any(
        marker in " ".join(drift["details"])
        for marker in ("drift child failed", "could not launch", "can't open file")
    )
    assert "Traceback" not in result.stderr
    assert json.loads(observation.read_text(encoding="utf-8")) == []


def test_malformed_json_is_a_recorded_failure(context_checker, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    result = context_checker._check("T", "bad", lambda: (True, [context_checker._read_json(path)]))
    assert not result.passed
    assert "JSONDecodeError" in result.details[0]


@pytest.mark.parametrize("dimension", ["project", "company", "cost_center", "department", "branch"])
@pytest.mark.parametrize("exposed", [1, True, "1"])
def test_scope_linter_covers_violations(metadata_linter, tmp_path, dimension, exposed):
    path = tmp_path / "sample.json"
    path.write_text(json.dumps({"name": "Sample", "fields": [
        {"fieldname": dimension, "in_standard_filter": exposed},
        {"fieldname": "unrelated", "in_standard_filter": 1},
    ]}), encoding="utf-8")
    assert metadata_linter.lint_doctype_json(str(path)) == [
        f"FAIL: Sample.json field '{dimension}' has in_standard_filter=1"
    ]


@pytest.mark.parametrize("dimension", ["project", "company", "cost_center", "department", "branch"])
@pytest.mark.parametrize("exposed", [0, False, None, "", "absent"])
def test_scope_linter_permits_unexposed_dimensions(metadata_linter, tmp_path, dimension, exposed):
    field = {"fieldname": dimension}
    if exposed != "absent":
        field["in_standard_filter"] = exposed
    path = tmp_path / "sample.json"
    path.write_text(json.dumps({"name": "Sample", "fields": [
        field, {"fieldname": "unrelated", "in_standard_filter": 1},
    ]}), encoding="utf-8")
    assert metadata_linter.lint_doctype_json(str(path)) == []


def test_scope_linter_reports_malformed_json(metadata_linter, tmp_path):
    path = tmp_path / "sample" / "sample.json"
    path.parent.mkdir()
    path.write_text("not json", encoding="utf-8")
    assert metadata_linter.lint_doctype_json(str(path))[0].startswith("ERROR:")


def test_offline_import_guard_rejects_forbidden_exact_names():
    import importlib

    with pytest.raises(AssertionError):
        importlib.import_module("frappe")
    with pytest.raises(AssertionError):
        importlib.import_module("construction")
    with pytest.raises(AssertionError):
        importlib.import_module("erpnext")


def test_linter_is_path_independent_from_relocated_copy(tmp_path):
    relocated = tmp_path / "copy"
    (relocated / "scripts").mkdir(parents=True)
    (relocated / "construction" / "construction" / "doctype").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "lint_scope_metadata.py", relocated / "scripts" / "lint_scope_metadata.py")
    shutil.copytree(ROOT / "construction" / "construction" / "doctype", relocated / "construction" / "construction" / "doctype", dirs_exist_ok=True)
    observation = tmp_path / "relocated-imports.json"
    env = offline_subprocess_env(tmp_path / "relocated-run")
    env["OFFLINE_IMPORT_OBSERVATION"] = str(observation)
    result = subprocess.run(
        [PYTHON, str(relocated / "scripts" / "lint_scope_metadata.py")],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS:" in result.stdout
    assert json.loads(observation.read_text(encoding="utf-8")) == []


def test_real_gate_is_not_replaced_by_fixture_marker():
    assert (ROOT / "construction" / "hooks.py").is_file()
    assert not os.environ.get("OFFLINE_FIXTURE_GATE")


@pytest.mark.parametrize("error", [FileNotFoundError, PermissionError])
def test_drift_launch_failure_reaches_main_json_report(
    context_checker, tmp_path, monkeypatch, capsys, error
):
    """A process-launch double exercises main/reporting, not the real gate."""
    real_run = subprocess.run
    calls = []

    def fail_drift_launch(args, **kwargs):
        if Path(args[-1]).name == "schema_drift_checker.py":
            calls.append((args, kwargs))
            raise error("drift launch unavailable")
        return real_run(args, **kwargs)

    monkeypatch.setattr(context_checker.subprocess, "run", fail_drift_launch)
    assert context_checker.main(["--repo-root", str(tmp_path), "--json"]) == 1
    output = capsys.readouterr()
    payload = json.loads(output.out)
    drift = next(check for check in payload["checks"] if check["id"] == "SCP-C8B")
    assert drift["status"] == "FAIL"
    assert "could not launch" in " ".join(drift["details"])
    assert error.__name__ in " ".join(drift["details"])
    assert "Traceback" not in output.err
    assert calls[0][0] == [PYTHON, str(tmp_path / "scripts" / "schema_drift_checker.py")]
    assert calls[0][1]["cwd"] == tmp_path


@pytest.mark.parametrize("forbidden", ["construction", "frappe", "erpnext"])
def test_cli_subprocess_guard_rejects_and_records_imports(tmp_path, forbidden):
    result = subprocess.run(
        [PYTHON, "-c", f"import {forbidden}"],
        cwd=tmp_path,
        env=offline_subprocess_env(tmp_path),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert f"offline subprocess attempted forbidden import: {forbidden}" in result.stderr
    assert json.loads((tmp_path / "imports.json").read_text(encoding="utf-8")) == [forbidden]
