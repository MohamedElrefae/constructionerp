"""Exercise the actual Flit backend, including a wheel rebuilt from the sdist."""

import ast
import email
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from candidates import git

ROOT = Path(__file__).resolve().parents[2]


def run(argv, cwd):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def assert_wheel(path):
    with zipfile.ZipFile(path) as wheel:
        names = wheel.namelist()
        assert "construction/__init__.py" in names
        assert not any(
            n.startswith(("orchestrator/", "tests_offline/")) or "/checkpoints.db" in n for n in names
        )
        metadata = email.message_from_bytes(
            wheel.read(next(n for n in names if n.endswith(".dist-info/METADATA")))
        )
        deps = metadata.get_all("Requires-Dist", [])
        assert not any(
            word in dep.lower()
            for dep in deps
            for word in ("langgraph", "pydantic", "pytest", "jsonschema", "flit")
        )


def test_flit_sdist_direct_and_rebuilt_wheel_install(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    archive = tmp_path / "source.tar"
    archive.write_bytes(git(ROOT, "archive", "HEAD"))
    with tarfile.open(archive) as t:
        t.extractall(source, filter="data")
    for name in ("pyproject.toml", "setup.py"):
        shutil.copyfile(ROOT / name, source / name)
    # Deliberately tracked fake packages prove exclusions, not incidental untracked omission.
    for package in ("orchestrator", "tests_offline"):
        (source / package).mkdir(exist_ok=True)
        (source / package / "__init__.py").write_text("UNWANTED_PACKAGE=True\n")
        (source / package / "checkpoints.db").write_text("must not ship")
    git(source, "init", "-b", "packaging-test")
    git(source, "config", "user.email", "test@example.invalid")
    git(source, "config", "user.name", "Packaging Test")
    git(source, "add", ".")
    git(source, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "synthetic packaging fixture")
    out = tmp_path / "dist"
    run([sys.executable, "-m", "build", "--no-isolation", "--sdist", "--wheel", "--outdir", str(out)], source)
    direct = next(out.glob("*.whl"))
    assert_wheel(direct)
    sdist = next(out.glob("*.tar.gz"))
    unpack = tmp_path / "unpack"
    unpack.mkdir()
    with tarfile.open(sdist) as t:
        names = t.getnames()
        assert not any("/orchestrator/" in n or "/tests_offline/" in n for n in names)
        t.extractall(unpack, filter="data")
    rebuilt = tmp_path / "rebuilt"
    run(
        [sys.executable, "-m", "build", "--no-isolation", "--wheel", "--outdir", str(rebuilt)],
        next(unpack.iterdir()),
    )
    wheel = next(rebuilt.glob("*.whl"))
    assert_wheel(wheel)
    env = tmp_path / "install-env"
    run([sys.executable, "-m", "venv", "--without-pip", str(env)], tmp_path)
    uv = shutil.which("uv")
    assert uv, "uv required for isolated no-deps install proof"
    run(
        [
            uv,
            "--cache-dir",
            str(tmp_path / "uv-cache"),
            "pip",
            "install",
            "--python",
            str(env / "bin/python"),
            "--no-deps",
            "--no-index",
            str(wheel),
        ],
        tmp_path,
    )
    # Inspect installation without importing Frappe-dependent construction.__init__.
    run(
        [
            str(env / "bin/python"),
            "-c",
            'import importlib.metadata as m; d=m.distribution("construction"); assert any(str(p)=="construction/__init__.py" for p in d.files); assert not any(str(p).startswith(("orchestrator/","tests_offline/")) for p in d.files)',
        ],
        tmp_path,
    )


def test_retained_setuptools_discovery_excludes_packages(tmp_path):
    source = ast.parse((ROOT / "setup.py").read_text())
    call = next(
        n
        for n in ast.walk(source)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "find_packages"
    )
    exclusions = ast.literal_eval(next(k.value for k in call.keywords if k.arg == "exclude"))
    from setuptools import find_packages

    for name in ("construction", "orchestrator", "tests_offline"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "__init__.py").touch()
    assert find_packages(str(tmp_path), exclude=exclusions) == ["construction"]
