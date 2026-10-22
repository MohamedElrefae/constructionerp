"""Shared path policy for preparing and verifying customer distributions."""

import fnmatch
import os

# Relative to the app root. Keep this policy shared by staging and verification.
NEVER_SHIP = (
    "docs/ai",
    "docs/ai/*",
    "docs/feature_reviews/evidence",
    "docs/feature_reviews/evidence/*",
    "docs/translation",
    "docs/translation/*",
    "docs/scope_context_option_*",
    "orchestrator",
    "orchestrator/*",
    "tests_offline",
    "tests_offline/*",
    "erpnext-mcp-server",
    "erpnext-mcp-server/*",
    "construction/tests",
    "construction/tests/*",
    "construction/data/localization",
    "construction/data/localization/*",
    "construction/data/localization/vendor_delta_*.json",
    "construction/public/dist/*.map",
    "construction/public/dist/**/*.map",
    "construction/public/dist/js/*.map",
    "construction/public/css/theme_*.css",
    "construction/public/css/login_theme.css",
    "**/__pycache__/*",
    "**/__pycache__",
    "**/*.pyc",
    "setup.py",
    "dist",
    "dist/*",
)

LICENSE_CANDIDATES = frozenset({"LICENSE", "LICENSE.txt", "license.txt"})

REQUIRED_CUSTOMER_FILES = frozenset(
    {
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "docs/CUSTOMER_ONBOARDING.md",
        "docs/MAINTENANCE.md",
        "docs/onboarding.md",
        "docs/token_reference.md",
        "docs/BILINGUAL_TASK_GUIDES.md",
        "docs/PERMISSION_SETUP.md",
        ".gitignore",
        ".gitattributes",
    }
)


def normalize(path):
    return path.replace(os.sep, "/")


def never_ships(path):
    path = normalize(path)
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in NEVER_SHIP)


def is_customer_path(path):
    path = normalize(path)
    return path.startswith("construction/") or path in (REQUIRED_CUSTOMER_FILES | LICENSE_CANDIDATES)
