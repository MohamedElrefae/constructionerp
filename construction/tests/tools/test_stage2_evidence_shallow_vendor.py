#!/usr/bin/env python3
"""Regression guard: the protocol fixture must survive the CI vendor shape.

The required Stage-2 protocol job checks the pinned vendor catalogs out with
``actions/checkout`` and ``--depth=1`` plus ``--filter=blob:none`` (the
sparse catalog needs the blob filter), so the pinned vendor checkout the
protocol runs against is a SHALLOW, blob-filtered partial clone.

The fixture used to obtain that checkout with
``git clone --quiet --shared --no-checkout <vendor> <target>``. Against such a
source that command cannot work:

* git drops the local/alternates path for a shallow source and falls back to a
  transport clone, so the alternates the flag asks for are never set up;
* the server side of that transport clone is ``git upload-pack`` on a
  blobless repository and upload-pack disables lazy fetching, so it cannot
  serve the missing blobs and the clone dies with exit code 128.

The required CI job therefore failed in ``setUpClass`` with an opaque
``CalledProcessError ... exit status 128`` (the captured stderr was swallowed).
This module builds a vendor checkout with exactly that shape and proves that:

  * the legacy clone transport cannot serve such a source,
  * the fixture builds the synthetic vendor tree from it (the CI path works),
  * the synthetic tree is self-contained (it borrows nothing from the source),
  * a vendor that does not carry the pinned commit fails closed,
  * a vendor that does not carry the pinned catalog fails closed,
  * a failed git command is reported with its command, exit code and stderr.

Every vendor checkout here is SYNTHETIC: no site, no network, no real vendor
checkout is read or written.

Run standalone:
    python3 construction/tests/tools/test_stage2_evidence_shallow_vendor.py
"""

import hashlib
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage2_evidence_fixtures as fx

FRAPPE_PO_REL = "frappe/locale/ar.po"
ERPNEXT_PO_REL = "erpnext/locale/ar.po"
FRAPPE_PO_BYTES = b'# SYNTHETIC TEST FIXTURE frappe catalog\nmsgid "a"\nmsgstr "b"\n'
ERPNEXT_PO_BYTES = b'# SYNTHETIC TEST FIXTURE erpnext catalog\nmsgid "c"\nmsgstr "d"\n'


