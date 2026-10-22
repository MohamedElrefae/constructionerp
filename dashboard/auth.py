"""Authentication and security module for the Civil Engineer Dashboard.

Provides:
- scrypt password hashing with explicit parameters (n=16384, r=8, p=1, dklen=64)
- Kernel-level atomic credential file creation (0600, O_EXCL, O_NOFOLLOW) with auto-removal
- Outermost Host-header validation middleware mitigating GHSA-86qp-5c8j-p5mr
- Double-submit CSRF cookie protection for unauthenticated login and mutating endpoints
- Origin/Referer verification
- In-memory session management
- Login rate-limiting (429 after 5 failures in 5 min)
"""

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from dashboard.config import (
    ALLOWED_HOSTS,
    AUTH_STORE_PATH,
    CREDENTIALS_FILE_PATH,
    CSRF_COOKIE_NAME,
    LOGIN_RATE_LIMIT_WINDOW,
    MAX_LOGIN_FAILURES,
    SCRYPT_DKLEN,
    SCRYPT_MAXMEM,
    SCRYPT_N,
    SCRYPT_P,
    SCRYPT_R,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    VAR_DIR,
)

HOST_REGEX = re.compile(r"^[a-zA-Z0-9.\-]+(:[0-9]+)?$")


# ---------------------------------------------------------------------------
# Password Hashing via hashlib.scrypt
# ---------------------------------------------------------------------------


