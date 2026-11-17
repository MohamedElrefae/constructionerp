#!/usr/bin/env python3
"""Host-network UNIX-socket broker for allowlisted HTTPS CONNECT tunnels."""

from __future__ import annotations

import argparse
import asyncio
import grp
import ipaddress
import os
import re
import socket
from pathlib import Path
from typing import Awaitable, Callable

MAX_REQUEST_BYTES = 8192
MAX_CLIENT_HELLO_BYTES = 65536
CONNECT_LINE = re.compile(rb"^CONNECT ([A-Za-z0-9.-]+):([0-9]{1,5}) HTTP/1\.[01]$")


class ProxyRequestError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def valid_dns_name(host: str) -> bool:
    if not re.fullmatch(r"[a-z0-9.-]+", host) or len(host) > 253:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    labels = host.split(".")
    return not (
        host.startswith(".")
        or host.endswith(".")
        or ".." in host
        or any(
            not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in labels
        )
    )


def parse_connect_request(data: bytes) -> tuple[str, int]:
    if len(data) > MAX_REQUEST_BYTES or not data.endswith(b"\r\n\r\n"):
        raise ProxyRequestError(400, "invalid request headers")
    lines = data[:-4].split(b"\r\n")
    match = CONNECT_LINE.fullmatch(lines[0]) if lines else None
    if not match:
        raise ProxyRequestError(405, "CONNECT is required")
    try:
        host = match.group(1).decode("ascii").lower()
        port = int(match.group(2))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProxyRequestError(400, "invalid CONNECT target") from exc
    if not valid_dns_name(host):
        raise ProxyRequestError(400, "invalid CONNECT hostname")
    if port != 443:
        raise ProxyRequestError(403, "only HTTPS port 443 is allowed")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if b":" not in line:
            raise ProxyRequestError(400, "invalid header")
        key_bytes, value_bytes = line.split(b":", 1)
        try:
            key = key_bytes.decode("ascii").strip().lower()
            value = value_bytes.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise ProxyRequestError(400, "invalid header") from exc
        if key in headers:
            raise ProxyRequestError(400, "duplicate header")
        if key == "proxy-authorization":
            raise ProxyRequestError(400, "proxy authentication is unsupported")
        headers[key] = value
    if "host" in headers and headers["host"].lower() not in (f"{host}:{port}", host):
        raise ProxyRequestError(400, "Host header does not match CONNECT target")
    return host, port


def parse_client_hello_sni(handshake: bytes) -> str:
    """Parse a TLS ClientHello handshake body and return its single DNS SNI."""
    if len(handshake) < 4 or handshake[0] != 1:
        raise ProxyRequestError(400, "TLS ClientHello required")
    declared = int.from_bytes(handshake[1:4], "big")
    if declared > MAX_CLIENT_HELLO_BYTES or len(handshake) < declared + 4:
        raise ProxyRequestError(400, "invalid TLS ClientHello length")
    body = memoryview(handshake)[4 : 4 + declared]
    pos = 0

    def take(length: int) -> memoryview:
        nonlocal pos
        if length < 0 or pos + length > len(body):
            raise ProxyRequestError(400, "truncated TLS ClientHello")
        result = body[pos : pos + length]
        pos += length
        return result

    take(2 + 32)  # legacy version and random
    session_id_len = int.from_bytes(take(1), "big")
    take(session_id_len)
    cipher_len = int.from_bytes(take(2), "big")
    if cipher_len == 0 or cipher_len % 2:
        raise ProxyRequestError(400, "invalid TLS cipher list")
    take(cipher_len)
    compression_len = int.from_bytes(take(1), "big")
    if compression_len == 0:
        raise ProxyRequestError(400, "invalid TLS compression list")
    take(compression_len)
    if pos == len(body):
        raise ProxyRequestError(403, "TLS SNI is required")
    extensions_len = int.from_bytes(take(2), "big")
    extensions = take(extensions_len)
    if pos != len(body):
        raise ProxyRequestError(400, "invalid TLS extension length")

    ext_pos = 0
    sni_names: list[str] = []
    while ext_pos < len(extensions):
        if ext_pos + 4 > len(extensions):
            raise ProxyRequestError(400, "truncated TLS extension")
        ext_type = int.from_bytes(extensions[ext_pos : ext_pos + 2], "big")
        ext_len = int.from_bytes(extensions[ext_pos + 2 : ext_pos + 4], "big")
        ext_pos += 4
        ext = extensions[ext_pos : ext_pos + ext_len]
        if len(ext) != ext_len:
            raise ProxyRequestError(400, "truncated TLS extension")
        ext_pos += ext_len
        if ext_type != 0:
            continue
        if len(ext) < 2 or int.from_bytes(ext[:2], "big") != len(ext) - 2:
            raise ProxyRequestError(400, "invalid TLS SNI extension")
        name_pos = 2
        while name_pos < len(ext):
            if name_pos + 3 > len(ext):
                raise ProxyRequestError(400, "truncated TLS SNI name")
            name_type = ext[name_pos]
            name_len = int.from_bytes(ext[name_pos + 1 : name_pos + 3], "big")
            name_pos += 3
            name_bytes = ext[name_pos : name_pos + name_len]
            if len(name_bytes) != name_len:
                raise ProxyRequestError(400, "truncated TLS SNI name")
            name_pos += name_len
            if name_type == 0:
                try:
                    sni_names.append(bytes(name_bytes).decode("ascii").lower())
                except UnicodeDecodeError as exc:
                    raise ProxyRequestError(400, "non-ASCII TLS SNI") from exc
    if len(sni_names) != 1 or not valid_dns_name(sni_names[0]):
        raise ProxyRequestError(403, "a single DNS TLS SNI is required")
    return sni_names[0]