def _git(args, cwd=None, stdin=None, check=True):
    """Run a git command for the fixture; report both streams when it fails."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        input=stdin,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed with exit code {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout.decode('utf-8', 'replace')}\n"
            f"--- stderr ---\n{proc.stderr.decode('utf-8', 'replace')}"
        )
    return proc


def _build_ci_shaped_vendor(root, app, po_rel, po_bytes):
    """Create a vendor checkout with the shape actions/checkout leaves in CI.

    The result is: a shallow repository (``.git/shallow``), a blob-filtered
    partial clone (one blob of the pinned commit is absent and the repository
    is marked as a promisor repository), a sparse checkout and a detached HEAD.

    Such a source cannot be cloned, which is exactly what made the required
    CI job fail.
    """
    repo = Path(root) / app
    repo.mkdir(parents=True, exist_ok=True)
    _git(["init", "--quiet", str(repo)])
    for key, value in (
        ("user.email", "stage2-fixture@example.invalid"),
        ("user.name", "Stage2 Fixture"),
        ("core.sparseCheckout", "true"),
        ("core.repositoryformatversion", "1"),
        ("extensions.partialClone", "origin"),
        ("remote.origin.promisor", "true"),
        ("remote.origin.partialclonefilter", "blob:none"),
        ("remote.origin.url", str(repo / ".git" / "absent-promisor")),
    ):
        _git(["-C", str(repo), "config", key, value])
    info = repo / ".git" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "sparse-checkout").write_text(po_rel + "\n", encoding="utf-8")

    # The catalog blob is present; a second blob of the same commit is
    # deliberately NOT written: the repository is blob filtered.
    po_blob = (
        _git(["-C", str(repo), "hash-object", "-w", "--stdin"], stdin=po_bytes).stdout.decode("ascii").strip()
    )
    filtered_blob = (
        _git(["-C", str(repo), "hash-object", "--stdin"], stdin=b"blob filtered out\n")
        .stdout.decode("ascii")
        .strip()
    )

    def mktree(entries):
        payload = "".join(f"{mode} {kind} {sha}\t{name}\n" for mode, kind, sha, name in entries)
        return (
            _git(["-C", str(repo), "mktree", "--missing"], stdin=payload.encode("utf-8"))
            .stdout.decode("ascii")
            .strip()
        )

    parts = po_rel.split("/")
    entries = [("100644", "blob", po_blob, parts[-1])]
    for dirname in reversed(parts[:-1]):
        entries = [("040000", "tree", mktree(entries), dirname)]
    root_tree = mktree([*entries, ("100644", "blob", filtered_blob, "filtered-out.txt")])
    commit = (
        _git(["-C", str(repo), "commit-tree", root_tree, "-m", "synthetic pinned vendor commit"])
        .stdout.decode("ascii")
        .strip()
    )

    # The shallow boundary and the detached HEAD, exactly like actions/checkout.
    (repo / ".git" / "shallow").write_text(commit + "\n", encoding="utf-8")
    _git(["-C", str(repo), "update-ref", "--no-deref", "HEAD", commit])
    po_path = repo / po_rel
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po_path.write_bytes(po_bytes)
    return repo, commit


class TestStage2ShallowVendor(unittest.TestCase):
    """The protocol fixture must work against the CI shape of the pinned vendor."""

    maxDiff = None

    def setUp(self):
        self.tmp = fx.make_tmp_root("stage2-shallow-vendor-")
        self.addCleanup(fx.remove_tmp_root, self.tmp)

    def _vendor_apps(self, name="vendor-apps"):
        """A bench-shaped vendor directory holding two CI-shaped checkouts."""
        base = self.tmp / name
        _frappe, frappe_commit = _build_ci_shaped_vendor(base, "frappe", FRAPPE_PO_REL, FRAPPE_PO_BYTES)
        _erpnext, erpnext_commit = _build_ci_shaped_vendor(base, "erpnext", ERPNEXT_PO_REL, ERPNEXT_PO_BYTES)
        pins = {
            "frappe": {
                "commit": frappe_commit,
                "po_sha": hashlib.sha256(FRAPPE_PO_BYTES).hexdigest(),
            },
            "erpnext": {
                "commit": erpnext_commit,
                "po_sha": hashlib.sha256(ERPNEXT_PO_BYTES).hexdigest(),
            },
        }
        return base, pins

    def _synthetic_tree(self, app):
        return self.tmp / fx.BENCH_DIRNAME / "apps" / app

    def test_the_legacy_clone_transport_cannot_serve_a_shallow_blobless_vendor(self):
        """Characterise the CI failure: the legacy transport cannot clone this source.

        The legacy transport was ``git clone --quiet --shared --no-checkout``.
        The assertion is deliberately about what the protocol needs (a vendor
        tree that carries the pinned commit AND can serve the pinned catalog),
        so it stays truthful if a future git release changes the failure mode.
        """
        base, pins = self._vendor_apps()
        target = self.tmp / "legacy-target"
        commit = pins["frappe"]["commit"]
        clone = _git(
            ["clone", "--quiet", "--shared", "--no-checkout", str(base / "frappe"), str(target)],
            check=False,
        )
        usable = False
        if clone.returncode == 0:
            head = _git(["-C", str(target), "rev-parse", "HEAD"], check=False)
            catalog = _git(
                ["-C", str(target), "cat-file", "blob", f"{commit}:{FRAPPE_PO_REL}"],
                check=False,
            )
            usable = head.returncode == 0 and catalog.returncode == 0
        self.assertFalse(
            usable,
            "the legacy --shared clone transport unexpectedly served a shallow, "
            "blob-filtered vendor checkout; the root cause of the CI failure has "
            "changed and this characterisation must be re-reviewed",
        )

    def test_the_fixture_builds_the_synthetic_vendor_from_a_shallow_blobless_vendor(self):
        """The CI path: the fixture must build the vendor tree from a CI-shaped checkout."""
        base, pins = self._vendor_apps()
        candidate, head = fx.build_candidate_root(self.tmp, fx.REPO_ROOT, base, pins=pins)
        self.assertTrue(candidate.is_dir())
        self.assertEqual(head, fx.git_text("rev-parse", "HEAD", cwd=fx.REPO_ROOT))
        for app, po_rel, po_bytes in (
            ("frappe", FRAPPE_PO_REL, FRAPPE_PO_BYTES),
            ("erpnext", ERPNEXT_PO_REL, ERPNEXT_PO_BYTES),
        ):
            tree = self._synthetic_tree(app)
            self.assertTrue((tree / ".git").is_dir(), f"{app}: no synthetic vendor repository")
            self.assertEqual(
                fx.git_text("rev-parse", "HEAD", cwd=tree),
                pins[app]["commit"],
                f"{app}: the synthetic vendor HEAD is not the pinned commit",
            )
            self.assertEqual((tree / po_rel).read_bytes(), po_bytes, f"{app}: catalog bytes")
            self.assertEqual(
                fx.sha256_file(tree / po_rel),
                pins[app]["po_sha"],
                f"{app}: the synthetic catalog is not the pinned digest",
            )

    def test_the_synthetic_vendor_tree_is_self_contained(self):
        """The synthetic tree borrows nothing from the source checkout."""
        base, pins = self._vendor_apps()
        fx.build_candidate_root(self.tmp, fx.REPO_ROOT, base, pins=pins)
        tree = self._synthetic_tree("frappe")
        alternates = tree / ".git" / "objects" / "info" / "alternates"
        self.assertFalse(
            alternates.exists(),
            "the synthetic vendor tree must not borrow the source's object store",
        )
        # The source may disappear: the synthetic tree still resolves.
        shutil.rmtree(base)
        self.assertEqual(
            fx.git_text("rev-parse", "HEAD", cwd=tree),
            pins["frappe"]["commit"],
            "the synthetic vendor HEAD must survive the source checkout",
        )
        self.assertEqual((tree / FRAPPE_PO_REL).read_bytes(), FRAPPE_PO_BYTES)

    def test_a_vendor_without_the_pinned_commit_fails_closed(self):
        """A vendor that does not carry the pinned commit must be refused."""
        base, _pins = self._vendor_apps()
        absent = "0" * 40
        with self.assertRaises(RuntimeError) as caught:
            fx.build_vendor_tree(base / "frappe", self.tmp / "out", absent, FRAPPE_PO_REL)
        self.assertIn(absent, str(caught.exception))

    def test_a_vendor_without_the_pinned_catalog_fails_closed(self):
        """A vendor that does not carry the pinned catalog must be refused."""
        base, pins = self._vendor_apps()
        absent_rel = "frappe/locale/absent.po"
        with self.assertRaises(RuntimeError) as caught:
            fx.build_vendor_tree(base / "frappe", self.tmp / "out", pins["frappe"]["commit"], absent_rel)
        message = str(caught.exception)
        self.assertIn(absent_rel, message)
        self.assertIn("stderr", message)

    def test_a_failed_git_command_reports_the_command_and_stderr(self):
        """A failed git command must be diagnosable, not an opaque exit status."""
        with self.assertRaises(RuntimeError) as caught:
            fx.run_git(["cat-file", "blob", "not-a-commit"], what="probe")
        message = str(caught.exception)
        self.assertIn("cat-file", message)
        self.assertIn("exit code", message)
        self.assertIn("stderr", message)


if __name__ == "__main__":
    unittest.main()
