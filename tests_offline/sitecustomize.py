"""Install an import guard in checker subprocesses used by offline tests."""

import atexit
import importlib.abc
import json
import os
import sys

FORBIDDEN_PREFIXES = ("construction", "frappe", "erpnext")
observed = []


class ForbiddenImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "sitecustomize":
            return None
        if fullname in FORBIDDEN_PREFIXES or fullname.startswith(
            tuple(f"{name}." for name in FORBIDDEN_PREFIXES)
        ):
            observed.append(fullname)
            raise AssertionError(f"offline subprocess attempted forbidden import: {fullname}")
        return None


if any(
    name == prefix or name.startswith(f"{prefix}.") for name in sys.modules for prefix in FORBIDDEN_PREFIXES
):
    raise AssertionError("forbidden app package already loaded in offline subprocess")

sys.meta_path.insert(0, ForbiddenImport())


def _write_observation():
    target = os.environ.get("OFFLINE_IMPORT_OBSERVATION")
    if target:
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(observed, handle)


atexit.register(_write_observation)
