"""Tests for authentication, scrypt hashing, atomic credential management, and Host-header validation."""

import os
from pathlib import Path
import stat
import pytest
import httpx

from dashboard.auth import (
    AuthStore,
    HostValidationMiddleware,
    auth_store,
    create_initial_credentials_file,
    hash_password,
    rate_limiter,
    remove_initial_credentials_file,
    session_manager,
    verify_password,
)
from dashboard.config import (
    ALLOWED_HOSTS,
    SCRYPT_DKLEN,
    SCRYPT_MAXMEM,
    SCRYPT_N,
    SCRYPT_P,
    SCRYPT_R,
)
from dashboard.app import app


def test_scrypt_hashing_parameters():
    """Verify scrypt hashing uses exact required parameters and format."""
    password = "secret_civil_engineer_password"
    hashed = hash_password(password)

    # Check format: scrypt$16384$8$1$<salt_hex>$<hash_hex>
    parts = hashed.split("$")
    assert len(parts) == 6
    assert parts[0] == "scrypt"
    assert int(parts[1]) == SCRYPT_N == 16384
    assert int(parts[2]) == SCRYPT_R == 8
    assert int(parts[3]) == SCRYPT_P == 1
    salt_bytes = bytes.fromhex(parts[4])
    assert len(salt_bytes) == 16
    hash_bytes = bytes.fromhex(parts[5])
    assert len(hash_bytes) == SCRYPT_DKLEN == 64

    # Verify constant-time match
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password("", hashed) is False


def test_atomic_credential_file_and_autoremoval(tmp_path):
    """Verify atomic credential file creation with 0600 permissions and auto-removal."""
    cred_file = tmp_path / "initial_credentials.txt"
    username, password = create_initial_credentials_file(cred_file, username="test_engineer")

    assert cred_file.is_file()
    assert len(password) == 24
    content = cred_file.read_text(encoding="utf-8")
    assert f"Username: test_engineer\nPassword: {password}\n" == content

    # Verify file mode permissions are 0600 (-rw-------)
    mode = stat.S_IMODE(os.stat(cred_file).st_mode)
    assert mode == 0o600

    # Verify O_EXCL rejection when file already exists
    with pytest.raises(FileExistsError):
        create_initial_credentials_file(cred_file, username="test_engineer")

    # Verify safe auto-removal
    assert remove_initial_credentials_file(cred_file) is True
    assert not cred_file.exists()
    # Second removal returns False without error
    assert remove_initial_credentials_file(cred_file) is False


def test_permanent_password_setup_and_credential_file_removal(tmp_path):
    """Verify that initial credential file is preserved upon login and ONLY deleted upon permanent password setup."""
    cred_file = tmp_path / "initial_credentials.txt"
    auth_file = tmp_path / "auth.json"

    # 1. Create initial credentials file
    username, initial_password = create_initial_credentials_file(cred_file, username="engineer")
    assert cred_file.is_file()

    # 2. Store initial hash with is_initial = True
    store = AuthStore(store_path=auth_file, credentials_file_path=cred_file)
    assert store.is_initial_user("engineer") is True
    assert store.verify_user("engineer", initial_password) is True

    # 3. Simulate login: initial credentials file MUST NOT be deleted during login
    assert cred_file.is_file()

    # 4. Attempt invalid permanent password changes
    # Wrong current password
    assert store.change_password("engineer", "wrong_password", "ValidPermanentPassword123!") is False
    assert cred_file.is_file()

    # Password too short (< 12 chars)
    with pytest.raises(ValueError, match=r"at least 12 characters"):
        store.change_password("engineer", initial_password, "short")
    assert cred_file.is_file()

    # Same password
    with pytest.raises(ValueError, match=r"different from current"):
        store.change_password("engineer", initial_password, initial_password)
    assert cred_file.is_file()

    # 5. Successful permanent password setup
    new_perm_password = "MySecurePermanentPassword2026!"
    assert store.change_password("engineer", initial_password, new_perm_password) is True

    # Initial credentials file is NOW deleted via remove_initial_credentials_file
    assert remove_initial_credentials_file(cred_file) is True
    assert not cred_file.exists()

    # 6. Verify permanent state
    assert store.is_initial_user("engineer") is False
    assert store.verify_user("engineer", new_perm_password) is True
    assert store.verify_user("engineer", initial_password) is False


