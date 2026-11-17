"""Process-local test-root state.

Only the first execution of ``dashboard/tests/conftest.py`` sets ``ROOT``. A
duplicate import of that conftest under a second module name reuses this
module object rather than an environment-supplied path.
"""

ROOT = None
