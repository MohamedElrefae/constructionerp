# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""Unit tests for application-level dependency security compensating guards."""

import unittest

from construction.construction.utils.security import (
    MAX_PDF_PAGES,
    SecurityGuardError,
    enforce_local_asset_protocol,
    guard_ssrf,
    is_safe_rich_text,
    sanitize_rich_text,
    sanitize_svg,
    validate_pdf_page_limit,
    validate_upload,
)

_MIN_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 10 10]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
)


class TestUploadValidation(unittest.TestCase):
    def test_valid_pdf_accepted(self):
        validate_upload("vo.pdf", _MIN_PDF, {".pdf"})

    def test_disallowed_extension_rejected(self):
        with self.assertRaises(SecurityGuardError):
            validate_upload("evil.exe", b"MZ", {".pdf"})

    def test_fake_pdf_rejected(self):
        with self.assertRaises(SecurityGuardError):
            validate_upload("vo.pdf", b"not a pdf", {".pdf"})

    def test_oversize_rejected(self):
        with self.assertRaises(SecurityGuardError):
            validate_upload("big.pdf", b"%PDF-" + b"0" * (21 * 1024 * 1024), {".pdf"})

    def test_valid_png_accepted(self):
        validate_upload("img.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, {".png"})

    def test_fake_png_rejected(self):
        with self.assertRaises(SecurityGuardError):
            validate_upload("img.png", b"GIF89a....", {".png"})


class TestPdfPageLimit(unittest.TestCase):
    def test_small_pdf_page_count(self):
        pages = validate_pdf_page_limit(_MIN_PDF)
        self.assertEqual(pages, 1)

    def test_oversized_pdf_rejected(self):
        with self.assertRaises(SecurityGuardError):
            validate_pdf_page_limit(b"%PDF-" + b"0" * (21 * 1024 * 1024))

    def test_garbage_pdf_rejected(self):
        with self.assertRaises(SecurityGuardError):
            validate_pdf_page_limit(b"%PDF-garbage")


class TestSvgSanitization(unittest.TestCase):
    def test_benign_svg_accepted(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
        self.assertEqual(sanitize_svg(svg), svg)

    def test_script_tag_rejected(self):
        with self.assertRaises(SecurityGuardError):
            sanitize_svg(b'<svg><script>alert(1)</script></svg>')

    def test_event_handler_rejected(self):
        with self.assertRaises(SecurityGuardError):
            sanitize_svg(b'<svg onload="alert(1)"></svg>')

    def test_javascript_uri_rejected(self):
        with self.assertRaises(SecurityGuardError):
            sanitize_svg(b'<svg><a href="javascript:alert(1)">x</a></svg>')

    def test_external_href_rejected(self):
        with self.assertRaises(SecurityGuardError):
            sanitize_svg(b'<svg><image href="https://evil.example/x.png"/></svg>')

    def test_foreign_object_rejected(self):
        with self.assertRaises(SecurityGuardError):
            sanitize_svg(b'<svg><foreignObject><body>x</body></foreignObject></svg>')


class TestSsrfGuard(unittest.TestCase):
    def test_loopback_blocked(self):
        with self.assertRaises(SecurityGuardError):
            guard_ssrf("http://127.0.0.1/admin")

    def test_metadata_ip_blocked(self):
        with self.assertRaises(SecurityGuardError):
            guard_ssrf("http://169.254.169.254/latest/meta-data")

    def test_private_range_blocked(self):
        with self.assertRaises(SecurityGuardError):
            guard_ssrf("http://10.0.0.5/internal")

    def test_localhost_blocked(self):
        with self.assertRaises(SecurityGuardError):
            guard_ssrf("http://localhost/secret")

    def test_file_scheme_blocked(self):
        with self.assertRaises(SecurityGuardError):
            guard_ssrf("file:///etc/passwd")

    def test_embedded_credentials_blocked(self):
        with self.assertRaises(SecurityGuardError):
            guard_ssrf("http://user:pass@example.com/x")

    def test_javascript_scheme_blocked(self):
        with self.assertRaises(SecurityGuardError):
            guard_ssrf("javascript:alert(1)")

    def test_public_https_allowed(self):
        guard_ssrf("https://example.com/asset.png")


class TestLocalAssetProtocol(unittest.TestCase):
    def test_relative_path_allowed(self):
        enforce_local_asset_protocol("/files/logo.png")

    def test_remote_http_blocked(self):
        with self.assertRaises(SecurityGuardError):
            enforce_local_asset_protocol("https://evil.example/x.css")

    def test_file_scheme_blocked(self):
        with self.assertRaises(SecurityGuardError):
            enforce_local_asset_protocol("file:///etc/passwd")

    def test_protocol_relative_blocked(self):
        with self.assertRaises(SecurityGuardError):
            enforce_local_asset_protocol("//evil.example/x.css")

    def test_traversal_blocked(self):
        with self.assertRaises(SecurityGuardError):
            enforce_local_asset_protocol("../../etc/passwd")


class TestRichTextSanitization(unittest.TestCase):
    def test_script_stripped(self):
        self.assertNotIn("<script>", sanitize_rich_text("<p>ok</p><script>alert(1)</script>"))

    def test_event_attribute_stripped(self):
        cleaned = sanitize_rich_text('<p onclick="alert(1)">hi</p>')
        self.assertNotIn("onclick", cleaned)

    def test_benign_markup_preserved(self):
        self.assertIn("<b>", sanitize_rich_text("<p><b>hi</b></p>"))

    def test_unsafe_text_detected(self):
        self.assertFalse(is_safe_rich_text("<img src=x onerror=alert(1)>"))

    def test_safe_text_passes(self):
        self.assertTrue(is_safe_rich_text("<p>مرحبا</p>"))


if __name__ == "__main__":
    unittest.main()
