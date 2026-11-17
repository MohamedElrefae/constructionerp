"""Loopback MCP credentials must not follow HTTP redirects."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from t3_transport import HttpT3Client, TransportRefusal, obtain_mcp_token, require_loopback


class LoopbackRedirectTests(unittest.TestCase):
    def test_pairing_is_revoked_if_decision_connection_fails(self):
        def response(body):
            result = mock.MagicMock()
            result.__enter__.return_value.status = 200
            result.__enter__.return_value.read.return_value = body
            return result

        opener = mock.Mock()
        opener.open.side_effect = [
            response(b'{"client_id":"synthetic"}'),
            response(b"{}"),
            OSError("synthetic failure"),
        ]
        pairing = mock.Mock(returncode=0, stdout='{"id":"pair-id","credential":"synthetic-code"}')
        with (
            mock.patch("t3_transport._loopback_opener", return_value=opener),
            mock.patch("subprocess.run", side_effect=[pairing, mock.Mock(returncode=0)]) as run,
        ):
            with self.assertRaises(OSError):
                obtain_mcp_token(base_url="http://127.0.0.1:12345", t3_cli="/synthetic/t3")
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[-1].args[0][-2:], ["revoke", "pair-id"])

    def test_origin_requires_literal_loopback_and_no_extra_components(self):
        for value in (
            "http://localhost:1234",
            "http://127.0.0.1.example:12",
            "http://127.0.0.1:1234/path",
            "http://127.0.0.1:99999",
        ):
            with self.subTest(value=value), self.assertRaises(TransportRefusal):
                require_loopback(value)

    def test_mcp_bearer_does_not_follow_redirect(self):
        hits = []

        class Target(BaseHTTPRequestHandler):
            def do_POST(self):
                hits.append(True)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *_args):
                pass

        target = ThreadingHTTPServer(("127.0.0.1", 0), Target)
        target_thread = threading.Thread(target=target.serve_forever, daemon=True)
        target_thread.start()
        self.addCleanup(target.server_close)
        self.addCleanup(target.shutdown)

        class Redirect(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(307)
                self.send_header("Location", f"http://127.0.0.1:{target.server_port}/mcp")
                self.end_headers()

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with self.assertRaises(TransportRefusal):
            HttpT3Client(f"http://127.0.0.1:{server.server_port}", "synthetic-token-0123456789").initialize()
        self.assertEqual(hits, [])