def hash_password(
    password: str,
    salt: bytes | None = None,
    n: int = SCRYPT_N,
    r: int = SCRYPT_R,
    p: int = SCRYPT_P,
    maxmem: int = SCRYPT_MAXMEM,
    dklen: int = SCRYPT_DKLEN,
) -> str:
    """Hash password using scrypt with explicit parameters.

    Format: scrypt$<n>$<r>$<p>$<salt_hex>$<hash_hex>
    """
    if salt is None:
        salt = os.urandom(16)
    pw_bytes = password.encode("utf-8")
    derived = hashlib.scrypt(
        pw_bytes,
        salt=salt,
        n=n,
        r=r,
        p=p,
        maxmem=maxmem,
        dklen=dklen,
    )
    return f"scrypt${n}${r}${p}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored scrypt hash in constant time."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected_hex = parts[5]

        computed = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=SCRYPT_MAXMEM,
            dklen=len(bytes.fromhex(expected_hex)),
        )
        return hmac.compare_digest(computed.hex(), expected_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Initial Credential Management
# ---------------------------------------------------------------------------


def create_initial_credentials_file(
    file_path: Path = CREDENTIALS_FILE_PATH,
    username: str = "engineer",
    password_len: int = 24,
) -> tuple[str, str]:
    """Atomically create initial credentials file with 0600 permissions.

    Uses os.open with O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW.
    Returns (username, password).
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    password = secrets.token_urlsafe(18)[:password_len]
    content = f"Username: {username}\nPassword: {password}\n"

    # Use os.open with kernel-level flags
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(file_path), flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise

    return username, password


def remove_initial_credentials_file(file_path: Path = CREDENTIALS_FILE_PATH) -> bool:
    """Safely unlink initial credentials file if it exists."""
    p = Path(file_path)
    try:
        if p.is_file() or p.is_symlink():
            p.unlink()
            return True
    except OSError:
        pass
    return False


class AuthStore:
    """Persistent storage for dashboard user accounts."""

    def __init__(
        self,
        store_path: Path = AUTH_STORE_PATH,
        credentials_file_path: Path = CREDENTIALS_FILE_PATH,
    ):
        self.store_path = Path(store_path)
        self.credentials_file_path = Path(credentials_file_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        if not self.store_path.is_file():
            # First run: create initial credentials if not already created
            if self.credentials_file_path.is_file():
                content = self.credentials_file_path.read_text(encoding="utf-8")
                username = "engineer"
                password = ""
                for line in content.splitlines():
                    if line.startswith("Username:"):
                        username = line.split(":", 1)[1].strip()
                    elif line.startswith("Password:"):
                        password = line.split(":", 1)[1].strip()
            else:
                username, password = create_initial_credentials_file(file_path=self.credentials_file_path)

            pw_hash = hash_password(password)
            data = {
                "users": {
                    username: {
                        "password_hash": pw_hash,
                        "created_utc": datetime.now(timezone.utc).isoformat(),
                        "is_initial": True,
                    }
                }
            }
            tmp_path = self.store_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_path.replace(self.store_path)

    def _load_data(self) -> dict[str, Any]:
        if not self.store_path.is_file():
            return {"users": {}}
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"users": {}}

    def _save_data(self, data: dict[str, Any]) -> None:
        tmp_path = self.store_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(self.store_path)

    def verify_user(self, username: str, password: str) -> bool:
        data = self._load_data()
        user_record = data.get("users", {}).get(username)
        if not user_record:
            return False
        return verify_password(password, user_record.get("password_hash", ""))

    def user_exists(self, username: str) -> bool:
        data = self._load_data()
        return username in data.get("users", {})

    def is_initial_user(self, username: str) -> bool:
        data = self._load_data()
        user_record = data.get("users", {}).get(username)
        if not user_record:
            return False
        return bool(user_record.get("is_initial", False))

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        data = self._load_data()
        user_record = data.get("users", {}).get(username)
        if not user_record:
            return False
        if not verify_password(old_password, user_record.get("password_hash", "")):
            return False
        if len(new_password) < 12:
            raise ValueError("New permanent password must be at least 12 characters long")
        if old_password == new_password:
            raise ValueError("New permanent password must be different from current password")

        new_hash = hash_password(new_password)
        user_record["password_hash"] = new_hash
        user_record["is_initial"] = False
        user_record["updated_utc"] = datetime.now(timezone.utc).isoformat()
        data["users"][username] = user_record
        self._save_data(data)
        return True


# Global auth store instance
auth_store = AuthStore()


# ---------------------------------------------------------------------------
# In-Memory Session Management
# ---------------------------------------------------------------------------


class SessionManager:
    """Manages authenticated sessions with expiration."""

    def __init__(self, max_age_seconds: int = SESSION_MAX_AGE_SECONDS):
        self.max_age_seconds = max_age_seconds
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        self._sessions[token] = {
            "username": username,
            "created_utc": now.isoformat(),
            "expires_utc": (now + timedelta(seconds=self.max_age_seconds)).isoformat(),
        }
        return token

    def get_session(self, token: str | None) -> dict[str, Any] | None:
        if not token or token not in self._sessions:
            return None
        session = self._sessions[token]
        expires_at = datetime.fromisoformat(session["expires_utc"])
        if datetime.now(timezone.utc) > expires_at:
            del self._sessions[token]
            return None
        return session

    def delete_session(self, token: str | None) -> bool:
        if token and token in self._sessions:
            del self._sessions[token]
            return True
        return False


session_manager = SessionManager()


# ---------------------------------------------------------------------------
# Rate Limiting for Login Attempts
# ---------------------------------------------------------------------------


class LoginRateLimiter:
    """Tracks failed login attempts per client IP."""

    def __init__(
        self,
        max_failures: int = MAX_LOGIN_FAILURES,
        window_seconds: int = LOGIN_RATE_LIMIT_WINDOW,
    ):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, list[datetime]] = {}

    def is_rate_limited(self, client_ip: str) -> bool:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        attempts = [t for t in self._failures.get(client_ip, []) if t > cutoff]
        self._failures[client_ip] = attempts
        return len(attempts) >= self.max_failures

    def record_failure(self, client_ip: str) -> None:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        attempts = [t for t in self._failures.get(client_ip, []) if t > cutoff]
        attempts.append(now)
        self._failures[client_ip] = attempts

    def reset(self, client_ip: str) -> None:
        if client_ip in self._failures:
            del self._failures[client_ip]


rate_limiter = LoginRateLimiter()


# ---------------------------------------------------------------------------
# ASGI Middlewares
# ---------------------------------------------------------------------------


class HostValidationMiddleware:
    """Outermost raw ASGI middleware enforcing strict Host-header validation.

    Mitigates GHSA-86qp-5c8j-p5mr (BadHost in Starlette <= 1.0.0).
    Runs before any Starlette request parsing or URL reconstruction.
    """

    def __init__(self, app: Any, allowed_hosts: set[str] | None = None):
        self.app = app
        self.allowed_hosts = allowed_hosts or ALLOWED_HOSTS

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            host_header_bytes = headers.get(b"host")
            if not host_header_bytes:
                await self._send_400(send, "Missing Host header")
                return

            try:
                host_str = host_header_bytes.decode("ascii")
            except UnicodeDecodeError:
                await self._send_400(send, "Malformed Host header")
                return

            # Check strict regex: alphanumeric, dots, hyphens, optional colon and port
            if not HOST_REGEX.match(host_str):
                await self._send_400(send, "Invalid Host header characters")
                return

            # Check explicit allowlist
            if host_str not in self.allowed_hosts:
                await self._send_400(send, f"Disallowed Host: {host_str}")
                return

        await self.app(scope, receive, send)

    async def _send_400(self, send: Callable, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 400,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )


class OriginAndCSRFMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing Origin/Referer and double-submit CSRF for mutating requests."""

    ALLOWED_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "testserver"}

    def _is_loopback_origin(self, origin_or_referer: str | None) -> bool:
        if not origin_or_referer:
            return False
        clean = origin_or_referer
        if "://" in clean:
            clean = clean.split("://", 1)[1]
        host = clean.split("/", 1)[0].split(":", 1)[0]
        return host in self.ALLOWED_ORIGIN_HOSTS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # 1. Origin / Referer validation
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            if not (self._is_loopback_origin(origin) or self._is_loopback_origin(referer)):
                return JSONResponse(
                    {"detail": "Invalid or missing Origin/Referer header"},
                    status_code=403,
                )

            # 2. Double-submit cookie CSRF validation
            csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
            csrf_header = request.headers.get("x-csrf-token")

            if not csrf_cookie or not csrf_header:
                return JSONResponse(
                    {"detail": "Missing CSRF cookie or X-CSRF-Token header"},
                    status_code=403,
                )

            if not hmac.compare_digest(csrf_cookie, csrf_header):
                return JSONResponse(
                    {"detail": "CSRF token mismatch"},
                    status_code=403,
                )

        return await call_next(request)


class SessionAuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware identifying authenticated session and setting request.state.user."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        session = session_manager.get_session(session_token)
        if session:
            request.state.user = session["username"]
        else:
            request.state.user = None
        return await call_next(request)
