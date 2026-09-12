"""Keep offline tests honest: no app or Frappe imports are available."""

import importlib.abc
import sys


FORBIDDEN_PREFIXES = ("construction", "frappe", "erpnext")


class ForbiddenImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in FORBIDDEN_PREFIXES or fullname.startswith(
            tuple(f"{name}." for name in FORBIDDEN_PREFIXES)
        ):
            raise AssertionError(f"offline test attempted forbidden import: {fullname}")
        return None


assert not any(
    name == prefix or name.startswith(f"{prefix}.")
    for name in sys.modules
    for prefix in FORBIDDEN_PREFIXES
), "forbidden app package already loaded during offline collection"
sys.meta_path.insert(0, ForbiddenImport())
