#!/usr/bin/env python3
"""Narrow root-owned verifier for cross-UID managed-service observations.

This daemon is a candidate only. It has one fixed socket, one fixed config,
one fixed three-byte request and a bounded two-byte decision. It has no shell,
filesystem/path arguments, provider access or privileged mutation API.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import stat
import struct
import sys

try:
    from ..managed_supervisor_attestation import (
        AttestationError,
        verify_local_service_attestation,
    )
except ImportError:
    from managed_supervisor_attestation import (
        AttestationError,
        verify_local_service_attestation,
    )


SOCKET_PATH = Path("/run/managed-attestation-verifier/verify.sock")
CONFIG_PATH = Path("/run/managed-supervisor-attestation/record.json")
SOCKET_DIR = SOCKET_PATH.parent
REQUEST = b"V1\n"
ACCEPT = b"OK\n"
DENY = b"NO\n"
MAX_REQUEST = 4
CLIENT_TIMEOUT = 0.75


class VerifierError(RuntimeError):
    """Verifier could not establish the required service identity."""


def _peer_credentials(conn):
    if not hasattr(socket, "SO_PEERCRED"):
        raise VerifierError("Unix peer credentials unavailable")
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        return struct.unpack("3i", raw)
    except (OSError, struct.error):
        raise VerifierError("Unix peer credentials are uninspectable") from None


def _read_exact_request(conn) -> bytes:
    conn.settimeout(CLIENT_TIMEOUT)
    data = bytearray()
    while len(data) < MAX_REQUEST:
        part = conn.recv(MAX_REQUEST - len(data))
        if not part:
            break
        data.extend(part)
    if bytes(data) != REQUEST:
        raise VerifierError("request must be the fixed V1 frame")
    return bytes(data)


def verify_request(conn, *, verifier=verify_local_service_attestation,
                   config_path=CONFIG_PATH):
    """Authorize a single request; all failures map to a generic deny."""
    try:
        peer_pid, peer_uid, _peer_gid = _peer_credentials(conn)
        if peer_pid <= 0 or peer_uid <= 0:
            raise VerifierError("invalid peer identity")
        _read_exact_request(conn)
        verifier(config_path, supervisor_pid=peer_pid, supervisor_uid=peer_uid)
        return True
    except Exception:
        return False


def _prepare_socket(path=SOCKET_PATH, *, group_name="managed-supervisor"):
    if os.geteuid() != 0:
        raise VerifierError("verifier daemon must run as root")
    if Path(path) != SOCKET_PATH:
        raise VerifierError("verifier socket path is fixed")
    try:
        directory = path.parent.lstat()
    except OSError:
        raise VerifierError("verifier socket directory must be provisioned") from None
    if (not stat.S_ISDIR(directory.st_mode) or stat.S_ISLNK(directory.st_mode)
            or directory.st_uid != 0 or directory.st_mode & 0o027):
        raise VerifierError("verifier socket directory ownership or mode is unsafe")
    try:
        import grp
        gid = grp.getgrnam(group_name).gr_gid
    except (ImportError, KeyError):
        raise VerifierError("managed-supervisor group is not provisioned") from None
    if path.exists() or path.is_symlink():
        raise VerifierError("refusing to replace an existing verifier socket path")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(str(path))
        os.chown(path, 0, gid, follow_symlinks=False)
        os.chmod(path, 0o660, follow_symlinks=False)
        listener.listen(8)
        listener.settimeout(1.0)
        return listener
    except Exception:
        listener.close()
        try:
            if path.is_socket():
                path.unlink()
        except OSError:
            pass
        raise


def serve_forever(*, path=SOCKET_PATH, group_name="managed-supervisor"):
    listener = _prepare_socket(path, group_name=group_name)
    try:
        while True:
            try:
                conn, _address = listener.accept()
            except socket.timeout:
                continue
            with conn:
                conn.settimeout(CLIENT_TIMEOUT)
                allowed = verify_request(conn)
                try:
                    conn.sendall(ACCEPT if allowed else DENY)
                    conn.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
    finally:
        listener.close()
        try:
            metadata = path.lstat()
            if stat.S_ISSOCK(metadata.st_mode) and metadata.st_uid == 0:
                path.unlink()
        except OSError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", required=True)
    args = parser.parse_args(argv)
    if not args.serve:
        return 2
    try:
        serve_forever()
    except (OSError, VerifierError, AttestationError) as exc:
        print(f"managed attestation verifier failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
