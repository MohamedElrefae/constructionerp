# Copyright (c) 2026, Mohamed Elrefae and contributors
# For license information, please see license.txt

"""Application-level compensating controls for unfixable upstream packages.

Implements defensive guards for user-supplied attachments and print-format
rendering paths (pypdf, WeasyPrint, pdfkit, bleach, Pillow):

1. Upload validation: extension allowlist, size cap, magic-byte sniffing.
2. SVG sanitization: strip active content (script, handlers, external refs).
3. SSRF boundary guard: block non-local schemes, credentials, loopback and
   private/reserved IP literals in any URL used for asset fetching.
4. Local-asset protocol enforcement for print formats (no file:// or remote).
5. PDF page/size limits enforced server-side before parsing.
6. Bleach-based HTML verification for bilingual notes / print fields.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import bleach

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB
MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MiB
MAX_PDF_PAGES = 200

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff"}
ALLOWED_DOC_EXTENSIONS = {".pdf"}
ALLOWED_SVG_EXTENSIONS = {".svg"}

_SVG_DANGEROUS_TAGS = re.compile(
    r"<\s*(script|foreignObject|iframe|object|embed|audio|video|link|meta)[\s>]", re.IGNORECASE
)
_SVG_EVENT_ATTRS = re.compile(r"\son[a-zA-Z]+\s*=", re.IGNORECASE)
_SVG_JS_URI = re.compile(r"(javascript|data)\s*:", re.IGNORECASE)
_SVG_EXTERNAL_REF = re.compile(
    r"(href|xlink:href|src)\s*=\s*['\"]?\s*(https?:|file:|//|data:)", re.IGNORECASE
)

_BLOCKED_SCHEMES = {"http", "https", "file", "ftp", "gopher", "data", "javascript", "smb", "ldap"}

_BLEACH_ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + ["p", "br", "span", "div", "bdi"]
_BLEACH_ALLOWED_ATTRS = {"*": ["dir", "lang", "class"]}


class SecurityGuardError(ValueError):
    pass


def _extension(filename: str) -> str:
    idx = filename.rfind(".")
    return filename[idx:].lower() if idx >= 0 else ""


def validate_upload(filename: str, content: bytes, allowed_extensions) -> None:
    """Validate a user upload by extension allowlist, size cap and magic bytes."""
    if not filename:
        raise SecurityGuardError("missing filename")
    ext = _extension(filename)
    if ext not in allowed_extensions:
        raise SecurityGuardError(f"disallowed extension: {ext or '<none>'}")
    if content is None:
        raise SecurityGuardError("empty payload")
    if len(content) > MAX_UPLOAD_BYTES:
        raise SecurityGuardError(f"upload exceeds {MAX_UPLOAD_BYTES} bytes")
    if ext == ".pdf":
        if len(content) > MAX_PDF_BYTES:
            raise SecurityGuardError(f"pdf exceeds {MAX_PDF_BYTES} bytes")
        if not content.startswith(b"%PDF-"):
            raise SecurityGuardError("pdf magic bytes missing")
    elif ext == ".svg":
        head = content[:512].lstrip().lower()
        if b"<svg" not in head and b"<?xml" not in head:
            raise SecurityGuardError("svg magic bytes missing")
    elif ext in {".png"}:
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise SecurityGuardError("png magic bytes missing")
    elif ext in {".jpg", ".jpeg"}:
        if not content.startswith(b"\xff\xd8\xff"):
            raise SecurityGuardError("jpeg magic bytes missing")


def validate_pdf_page_limit(content: bytes, max_pages: int = MAX_PDF_PAGES) -> int:
    """Enforce a server-side page cap before any PDF parsing work."""
    if len(content) > MAX_PDF_BYTES:
        raise SecurityGuardError(f"pdf exceeds {MAX_PDF_BYTES} bytes")
    if not content.startswith(b"%PDF-"):
        raise SecurityGuardError("pdf magic bytes missing")
    try:
        from pypdf import PdfReader
        import io as _io

        pages = len(PdfReader(_io.BytesIO(content)).pages)
    except SecurityGuardError:
        raise
    except Exception as exc:
        raise SecurityGuardError(f"unparsable pdf: {exc}") from exc
    if pages > max_pages:
        raise SecurityGuardError(f"pdf exceeds {max_pages} pages")
    return pages


def sanitize_svg(content: bytes) -> bytes:
    """Reject SVGs containing active content or external references."""
    if len(content) > MAX_UPLOAD_BYTES:
        raise SecurityGuardError("svg exceeds size cap")
    text = content.decode("utf-8", errors="replace")
    if _SVG_DANGEROUS_TAGS.search(text):
        raise SecurityGuardError("svg contains active content tag")
    if _SVG_EVENT_ATTRS.search(text):
        raise SecurityGuardError("svg contains event handler attribute")
    if _SVG_JS_URI.search(text):
        raise SecurityGuardError("svg contains javascript/data uri")
    if _SVG_EXTERNAL_REF.search(text):
        raise SecurityGuardError("svg contains external reference")
    return content


def guard_ssrf(url: str) -> None:
    """Block SSRF vectors in any URL that rendering or fetching may reach."""
    if not url or not isinstance(url, str):
        raise SecurityGuardError("empty url")
    if any(c in url for c in ("\r", "\n", "\t")):
        raise SecurityGuardError("url contains control characters")
    lowered = url.strip().lower()
    for blocked in _BLOCKED_SCHEMES - {"http", "https"}:
        if lowered.startswith(blocked + ":"):
            raise SecurityGuardError(f"blocked scheme: {blocked}")
    parsed = urlparse(url if "://" in url else f"http://{url}")
    scheme = parsed.scheme.lower()
    if scheme not in {"", "http", "https"}:
        raise SecurityGuardError(f"blocked scheme: {scheme}")
    if parsed.username or parsed.password:
        raise SecurityGuardError("url contains embedded credentials")
    host = parsed.hostname
    if not host:
        raise SecurityGuardError("url missing host")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise SecurityGuardError("url targets non-public ip")
    elif (
        host.lower() in {"localhost", "localhost.localdomain"}
        or host.lower().endswith(".local")
        or host.lower().endswith(".internal")
    ):
        raise SecurityGuardError("url targets local hostname")


def enforce_local_asset_protocol(url: str) -> None:
    """Print-format asset references must be local (relative or /private/, /files/ under site)."""
    if not url:
        raise SecurityGuardError("empty asset reference")
    lowered = url.strip().lower()
    if lowered.startswith(("http://", "https://", "//", "file://", "data:", "ftp://")):
        raise SecurityGuardError("remote or file asset protocol blocked")
    if lowered.startswith("javascript:"):
        raise SecurityGuardError("javascript asset protocol blocked")
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in {""}:
        raise SecurityGuardError(f"disallowed asset scheme: {parsed.scheme}")
    if re.search(r"\.\.(/|\\)", url) or url.startswith("/etc") or url.startswith("/proc"):
        raise SecurityGuardError("path traversal blocked")


def sanitize_rich_text(html_text: str) -> str:
    """Verify rich text (bilingual notes, print fields) against the bleach allowlist."""
    if not html_text:
        return ""
    return bleach.clean(
        html_text,
        tags=_BLEACH_ALLOWED_TAGS,
        attributes=_BLEACH_ALLOWED_ATTRS,
        strip=True,
    )


def is_safe_rich_text(html_text: str) -> bool:
    return sanitize_rich_text(html_text) == (html_text or "")
