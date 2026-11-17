import os
import socket
import struct
import unittest
from unittest import mock

import managed_attestation_verifier as verifier
from managed_supervisor_attestation import AttestationError, verify_via_root_service


class FakeConn:
    def __init__(self, payload=b"V1\n", *, pid=123, uid=1001):
        self.payload = bytearray(payload)
        self.credentials = struct.pack("3i", pid, uid, 1001)

    def getsockopt(self, *_args):
        return self.credentials

    def settimeout(self, _timeout):
        return None

    def recv(self, size):
        data = bytes(self.payload[:size])
        del self.payload[:size]
        return data


class VerifierProtocolTests(unittest.TestCase):
    def test_accepts_only_exact_frame_and_binds_peer_pid_uid(self):
        calls = []

        def check(path, *, supervisor_pid, supervisor_uid):
            calls.append((path, supervisor_pid, supervisor_uid))

        self.assertTrue(verifier.verify_request(FakeConn(), verifier=check))
        self.assertEqual(calls, [(verifier.CONFIG_PATH, 123, 1001)])

    def test_rejects_unknown_or_overlong_frame_without_attestation(self):
        for payload in (b"NO\n", b"V1\nX", b"V1"):
            with self.subTest(payload=payload):
                check = mock.Mock()
                self.assertFalse(verifier.verify_request(FakeConn(payload), verifier=check))
                check.assert_not_called()

    def test_fail_closed_on_attestation_error(self):
        self.assertFalse(verifier.verify_request(
            FakeConn(), verifier=mock.Mock(side_effect=AttestationError("no proc access"))))


class ClientTests(unittest.TestCase):
    def _client_socket(self, *, uid=0, response=b"OK\n"):
        client = mock.Mock()
        client.getsockopt.return_value = struct.pack("3i", 90, uid, 0)
        client.recv.return_value = response
        return client

    def test_client_requires_root_peer_and_exact_positive_reply(self):
        client = self._client_socket()
        with mock.patch("managed_supervisor_attestation.socket.socket", return_value=client):
            self.assertTrue(verify_via_root_service())
        self.assertEqual(client.connect.call_args.args[0], str(verifier.SOCKET_PATH))
        self.assertEqual(client.sendall.call_args.args[0], b"V1\n")
        self.assertTrue(client.shutdown.called)
        for uid, response in ((1000, b"OK\n"), (0, b"NO\n"), (0, b"OK\nX")):
            with self.subTest(uid=uid, response=response):
                client = self._client_socket(uid=uid, response=response)
                with mock.patch("managed_supervisor_attestation.socket.socket", return_value=client):
                    with self.assertRaises(AttestationError):
                        verify_via_root_service()

    def test_client_rejects_unfixed_path_and_timeout(self):
        with self.assertRaises(AttestationError):
            verify_via_root_service(socket_path="/tmp/alternate.sock")
        with self.assertRaises(AttestationError):
            verify_via_root_service(timeout=10)

if __name__ == "__main__":
    unittest.main()
