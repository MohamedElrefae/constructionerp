# Copyright (c) 2026, Mohamed and contributors
# For license information, please see license.txt

"""
Export Sanitization Utility
Provides shared formula injection protection and HTML/PDF escaping across
generic and BOQ-specific Excel and PDF exports.
"""

import html
from typing import Any

import frappe

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_spreadsheet_value(val: Any) -> Any:
    """Neutralize formula injection (CSV/DDE/Excel) by prefixing dangerous characters with a single quote."""
    if isinstance(val, str) and val:
        # Check if the string starts with any dangerous formula trigger
        trimmed = val.lstrip()
        if trimmed and trimmed[0] in FORMULA_PREFIXES:
            return f"'{val}"
    return val


def escape_html_for_pdf(val: Any) -> str:
    """Escape untrusted database values before rendering into PDF HTML templates."""
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return str(val)
    return html.escape(str(val), quote=True)
