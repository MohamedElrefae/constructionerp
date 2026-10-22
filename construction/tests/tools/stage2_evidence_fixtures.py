"""Synthetic Stage-2 evidence fixtures for the offline protocol round trip.

EVERY artefact produced by this module is a SYNTHETIC TEST FIXTURE. Nothing
here is a real capture, a real gate run, a real site interaction or a real
evidence set. The module synthesises raw captures that satisfy the governed
schema of ``scripts/check_localization_gates.py`` so the
assembler -> checker protocol can be exercised end to end inside a throw-away
directory tree that nobody else owns.

Layout created under the temporary root (three DISTINCT trees):

    <tmp>/synthetic-captures/          raw capture inputs (marked synthetic)
    <tmp>/synthetic-evidence-out/      assembler output (envelopes + index)
    <tmp>/synthetic-bench/apps/construction   candidate root the checker reads
    <tmp>/synthetic-bench/apps/frappe         pinned vendor catalog checkout
    <tmp>/synthetic-bench/apps/erpnext        pinned vendor catalog checkout

The candidate root is a fresh local clone of the checkout under test, detached
at the checkout's own HEAD commit, so the assembled evidence is bound to the
immutable tested HEAD exactly like a real capture set would be.

The two synthetic vendor trees are NOT clones of the pinned vendor checkouts:
the pinned checkouts are shallow, blob-filtered partial clones in CI, which
cannot be cloned at all (see ``build_vendor_tree``). They are built from the
pinned commit object and the pinned catalog bytes of the vendor checkout, so
they stay bound to the pinned vendor commits and the pinned catalog digests.

The timestamp sidecars (``<capture>.start`` / ``<capture>.finish``) cannot
carry the synthetic marker inline: the assembler consumes them verbatim as the
envelope UTC timestamp. Their synthetic nature is declared by the capture
directory manifest (``SYNTHETIC-FIXTURE.txt``) and by the directory names.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SYNTHETIC_MARKER = "SYNTHETIC TEST FIXTURE"
FIXTURE_MANIFEST = "SYNTHETIC-FIXTURE.txt"
CAPTURES_DIRNAME = "synthetic-captures"
OUTPUT_DIRNAME = "synthetic-evidence-out"
BENCH_DIRNAME = "synthetic-bench"
PROTECTED_SITES = ("v16.localhost", "v16rehearsal.localhost")
VENDOR_INPUTS_RELPATH = "construction/data/localization/vendor_ci_inputs.json"


def ci_mode() -> bool:
    """True when the run is a required CI run.

    In CI mode a missing vendor input must FAIL the run; only an explicitly
    labelled local unit layer may skip (and only when it may use a mirror).
    """
    return os.environ.get("STAGE2_PROTOCOL_CI") == "1" or os.environ.get("GITHUB_ACTIONS") == "true"


def load_vendor_inputs(root):
    """The pinned vendor inputs the protocol run requires (repo file)."""
    data = json.loads((Path(root) / VENDOR_INPUTS_RELPATH).read_text(encoding="utf-8"))
    return data["apps"]


class VendorInputsUnavailable(RuntimeError):
    """The mandatory pinned vendor input manifest is absent or unusable."""


def load_required_vendor_inputs(root):
    """The pinned vendor inputs the protocol run requires.

    Raises ``VendorInputsUnavailable`` when the mandatory manifest is absent,
    unreadable or malformed. The required CI must FAIL on that condition; it
    must never skip it and report a green suite.
    """
    path = Path(root) / VENDOR_INPUTS_RELPATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VendorInputsUnavailable(
            f"the mandatory pinned vendor input manifest {VENDOR_INPUTS_RELPATH} is absent "
            f"(expected at {path})"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise VendorInputsUnavailable(
            f"the mandatory pinned vendor input manifest {VENDOR_INPUTS_RELPATH} is unreadable: {exc}"
        ) from exc
    apps = data.get("apps") if isinstance(data, dict) else None
    if not isinstance(apps, dict) or not apps:
        raise VendorInputsUnavailable(
            f"the mandatory pinned vendor input manifest {VENDOR_INPUTS_RELPATH} has no usable 'apps' section"
        )
    return apps


def git(*args, cwd=None, check=True):
    """Run a git command and return its stripped stdout."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed with exit code {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    return proc.stdout.strip()