async def read_tls_client_hello(reader: asyncio.StreamReader) -> tuple[bytes, str]:
    """Read bounded TLS handshake records and preserve bytes for the tunnel."""
    records = bytearray()
    handshake = bytearray()
    expected_size: int | None = None
    while expected_size is None or len(handshake) < expected_size:
        header = await reader.readexactly(5)
        record_type, major, _minor = header[:3]
        record_len = int.from_bytes(header[3:5], "big")
        if record_type != 22 or major != 3 or record_len == 0 or record_len > 18432:
            raise ProxyRequestError(400, "TLS handshake record required")
        payload = await reader.readexactly(record_len)
        records.extend(header)
        records.extend(payload)
        handshake.extend(payload)
        if len(records) > MAX_CLIENT_HELLO_BYTES:
            raise ProxyRequestError(400, "TLS ClientHello exceeds size limit")
        if len(handshake) >= 4:
            if handshake[0] != 1:
                raise ProxyRequestError(400, "TLS ClientHello required")
            expected_size = 4 + int.from_bytes(handshake[1:4], "big")
            if expected_size > MAX_CLIENT_HELLO_BYTES:
                raise ProxyRequestError(400, "TLS ClientHello exceeds size limit")
    return bytes(records), parse_client_hello_sni(bytes(handshake[:expected_size]))


