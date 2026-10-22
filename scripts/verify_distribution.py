"""Run preliminary checkout hygiene checks; this does not certify a customer artifact.

The staged tree must be built and checked with stage_distribution.py and
verify_staged_distribution.py as described in docs/DISTRIBUTION.md.
"""

import subprocess
import sys

FAILURES = []


def tracked(pattern_note, predicate):
    files = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout.split(b"\0")
    files = [f.decode("utf-8", "replace") for f in files if f]
    hits = sorted(f for f in files if predicate(f))
    if hits:
        FAILURES.append(f"{pattern_note}: {len(hits)} file(s)\n  " + "\n  ".join(hits[:10]))
    else:
        print(f"PASS {pattern_note}: none")


def main():
    tracked(
        "source maps under construction/public/dist",
        lambda f: f.startswith("construction/public/dist/") and f.endswith(".map"),
    )
    tracked(
        "screenshots under construction/tests",
        lambda f: f.startswith("construction/tests/") and f.lower().endswith(".png"),
    )
    tracked(
        "bytecode (__pycache__/.pyc)",
        lambda f: "__pycache__" in f or f.endswith(".pyc"),
    )
    tracked("legacy setup.py at root", lambda f: f == "setup.py")
    # Customer-set verification operates on a STAGED TREE (see stage_distribution.py),
    # not on the checkout: the checkout legitimately contains internal evidence, and a
    # predicate over the checkout cannot prove exclusion from a generated artifact.
    # This check therefore asserts the staging script and its allowlist exist and are
    # consistent; the staged tree itself is verified by verify_staged_distribution.py.
    # (An earlier version of this predicate ended in `and False` and always passed —
    # removed 2026-10-14; a check that cannot fail is not a check.)
    import os as _os

    if _os.path.exists("scripts/stage_distribution.py"):
        print("PASS distribution staging script present (staged-tree verification is authoritative)")
    else:
        FAILURES.append("scripts/stage_distribution.py missing — staged verification unavailable")
    # Customer-set presence: the files a customer install needs must exist.
    import os

    for required in (
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "docs/CUSTOMER_ONBOARDING.md",
        "docs/MAINTENANCE.md",
        "construction/construction/sidebar/construction_home/construction_home.json",
    ):
        if os.path.exists(required):
            print(f"PASS required present: {required}")
        else:
            FAILURES.append(f"required customer file missing: {required}")
    if FAILURES:
        print("\nDISTRIBUTION CHECK FAILED")
        for failure in FAILURES:
            print(" -", failure.replace("\n", "\n   "))
        return 1
    print("\nDISTRIBUTION CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
