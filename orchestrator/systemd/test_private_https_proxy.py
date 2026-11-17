import asyncio
import errno
from pathlib import Path
import tempfile
import unittest

from https_connect_broker import (
    HTTPSConnectBroker,
    ProxyRequestError,
    parse_client_hello_sni,
    parse_connect_request,
)
from t3_private_proxy_runner import bridge_client, clean_child_environment


class PrivateHTTPSProxyTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _client_hello(sni):
        name = sni.encode("ascii")
        entry = b"\x00" + len(name).to_bytes(2, "big") + name
        server_name_list = len(entry).to_bytes(2, "big") + entry
        extension = b"\x00\x00" + len(server_name_list).to_bytes(2, "big") + server_name_list
        body = (
            b"\x03\x03" + bytes(32) + b"\x00"
            + b"\x00\x02\x00\x2f"
            + b"\x01\x00"
            + len(extension).to_bytes(2, "big") + extension
        )
        handshake = b"\x01" + len(body).to_bytes(3, "big") + body
        return b"\x16\x03\x01" + len(handshake).to_bytes(2, "big") + handshake

    def _skip_if_network_socket_denied(self, exc):
        nested = exc.__cause__ or exc.__context__
        denied = exc.errno == errno.EPERM
        while nested is not None:
            denied = denied or getattr(nested, "errno", None) == errno.EPERM
            nested = nested.__cause__ or nested.__context__
        if not denied and "could not bind on any address" not in str(exc):
            raise exc
        self.skipTest(f"sandbox denies local socket creation: {exc}")

    class MemoryReader:
        def __init__(self, *chunks):
            self.chunks = list(chunks)

        async def readuntil(self, separator):
            return self.chunks.pop(0)

        async def read(self, _size):
            return self.chunks.pop(0) if self.chunks else b""

        async def readexactly(self, size):
            data = b"".join(self.chunks)
            if len(data) < size:
                self.chunks.clear()
                raise asyncio.IncompleteReadError(data, size)
            result, remaining = data[:size], data[size:]
            self.chunks.clear()
            if remaining:
                self.chunks.append(remaining)
            return result

    class MemoryWriter:
        def __init__(self):
            self.data = bytearray()
            self.closed = False

        def write(self, data):
            self.data.extend(data)

        async def drain(self):
            pass

        def write_eof(self):
            pass

        def close(self):
            self.closed = True

        async def wait_closed(self):
            pass

    def test_connect_parser_and_allowlist_target_shape(self):
        self.assertEqual(
            parse_connect_request(
                b"CONNECT opencode.ai:443 HTTP/1.1\r\nHost: opencode.ai:443\r\n\r\n"
            ),
            ("opencode.ai", 443),
        )
        for request in (
            b"GET https://opencode.ai/ HTTP/1.1\r\n\r\n",
            b"CONNECT opencode.ai:444 HTTP/1.1\r\n\r\n",
            b"CONNECT 127.0.0.1:443 HTTP/1.1\r\n\r\n",
            b"CONNECT opencode.ai:443 HTTP/1.1\r\nHost: other.ai\r\n\r\n",
            b"CONNECT opencode.ai:443 HTTP/1.1\r\nProxy-Authorization: Basic abc\r\n\r\n",
        ):
            with self.subTest(request=request), self.assertRaises(ProxyRequestError):
                parse_connect_request(request)

    def test_tls_sni_parser_requires_exact_dns_name(self):
        allowed = self._client_hello("opencode.ai")[5:]
        denied = self._client_hello("other.example")[5:]
        self.assertEqual(parse_client_hello_sni(allowed), "opencode.ai")
        self.assertEqual(parse_client_hello_sni(denied), "other.example")

    def test_clean_child_environment_contains_only_profile_and_proxy_settings(self):
        env = clean_child_environment("/tmp/test-profile", 3128)
        self.assertEqual(set(env), {
            "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME",
            "PATH", "LC_ALL", "HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy",
        })
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:3128")
        self.assertEqual(env["XDG_DATA_HOME"], "/tmp/test-profile/.local/share")

    async def test_broker_and_bridge_allow_only_exact_host_and_tunnel_bytes(self):
        connector_calls = []
        upstream_reader = self.MemoryReader(b"server_tls_bytes")
        upstream_writer = self.MemoryWriter()

        async def fake_connector(host, port):
            connector_calls.append((host, port))
            return upstream_reader, upstream_writer

        broker = HTTPSConnectBroker({"opencode.ai"}, fake_connector)
        request = b"CONNECT opencode.ai:443 HTTP/1.1\r\nHost: opencode.ai:443\r\n\r\n"
        client_hello = self._client_hello("opencode.ai")
        client_reader = self.MemoryReader(request, client_hello, b"client_application_data")
        client_writer = self.MemoryWriter()
        await broker.handle(client_reader, client_writer)
        self.assertTrue(bytes(client_writer.data).startswith(b"HTTP/1.1 200"))
        self.assertIn(b"server_tls_bytes", client_writer.data)
        self.assertIn(client_hello, upstream_writer.data)
        self.assertIn(b"client_application_data", upstream_writer.data)
        self.assertEqual(connector_calls, [("opencode.ai", 443)])

        denied_reader = self.MemoryReader(
            b"CONNECT not-allowed.example:443 HTTP/1.1\r\n\r\n"
        )
        denied_writer = self.MemoryWriter()
        await broker.handle(denied_reader, denied_writer)
        self.assertTrue(bytes(denied_writer.data).startswith(b"HTTP/1.1 403"))
        self.assertEqual(connector_calls, [("opencode.ai", 443)])

        mismatch_reader = self.MemoryReader(
            request, self._client_hello("other.example")
        )
        mismatch_writer = self.MemoryWriter()
        await broker.handle(mismatch_reader, mismatch_writer)
        self.assertTrue(bytes(mismatch_writer.data).startswith(b"HTTP/1.1 200"))
        self.assertNotIn(b"HTTP/1.1 403", mismatch_writer.data)
        self.assertEqual(connector_calls, [("opencode.ai", 443)])

        bridge_reader = self.MemoryReader(b"proxy request", b"")
        bridge_writer = self.MemoryWriter()
        bridge_upstream_reader = self.MemoryReader(b"broker reply")
        bridge_upstream_writer = self.MemoryWriter()

        async def fake_unix_connect(_path):
            return bridge_upstream_reader, bridge_upstream_writer

        await bridge_client(
            bridge_reader, bridge_writer, Path("/unused/socket"), fake_unix_connect
        )
        self.assertEqual(bytes(bridge_upstream_writer.data), b"proxy request")
        self.assertIn(b"broker reply", bridge_writer.data)

    async def test_local_socket_and_tcp_round_trip_without_external_traffic(self):
        with tempfile.TemporaryDirectory(prefix="t3-proxy-local-test-") as tmp:
            root = Path(tmp)
            broker_socket = root / "broker.sock"
            echo_connections = 0

            async def echo(reader, writer):
                nonlocal echo_connections
                echo_connections += 1
                try:
                    while chunk := await reader.read(4096):
                        writer.write(chunk)
                        await writer.drain()
                finally:
                    writer.close()
                    await writer.wait_closed()

            try:
                echo_server = await asyncio.start_server(echo, "127.0.0.1", 0)
            except OSError as exc:
                self._skip_if_network_socket_denied(exc)
            echo_port = echo_server.sockets[0].getsockname()[1]

            async def local_fake_connector(host, port):
                self.assertEqual((host, port), ("opencode.ai", 443))
                return await asyncio.open_connection("127.0.0.1", echo_port)

            try:
                broker_server = await asyncio.start_unix_server(
                    HTTPSConnectBroker({"opencode.ai"}, local_fake_connector).handle,
                    path=str(broker_socket), limit=8192,
                )
            except OSError as exc:
                self._skip_if_network_socket_denied(exc)
                echo_server.close()
                await echo_server.wait_closed()
                self.skipTest(f"sandbox does not permit local UNIX sockets: {exc}")
            try:
                try:
                    bridge_server = await asyncio.start_server(
                        lambda r, w: bridge_client(r, w, broker_socket),
                        "127.0.0.1", 0, limit=8192,
                    )
                except OSError as exc:
                    self._skip_if_network_socket_denied(exc)
                    broker_server.close()
                    echo_server.close()
                    await broker_server.wait_closed()
                    await echo_server.wait_closed()
                    self.skipTest(f"sandbox does not permit local TCP bridge sockets: {exc}")
                proxy_port = bridge_server.sockets[0].getsockname()[1]
                try:
                    reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
                    writer.write(
                        b"CONNECT opencode.ai:443 HTTP/1.1\r\nHost: opencode.ai:443\r\n\r\n"
                    )
                    await writer.drain()
                    self.assertTrue(
                        (await reader.readuntil(b"\r\n\r\n")).startswith(b"HTTP/1.1 200")
                    )
                    tls_bytes = self._client_hello("opencode.ai")
                    writer.write(tls_bytes)
                    await writer.drain()
                    self.assertEqual(
                        await asyncio.wait_for(reader.readexactly(len(tls_bytes)), 2), tls_bytes
                    )
                    writer.close()
                    await writer.wait_closed()

                    reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
                    writer.write(b"CONNECT other.example:443 HTTP/1.1\r\n\r\n")
                    await writer.drain()
                    denial = await reader.readuntil(b"\r\n\r\n")
                    self.assertTrue(denial.startswith(b"HTTP/1.1 403"))
                    writer.close()
                    await writer.wait_closed()
                    self.assertEqual(echo_connections, 1)
                finally:
                    bridge_server.close()
                    await bridge_server.wait_closed()
            finally:
                broker_server.close()
                echo_server.close()
                await broker_server.wait_closed()
                await echo_server.wait_closed()


if __name__ == "__main__":
    unittest.main()