@pytest.mark.anyio
async def test_host_header_malformed_chars_rejected():
    """Test Host-header validation rejecting malformed headers (GHSA-86qp-5c8j-p5mr)."""
    malformed_hosts = [
        "127.0.0.1:8080/evil",
        "localhost#",
        "127.0.0.1?foo",
        "127.0.0.1@evil.com",
        "127.0.0.1:8080\r\nevil",
        "127.0.0.1:8080 evil",
        "attacker.com:8080",
        "192.168.1.1:8080",
    ]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        for host in malformed_hosts:
            resp = await client.get("/api/auth/csrf-token", headers={"host": host})
            assert resp.status_code == 400
            data = resp.json()
            assert "detail" in data


@pytest.mark.anyio
async def test_host_header_ordering_outermost():
    """Test that malformed Host rejection occurs before route dispatching or 404 handlers."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        # Requesting nonexistent path with malformed host must yield 400 Bad Request (not 404)
        resp = await client.get("/nonexistent-path-12345", headers={"host": "127.0.0.1:8080/exploit"})
        assert resp.status_code == 400


@pytest.mark.anyio
async def test_host_header_valid_loopback_accepted():
    """Test that legitimate loopback Host headers are accepted."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        for valid_host in ["127.0.0.1:8080", "localhost:8080", "127.0.0.1", "localhost"]:
            resp = await client.get("/api/auth/csrf-token", headers={"host": valid_host})
            assert resp.status_code == 200


@pytest.mark.anyio
async def test_unauthenticated_login_csrf_protection():
    """Test double-submit CSRF protection on unauthenticated POST /api/auth/login."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        # 1. Missing CSRF cookie and header -> 403
        resp = await client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "any"},
            headers={"origin": "https://127.0.0.1:8080"},
        )
        assert resp.status_code == 403
        assert "CSRF" in resp.json()["detail"]

        # 2. CSRF token mismatch -> 403
        client.cookies.set("dashboard_csrf", "valid_cookie_token")
        resp = await client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "any"},
            headers={
                "origin": "https://127.0.0.1:8080",
                "x-csrf-token": "mismatched_token",
            },
        )
        assert resp.status_code == 403

        # 3. Invalid Origin -> 403
        resp = await client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "any"},
            headers={
                "origin": "https://evil-attacker.com",
                "x-csrf-token": "valid_cookie_token",
            },
        )
        assert resp.status_code == 403

        # 4. Valid CSRF cookie + header and loopback origin -> passes CSRF check (returns 401 if bad credentials)
        resp = await client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "bad_password"},
            headers={
                "origin": "https://127.0.0.1:8080",
                "x-csrf-token": "valid_cookie_token",
            },
        )
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]


@pytest.mark.anyio
async def test_login_rate_limiting():
    """Test login throttling (429 after 5 failures in 5 minutes)."""
    transport = httpx.ASGITransport(app=app)
    client_ip = "127.0.0.1"
    rate_limiter.reset(client_ip)

    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        client.cookies.set("dashboard_csrf", "test_csrf")
        headers = {
            "origin": "https://127.0.0.1:8080",
            "x-csrf-token": "test_csrf",
        }

        # First 5 failed attempts return 401
        for _ in range(5):
            resp = await client.post(
                "/api/auth/login",
                json={"username": "engineer", "password": "wrong"},
                headers=headers,
            )
            assert resp.status_code == 401

        # 6th attempt must trigger 429 Too Many Requests
        resp = await client.post(
            "/api/auth/login",
            json={"username": "engineer", "password": "wrong"},
            headers=headers,
        )
        assert resp.status_code == 429
        assert "Too many" in resp.json()["detail"]

    rate_limiter.reset(client_ip)