# Reading a pinned object out of a blob-filtered vendor checkout must never
# reach for the network: a missing object has to fail closed instead of being
# fetched lazily from the promisor remote.
NO_LAZY_FETCH_ENV = {"GIT_NO_LAZY_FETCH": "1"}


def run_git(args, cwd=None, what="", stdin=None, env=None):
    """Run a git command and raise a diagnosable error when it fails.

    ``subprocess.run(..., check=True)`` reports only "returned non-zero exit
    status N" and hides the captured streams, which is exactly how the CI
    failure stayed opaque. Every git invocation of this module goes through
    this helper, so a failure names the command, the exit code, stdout and
    stderr.
    """
    child_env = {**os.environ, **env} if env else None
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        input=stdin,
        capture_output=True,
        check=False,
        env=child_env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "git {cmd} failed with exit code {rc}{what}\n"
            "--- stdout ---\n{out}\n--- stderr ---\n{err}".format(
                cmd=" ".join(args),
                rc=proc.returncode,
                what=f" ({what})" if what else "",
                out=proc.stdout.decode("utf-8", "replace"),
                err=proc.stderr.decode("utf-8", "replace"),
            )
        )
    return proc


def git_text(*args, cwd=None, what=""):
    """Run a git command and return its stdout as stripped text."""
    return run_git(args, cwd=cwd, what=what).stdout.decode("utf-8", "replace").strip()


