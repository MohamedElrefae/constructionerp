"""Configuration settings for the Civil Engineer Dashboard."""

import os
from pathlib import Path

# Base paths
DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent

DASHBOARD_TEST_MODE = os.environ.get("DASHBOARD_TEST_MODE") == "1"

if DASHBOARD_TEST_MODE and "DASHBOARD_TEST_ROOT" in os.environ:
    VAR_DIR = (Path(os.environ["DASHBOARD_TEST_ROOT"]).resolve() / "dashboard" / "var")
    REGISTRY_DB_PATH = (VAR_DIR / "registry.db").resolve()
elif DASHBOARD_TEST_MODE and "DASHBOARD_REGISTRY_DB" in os.environ:
    REGISTRY_DB_PATH = Path(os.environ["DASHBOARD_REGISTRY_DB"]).resolve()
    VAR_DIR = REGISTRY_DB_PATH.parent
else:
    # Production Invariant: strictly fixed derived path
    VAR_DIR = (DASHBOARD_DIR / "var").resolve()
    REGISTRY_DB_PATH = (VAR_DIR / "registry.db").resolve()

VAR_DIR.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(VAR_DIR, 0o700)
except Exception:
    pass

CANONICAL_REGISTRY_PATH = REGISTRY_DB_PATH
LOCKS_DIR = (VAR_DIR / "locks").resolve()
LOCKS_DIR.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(LOCKS_DIR, 0o700)
except Exception:
    pass

CREDENTIALS_FILE_PATH = Path(os.environ.get("DASHBOARD_CREDENTIALS_FILE", str(VAR_DIR / "initial_credentials.txt"))).resolve()
AUTH_STORE_PATH = Path(os.environ.get("DASHBOARD_AUTH_STORE", str(VAR_DIR / "auth.json"))).resolve()

# Network binding & loopback security
HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("DASHBOARD_PORT", "8080"))
ALLOWED_HOSTS = {
    f"{HOST}:{PORT}",
    f"localhost:{PORT}",
    "127.0.0.1:8080",
    "localhost:8080",
    "127.0.0.1",
    "localhost",
}

def resolve_frappe_bench_root() -> Path:
    """Structurally derive the Frappe bench root with fail-closed semantics."""
    if "FRAPPE_BENCH_ROOT" in os.environ:
        p = Path(os.environ["FRAPPE_BENCH_ROOT"]).resolve()
        if p.is_dir() and (p / "apps").is_dir() and (p / "sites").is_dir():
            return p
        raise RuntimeError(
            f"Configured FRAPPE_BENCH_ROOT='{p}' is invalid: must be a directory containing apps/ and sites/"
        )
    curr = REPO_ROOT.resolve()
    while curr != curr.parent:
        if (curr / "apps").is_dir() and (curr / "sites").is_dir():
            return curr
        curr = curr.parent
    raise RuntimeError(
        f"Cannot structurally resolve Frappe bench root from REPO_ROOT='{REPO_ROOT}': no ancestor contains apps/ and sites/"
    )

FRAPPE_BENCH_ROOT = resolve_frappe_bench_root()

# Stage 4 Authoritative Manifest Path (Controlling Installation Root)
if DASHBOARD_TEST_MODE and "STAGE4_TEST_MANIFEST_PATH" in os.environ:
    STAGE4_AUTHORITATIVE_MANIFEST_PATH = Path(os.environ["STAGE4_TEST_MANIFEST_PATH"]).resolve()
else:
    STAGE4_AUTHORITATIVE_MANIFEST_PATH = (
        FRAPPE_BENCH_ROOT / "apps" / "construction" / "construction" / "data" / "localization" / "stage4_export_manifest.json"
    ).resolve()

# Worktree containment settings
WORKTREES_ROOT = Path(os.environ.get("WORKTREES_ROOT", str(FRAPPE_BENCH_ROOT / "worktrees"))).resolve()
BASE_ALLOWED_ROOTS = [
    WORKTREES_ROOT,
    FRAPPE_BENCH_ROOT,
]

# Orchestrator paths
ORCHESTRATOR_ROOT = Path(os.environ.get("ORCHESTRATOR_ROOT", str(REPO_ROOT))).resolve()
ORCHESTRATOR_PYTHON = Path(
    os.environ.get(
        "ORCHESTRATOR_PYTHON",
        str(ORCHESTRATOR_ROOT / "orchestrator" / ".venv" / "bin" / "python")
    )
).absolute()

# Chrome binary for Playwright DOM testing
CHROME_BIN = os.environ.get("CHROME_BIN", "/usr/bin/google-chrome")

# Session & Authentication
SESSION_COOKIE_NAME = "dashboard_session"
CSRF_COOKIE_NAME = "dashboard_csrf"
SESSION_MAX_AGE_SECONDS = 3600  # 1 hour
MAX_LOGIN_FAILURES = 5
LOGIN_RATE_LIMIT_WINDOW = 300  # 5 minutes

# Subprocess client limits
SUBPROCESS_TIMEOUT_SECONDS = 10.0
MAX_CONCURRENT_SUBPROCESSES = 4

# Scrypt parameters (explicit and robust)
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 33554432
SCRYPT_DKLEN = 64