async def open_public_connection(host: str, port: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Resolve on the host side and connect only to globally routable addresses."""
    loop = asyncio.get_running_loop()
    try:
        infos = await asyncio.wait_for(loop.getaddrinfo(host, port, type=socket.SOCK_STREAM), timeout=5)
    except (OSError, asyncio.TimeoutError) as exc:
        raise OSError("host lookup failed") from exc
    seen: set[tuple[int, str]] = set()
    for family, socktype, proto, _canonname, sockaddr in infos:
        address = sockaddr[0]
        key = (family, address)
        if key in seen:
            continue
        seen.add(key)
        try:
            if not ipaddress.ip_address(address.split("%", 1)[0]).is_global:
                continue
        except ValueError:
            continue
        sock = socket.socket(family, socktype, proto)
        sock.setblocking(False)
        try:
            await asyncio.wait_for(loop.sock_connect(sock, sockaddr), timeout=8)
            return await asyncio.open_connection(sock=sock)
        except (OSError, asyncio.TimeoutError):
            sock.close()
    raise OSError("DNS returned no globally routable endpoint")


async def pipe_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while chunk := await reader.read(65536):
            writer.write(chunk)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            writer.write_eof()
        except (AttributeError, OSError, RuntimeError):
            pass


async def tunnel(
    left_reader: asyncio.StreamReader,
    left_writer: asyncio.StreamWriter,
    right_reader: asyncio.StreamReader,
    right_writer: asyncio.StreamWriter,
) -> None:
    tasks = [
        asyncio.create_task(pipe_stream(left_reader, right_writer)),
        asyncio.create_task(pipe_stream(right_reader, left_writer)),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


class HTTPSConnectBroker:
    def __init__(
        self,
        allowed_hosts: set[str],
        connector: Callable[
            [str, int], Awaitable[tuple[asyncio.StreamReader, asyncio.StreamWriter]]
        ] = open_public_connection,
    ):
        self.allowed_hosts = {host.lower() for host in allowed_hosts}
        if not self.allowed_hosts or any(not valid_dns_name(h) for h in self.allowed_hosts):
            raise ValueError("at least one exact DNS hostname must be allowlisted")
        self.connector = connector

    async def handle(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
        upstream_writer: asyncio.StreamWriter | None = None
        connect_established = False
        try:
            try:
                header = await asyncio.wait_for(client_reader.readuntil(b"\r\n\r\n"), timeout=5)
                if len(header) > MAX_REQUEST_BYTES:
                    raise ProxyRequestError(400, "request too large")
                host, port = parse_connect_request(header)
            except asyncio.IncompleteReadError as exc:
                raise ProxyRequestError(400, "incomplete request") from exc
            except asyncio.LimitOverrunError as exc:
                raise ProxyRequestError(400, "request too large") from exc
            except asyncio.TimeoutError as exc:
                raise ProxyRequestError(408, "request timeout") from exc
            if host not in self.allowed_hosts or port != 443:
                raise ProxyRequestError(403, "target not allowlisted")
            client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await client_writer.drain()
            connect_established = True
            try:
                client_hello, sni = await asyncio.wait_for(read_tls_client_hello(client_reader), timeout=5)
            except asyncio.TimeoutError:
                raise ProxyRequestError(408, "TLS ClientHello timeout")
            if sni != host:
                raise ProxyRequestError(403, "TLS SNI does not match allowlisted CONNECT host")
            try:
                upstream_reader, upstream_writer = await asyncio.wait_for(
                    self.connector(host, port), timeout=10
                )
            except (OSError, asyncio.TimeoutError):
                raise ProxyRequestError(502, "upstream unavailable")
            upstream_writer.write(client_hello)
            await upstream_writer.drain()
            await client_writer.drain()
            await tunnel(client_reader, client_writer, upstream_reader, upstream_writer)
        except ProxyRequestError as exc:
            if not connect_established:
                client_writer.write(f"HTTP/1.1 {exc.status} {exc}\r\nConnection: close\r\n\r\n".encode())
                try:
                    await client_writer.drain()
                except (ConnectionError, OSError):
                    pass
        finally:
            if upstream_writer is not None:
                upstream_writer.close()
                await upstream_writer.wait_closed()
            client_writer.close()
            await client_writer.wait_closed()


async def serve(socket_path: Path, allowed_hosts: set[str], *, socket_gid: int | None = None) -> None:
    if socket_gid is not None and (
        isinstance(socket_gid, bool) or not isinstance(socket_gid, int) or socket_gid < 0
    ):
        raise ValueError("socket GID must be a nonnegative integer")
    if socket_path.exists() or socket_path.is_symlink():
        raise RuntimeError(f"refusing to replace existing socket path: {socket_path}")
    socket_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    server = await asyncio.start_unix_server(
        HTTPSConnectBroker(allowed_hosts).handle, path=str(socket_path), limit=MAX_REQUEST_BYTES
    )
    if socket_gid is None:
        socket_path.chmod(0o600)
    else:
        try:
            os.chown(socket_path, -1, socket_gid)
            socket_path.chmod(0o660)
        except OSError:
            server.close()
            await server.wait_closed()
            socket_path.unlink(missing_ok=True)
            raise
    try:
        async with server:
            await server.serve_forever()
    finally:
        server.close()
        await server.wait_closed()
        socket_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True, type=Path)
    parser.add_argument("--allow-host", action="append", required=True)
    parser.add_argument(
        "--socket-gid", type=int, help="optional dedicated client group; socket is then mode 0660"
    )
    parser.add_argument(
        "--socket-group", help="optional dedicated client group name; socket is then mode 0660"
    )
    args = parser.parse_args()
    if args.socket_gid is not None and args.socket_group is not None:
        parser.error("--socket-gid and --socket-group are mutually exclusive")
    try:
        socket_gid = args.socket_gid
        if args.socket_group is not None:
            socket_gid = grp.getgrnam(args.socket_group).gr_gid
    except KeyError:
        parser.error("unknown --socket-group")
    try:
        asyncio.run(serve(args.socket, set(args.allow_host), socket_gid=socket_gid))
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