def git_bytes(*args, cwd=None, what="", stdin=None, env=None):
    """Run a git command and return its stdout as bytes."""
    return run_git(args, cwd=cwd, what=what, stdin=stdin, env=env).stdout


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_checker(root):
    """Import the checker that lives under ``root`` (the candidate under test)."""
    path = Path(root) / "scripts" / "check_localization_gates.py"
    spec = importlib.util.spec_from_file_location("stage2_checker_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def vendor_pins(root):
    """The pinned vendor commits / catalog hashes recorded by the repo."""
    base = json.loads(
        (Path(root) / "construction/data/localization/vendor_catalog_baseline.json").read_text(
            encoding="utf-8"
        )
    )
    return {app: base["apps"][app] for app in ("frappe", "erpnext")}


def vendor_candidates(repo_root):
    """The bench-shaped directories that may hold the pinned vendor checkouts.

    An explicitly supplied vendor directory (``STAGE2_VENDOR_APPS_DIR``) is
    authoritative: the run must never silently validate a different vendor
    tree than the one the caller pinned.
    """
    env = os.environ.get("STAGE2_VENDOR_APPS_DIR")
    if env:
        return [Path(env)]
    repo_root = Path(repo_root)
    return [
        repo_root.parent.parent / "apps",
        repo_root.parent / "apps",
        Path("/home/mohamed/frappe-bench/apps"),
    ]


def locate_vendor_apps(repo_root, pins, required_inputs=None):
    """Locate the pinned vendor checkouts and explain every rejection.

    Returns ``(base, problems)``. ``base`` is the usable bench-shaped
    directory or None. ``problems`` names, for every candidate that was
    rejected, the exact reason: the app directory is absent, the checkout is
    not at the pinned commit, or a required input is absent or carries a
    different digest.

    The reasons are reported per candidate AND per input on purpose. A
    fail-closed report must name the input that actually failed; listing every
    required input as "not found" would misreport inputs that are present and
    correctly digested.
    """
    required_inputs = required_inputs or {}
    problems = []
    for base in vendor_candidates(repo_root):
        missing_apps = [app for app in sorted(pins) if not (base / app).is_dir()]
        if missing_apps:
            problems.append(
                f"{base}: not a bench-shaped vendor directory "
                f"(missing app directory: {', '.join(missing_apps)})"
            )
            continue
        candidate_problems = []
        for app, pin in sorted(pins.items()):
            head = git("rev-parse", "--verify", pin["commit"] + "^{commit}", cwd=base / app, check=False)
            if head != pin["commit"]:
                candidate_problems.append(
                    f"{base}/{app}: HEAD {head or 'unresolvable'} is not the pinned commit "
                    f"{pin['commit']}"
                )
            for rel, want in sorted((required_inputs.get(app) or {}).items()):
                path = base / app / rel
                if not path.is_file():
                    candidate_problems.append(f"{base}/{app}/{rel}: required pinned input is absent")
                    continue
                got = sha256_file(path)
                if got != want:
                    candidate_problems.append(
                        f"{base}/{app}/{rel}: sha256 {got[:12]}… is not the pinned digest " f"{want[:12]}…"
                    )
        if not candidate_problems:
            return base, []
        problems.extend(candidate_problems)
    if not problems:
        problems.append(
            "no bench-shaped vendor checkout with the pinned frappe/erpnext commits was found "
            "(set STAGE2_VENDOR_APPS_DIR)"
        )
    return None, problems


def find_vendor_apps(repo_root, pins, required_inputs=None):
    """Locate a bench-shaped vendor checkout holding the pinned vendor commits.

    Read-only: the located trees are never written to. Returns None when no
    usable vendor checkout is available.

    ``required_inputs`` maps an app name to {relative path: sha256} pairs that
    MUST be present with the recorded digest in the located checkout. A
    checkout that has the right commits but not the right input bytes is not
    usable: the protocol run would then validate a different vendor tree.
    """
    base, _problems = locate_vendor_apps(repo_root, pins, required_inputs)
    return base


def vendor_input_problems(repo_root, pins, required_inputs):
    """Human-readable reasons why no usable vendor checkout was found."""
    _base, problems = locate_vendor_apps(repo_root, pins, required_inputs)
    return problems


def build_vendor_tree(source, target, commit, po_rel):
    """Materialise the synthetic vendor checkout the checker reads.

    ``source`` is the pinned vendor checkout (read-only: it is never written
    to), ``target`` the synthetic bench-shaped directory to create, ``commit``
    the pinned vendor commit and ``po_rel`` the catalog path inside the vendor
    tree.

    The vendor checkout is deliberately NOT cloned. In the required CI the
    pinned catalogs are checked out by ``actions/checkout`` with
    ``--depth=1`` and ``--filter=blob:none``, so that checkout is a SHALLOW,
    blob-filtered partial clone. Such a source cannot be cloned:

    * ``git clone --shared``/``--local`` silently drops the local/alternates
      path for a shallow source (git sets ``is_local = 0`` when the source
      has a ``shallow`` file) and falls back to a transport clone;
    * the server side of that transport clone is ``git upload-pack`` on a
      blobless repository, and upload-pack disables lazy fetching, so it
      cannot serve the missing blobs: the clone dies with exit code 128.

    Instead the pinned commit object is copied out of the source's object
    store with local plumbing - no alternates, no hardlinks, no history copy
    and no network - and the catalog blob is extracted from that very commit.
    The result is a self-contained synthetic vendor tree whose HEAD is the
    pinned commit and whose catalog bytes are the pinned bytes.
    """
    source = Path(source)
    target = Path(target)

    resolved = (
        git_bytes(
            "rev-parse",
            "--verify",
            f"{commit}^{{commit}}",
            cwd=source,
            what=f"verify the pinned commit {commit}",
            env=NO_LAZY_FETCH_ENV,
        )
        .decode("ascii", "replace")
        .strip()
    )
    if resolved != commit:
        raise RuntimeError(
            f"the pinned commit {commit} is not present in the vendor checkout {source} "
            f"(git resolved {resolved or 'nothing'})"
        )

    commit_bytes = git_bytes(
        "cat-file",
        "commit",
        commit,
        cwd=source,
        what=f"read the pinned commit {commit}",
        env=NO_LAZY_FETCH_ENV,
    )

    target.mkdir(parents=True, exist_ok=True)
    run_git(
        ["init", "--quiet", str(target)],
        what=f"create the synthetic vendor repository {target}",
    )
    written = (
        git_bytes(
            "hash-object",
            "-t",
            "commit",
            "-w",
            "--stdin",
            cwd=target,
            what="write the pinned commit object into the synthetic vendor repository",
            stdin=commit_bytes,
        )
        .decode("ascii", "replace")
        .strip()
    )
    if written != commit:
        raise RuntimeError(f"the copied commit object hashes to {written}, not to the pinned {commit}")
    git_text(
        "update-ref",
        "--no-deref",
        "HEAD",
        commit,
        cwd=target,
        what="pin the synthetic vendor HEAD to the pinned commit",
    )

    blob = git_bytes(
        "cat-file",
        "blob",
        f"{commit}:{po_rel}",
        cwd=source,
        what=f"read {po_rel} at the pinned commit {commit}",
        env=NO_LAZY_FETCH_ENV,
    )
    po_path = target / po_rel
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po_path.write_bytes(blob)

    head = git_text("rev-parse", "HEAD", cwd=target, what="read the synthetic vendor HEAD")
    if head != commit:
        raise RuntimeError(f"the synthetic vendor HEAD is {head}, not the pinned {commit}")
    return target


def build_candidate_root(tmp_root, repo_root, vendor_apps, pins=None):
    """Build the candidate root the checker reads (clone at the tested HEAD).

    Returns (candidate_root, head_sha). ``pins`` defaults to the pinned
    vendor commits recorded by the repository; it is an explicit parameter only
    so that the fixture can be exercised against a synthetic vendor.
    """
    apps = Path(tmp_root) / BENCH_DIRNAME / "apps"
    candidate = apps / "construction"
    run_git(
        ["clone", "--quiet", "--local", "--no-hardlinks", str(repo_root), str(candidate)],
        what="clone the candidate root at the tested HEAD",
    )
    head = git_text("rev-parse", "HEAD", cwd=repo_root, what="read the tested HEAD")
    run_git(
        ["-C", str(candidate), "checkout", "--quiet", "--detach", head],
        what="detach the candidate root at the tested HEAD",
    )
    pins = vendor_pins(repo_root) if pins is None else pins
    for app, po_rel in (("frappe", "frappe/locale/ar.po"), ("erpnext", "erpnext/locale/ar.po")):
        source = Path(vendor_apps) / app
        target = apps / app
        build_vendor_tree(source, target, pins[app]["commit"], po_rel)
        want = (pins[app] or {}).get("po_sha")
        if want:
            got = sha256_file(target / po_rel)
            if got != want:
                raise RuntimeError(
                    f"{app}: the catalog written into the synthetic vendor tree has "
                    f"sha256 {got}, not the pinned {want}"
                )
    return candidate, head


def build_captures(
    captures_dir,
    checker,
    candidate_root,
    site,
    now=None,
    contract="current",
    overrides=None,
):
    """Write the synthetic raw capture set consumed by the assembler.

    ``contract`` selects the frozen contract the captures are built from
    ("current" or "legacy"). ``overrides`` deliberately corrupts the captured
    numbers so the gate can be proven to REJECT them:

        {"gate": {"catalog": 1, ...}, "module_counts": {module: n},
         "standalone_count": n}

    Returns the list of capture file names written (content captures first).
    """
    overrides = overrides or {}
    if contract not in checker.CONTRACTS:
        raise ValueError(f"unknown contract {contract!r}")
    spec = checker.CONTRACTS[contract]
    modules = [(m, n) for m, n in spec["modules"]]
    gate = dict(spec["gate"])
    gate.update(overrides.get("gate") or {})
    module_counts = {m: n for m, n in modules}
    module_counts.update(overrides.get("module_counts") or {})
    standalone_count = overrides.get(
        "standalone_count", module_counts["construction.tests.test_localization_gates"]
    )

    caps = Path(captures_dir)
    caps.mkdir(parents=True, exist_ok=True)
    candidate_root = Path(candidate_root)
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    started = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    finished = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    content_files = []
    stamp_files = []

    def write_capture(name, lines):
        path = caps / name
        header = f"# {SYNTHETIC_MARKER} — synthetic capture, not a real capture of any run"
        path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
        content_files.append(name)
        return path

    def write_stamp(name, value):
        path = caps / name
        path.write_text(value + "\n", encoding="utf-8")
        stamp_files.append(name)
        return path

    for stem in (
        "standalone",
        "alltests",
        "dryrun",
        "freshness",
        "fullgate",
        "lints",
        "merkle",
        "scoped",
        "sync",
        "vendor",
    ):
        write_stamp(f"{stem}.start", started)
        write_stamp(f"{stem}.finish", finished)

    # gate-tests-standalone.txt: the governed standalone count of the gate suite.
    write_capture(
        "standalone.out",
        [
            f"Ran {standalone_count} tests in 0.1s",
            "OK",
        ],
    )

    # all-tests.txt: the governed module list and counts, one capture per module.
    total = 0
    for module, _count in modules:
        count = module_counts[module]
        total += count
        write_capture(
            f"mod_{module}.out",
            [
                f"Ran {count} tests in 0.1s",
                "OK",
            ],
        )

    # final-dryrun.txt: the governed dry-run arithmetic.
    dry = dict(checker.EXPECTED_DRYRUN)
    dry.update(overrides.get("dryrun") or {})
    write_capture(
        "dryrun.raw",
        [
            f"In [1]: DRY total={dry['total']} created={dry['created']} updated={dry['updated']} "
            f"skipped={dry['skipped']} drift={dry['drift']}"
        ],
    )

    # full-gate.txt: the governed gate result object.
    write_capture(
        "fullgate.raw",
        [
            "checked="
            + json.dumps(
                {
                    "construction/locale/ar.po": gate["catalog"],
                    "csv_rows": dry["total"],
                    "extract": {
                        "files": gate["files"],
                        "json_labels": gate["json_labels"],
                        "missing": gate["missing"],
                        "wrapped": gate["wrapped"],
                    },
                    "raw_text": {"files": 7, "missing": 0, "texts": 2},
                },
                sort_keys=True,
            )
            + " errors=0"
        ],
    )

    # lints-diffcheck.txt: the governed lint markers.
    write_capture(
        "lints.raw",
        [
            f"PASS: no scope-dimension field has in_standard_filter=1 — {SYNTHETIC_MARKER}",
            "Translation write lint PASSED",
            "DIFFCHECK_CLEAN",
        ],
    )

    # merkle.txt: the live inventory manifest bindings of the candidate root.
    inventory_path = candidate_root / "construction/data/localization/stage2_inventory_manifest.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    merkle = inventory.get("merkle") or {}
    manifest_sha = sha256_file(candidate_root / "construction/data/localization/localization_manifest.json")
    inventory_sha = sha256_file(inventory_path)
    sql_sha = sha256_file(candidate_root / "scripts/stage2_inventory.sql")
    write_capture(
        "merkle.raw",
        [
            "In [1]: MANIFEST: construction/data/localization/stage2_inventory_manifest.json",
            f"In [2]: MANIFEST_SHA256: {manifest_sha}",
            f"In [3]: INVENTORY_MANIFEST_SHA256: {inventory_sha}",
            f"In [4]: MERKLE_ROOT: {merkle.get('root')}",
            f"In [5]: MERKLE_ROWS: {merkle.get('rows')}",
            f"In [6]: SQL_SHA256: {sql_sha}",
        ],
    )

    # scoped-gate.txt: the governed scoped-gate skip note and result line.
    write_capture(
        "scoped.raw",
        [
            "SKIP construction/workspace/construction/construction.json: markup/code blob excluded "
            "from string gate (print/CSS/seed-data; covered by bilingual-output waves + leak detection)",
            'checked={"construction/locale/ar.po": '
            + str(gate["catalog"])
            + ', "extract_scoped": {"files": 2, "json_labels": 0, "missing": 0, "wrapped": 6}, '
            + '"json_labels": '
            + str(gate["json_labels"])
            + "} errors=0",
        ],
    )

    # sync.txt: zero creates/updates plus the recorded site of the capture.
    write_capture(
        "sync.raw",
        [
            "In [2]: SYNC:{'created': 0, 'updated': 0, 'fixture': '"
            + SYNTHETIC_MARKER
            + "', 'cmd': 'bench --site "
            + site
            + " console sync_translation_catalog(dry_run=False)'}"
        ],
    )

    # vendor-audit.txt: a clean vendor audit result.
    write_capture("vendor.raw", ["errors=0"])

    manifest_lines = [
        SYNTHETIC_MARKER,
        "",
        "This directory holds SYNTHETIC raw captures generated by",
        "construction/tests/tools/stage2_evidence_fixtures.py.",
        "They are NOT captures of any site, gate run or test run and must never",
        "be presented as such.",
        "",
        "content captures (each carries the marker inline):",
    ]
    manifest_lines += [f"  {name}" for name in sorted(content_files)]
    manifest_lines += [
        "",
        "timestamp sidecars (bare UTC timestamps: the assembler consumes them",
        "verbatim as the envelope timestamp, so they are marked here instead):",
    ]
    manifest_lines += [f"  {name}" for name in sorted(stamp_files)]
    (caps / FIXTURE_MANIFEST).write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    return sorted(content_files), sorted(stamp_files)


def run_assembler(candidate_root, captures_dir, out_dir, site, extra_args=(), python=None):
    """Run the assembler as a subprocess against the synthetic captures."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    cmd = [
        python or sys.executable,
        str(Path(candidate_root) / "construction/tests/tools/stage2_evidence_assemble.py"),
        f"--captures={captures_dir}",
        f"--out={out_dir}",
        f"--site={site}",
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(candidate_root))


def run_checker(candidate_root, evidence_dir, site, extra_args=(), python=None):
    """Run the checker as a subprocess in site-aware mode against an evidence dir."""
    cmd = [
        python or sys.executable,
        str(Path(candidate_root) / "scripts/check_localization_gates.py"),
        f"--root={candidate_root}",
        f"--evidence-dir={evidence_dir}",
        f"--expected-evidence-site={site}",
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(candidate_root))


def parse_checker_output(stdout):
    """Parse the checker's stdout into (counts, errors, error_count).

    The checker prints one ``FAIL <error>`` line per error and a final
    ``checked=<json> errors=<n>`` summary line.
    """
    counts = {}
    errors = []
    error_count = None
    for line in stdout.splitlines():
        if line.startswith("FAIL "):
            errors.append(line[len("FAIL ") :].strip())
        elif line.startswith("checked="):
            payload = line[len("checked=") :].strip()
            marker = " errors="
            cut = payload.rfind(marker)
            if cut == -1:
                raise AssertionError(f"unparsable checker summary line: {line!r}")
            counts = json.loads(payload[:cut])
            error_count = int(payload[cut + len(marker) :].strip())
    return counts, errors, error_count


def make_tmp_root(prefix):
    """An exclusively owned temporary root; honor the caller's TMPDIR."""
    return Path(tempfile.mkdtemp(prefix=prefix))


def remove_tmp_root(path):
    shutil.rmtree(path, ignore_errors=True)
