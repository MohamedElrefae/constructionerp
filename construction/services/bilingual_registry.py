"""Pure bilingual-registry logic (Stage 3 pilot).

No Frappe import — safe to load standalone (adversarial test suites and CI
run without a site). Frappe-dependent behavior lives in bilingual_service.py.

Registry contract (construction/data/bilingual/bilingual_registry.json):
- Doctype mapping with staged states: planned / schema_installed / active.
- Arabic display fallback: Arabic -> English -> identity.
- English display fallback (the reverse): English -> Arabic -> identity.
- Unicode policy: reject C0/C1/DEL in identity/name fields; allow the
  documented direction marks (LRM, RLM, ALM).
"""

import hashlib
import json
import re
from pathlib import Path

REGISTRY_SCHEMA = "construction-bilingual-registry/v1"
REGISTRY_STATES = ("planned", "schema_installed", "active")
FALLBACK_MODES = ("arabic", "english", "identity")

_DIRECTION_MARK_NAMES = {"LRM": "\u200e", "RLM": "\u200f", "ALM": "\u061c"}
# Canonical C1: bidi controls are FORBIDDEN in stored Arabic values —
# embeddings/overrides/isolates (U+202A–U+202E, U+2066–U+2069) and the
# direction marks (U+200E, U+200F, U+061C).
_BIDI_CONTROL_RE = re.compile("[\u202a-\u202e\u2066-\u2069\u200e\u200f\u061c]")
_CONTROL_RE = re.compile("[\x00-\x1f\x7f\x80-\x9f]")
_NARRATIVE_CONTROL_RE = re.compile("[\x00-\x1f\x7f\x80-\x9f]")
# Arabic normalization (canonical C3, server-authoritative):
# - strip diacritics (fathatan..sukun, superscript alef) and tatweel
# - unify Alef variants (أ إ آ ٱ) to bare Alef
_DIACRITICS_RE = re.compile("[\u064b-\u0655\u0670\u0640]")
_ALEF_RE = re.compile("[\u0623\u0625\u0622\u0671]")

_REGISTRY_ERRORS = []


class RegistryError(ValueError):
    pass


def default_registry_path(root=None):
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    return base / "data" / "bilingual" / "bilingual_registry.json"


def load_registry(path=None, root=None):
    """Parse and structurally validate the registry; return (data, errors).

    Fail-closed on schema/state/fallback violations; a doctype entry whose
    state is `planned` may reference absent physical fields (validated later
    against live metadata by the service layer).
    """
    errors = []
    p = Path(path) if path else default_registry_path(root)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"bilingual-registry-parse: {exc}"]

    if data.get("schema") != REGISTRY_SCHEMA:
        errors.append(f"bilingual-registry-schema: {data.get('schema')!r} != {REGISTRY_SCHEMA!r}")
    display = data.get("display") or {}
    if display.get("ar_fallback") != ["arabic", "english", "identity"]:
        errors.append("bilingual-registry-fallback: ar_fallback must be ['arabic', 'english', 'identity']")
    if display.get("en_fallback") != ["english", "arabic", "identity"]:
        errors.append("bilingual-registry-fallback: en_fallback must be ['english', 'arabic', 'identity']")
    doctypes = data.get("doctypes")
    if not isinstance(doctypes, dict) or not doctypes:
        errors.append("bilingual-registry-empty: no doctype mappings")
        doctypes = {}
    for dt, cfg in sorted(doctypes.items()):
        if cfg.get("state") not in REGISTRY_STATES:
            errors.append(f"bilingual-registry-state: {dt} state {cfg.get('state')!r} invalid")
        for field in ("english_field", "arabic_field", "identity_field"):
            if not isinstance(cfg.get(field), str) or not cfg[field]:
                errors.append(f"bilingual-registry-field: {dt}.{field} missing")
        if "search" in cfg:
            fields = (cfg.get("search") or {}).get("fields")
            if not isinstance(fields, list) or not fields:
                errors.append(f"bilingual-registry-search: {dt} search.fields missing")
    policy = data.get("unicode_policy") or {}
    for name in policy.get("narrative_allowed_direction_marks") or []:
        name_val = name.get("name") if isinstance(name, dict) else name
        if name_val not in _DIRECTION_MARK_NAMES:
            errors.append(f"bilingual-registry-unicode: unknown direction mark {name_val!r}")
    return data, errors


def registry_sha256(path=None, root=None):
    p = Path(path) if path else default_registry_path(root)
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def fallback_chain(lang):
    """Display fallback chain by session language (locked architecture #4)."""
    if lang and lang.split("-")[0].lower().startswith("ar"):
        return ["arabic", "english", "identity"]
    return ["english", "arabic", "identity"]


def is_safe_identity_text(text):
    """Canonical Unicode policy for identity/name fields (stored Arabic values).

    Rejects NUL, C0 controls, DEL, C1 controls AND every bidi control:
    U+202A–U+202E, U+2066–U+2069, U+200E (LRM), U+200F (RLM), U+061C (ALM).
    """
    if text is None:
        return False
    if not isinstance(text, str):
        return False
    if _BIDI_CONTROL_RE.search(text):
        return False
    return not _CONTROL_RE.search(text)


def is_safe_narrative_text(text):
    """Documented §8.6 policy for unrestricted narrative fields (e.g. rename
    reasons): NUL/C0/DEL/C1 and the bidi EMBEDDING/OVERRIDE/ISOLATE controls
    (U+202A–U+202E, U+2066–U+2069) are always rejected; the legitimate
    direction marks LRM/RLM/ALM are allowed."""
    if text is None:
        return False
    if not isinstance(text, str):
        return False
    if re.search("[\u202a-\u202e\u2066-\u2069]", text):
        return False
    return not _NARRATIVE_CONTROL_RE.search(text)


def normalize_arabic(text):
    """Server-authoritative Arabic search normalization (canonical C3).

    Strips diacritics and tatweel and unifies Alef variants to bare Alef so
    searches are insensitive to those differences regardless of input form.
    """
    if not text:
        return ""
    return _ALEF_RE.sub("\u0627", _DIACRITICS_RE.sub("", text))


def display_label(values, lang, identity=""):
    """Resolve a display label by the fallback chain.

    values: {"arabic": str|None, "english": str|None}
    identity: language-neutral internal name (last resort).
    Returns (label, resolved_mode).
    """
    for mode in fallback_chain(lang):
        candidate = (values or {}).get(mode)
        if candidate and str(candidate).strip():
            return str(candidate), mode
    return (identity or ""), "identity"


def relevance_rank(strings, query):
    """Deterministic relevance rank for search results (lower is better).

    0 = exact match, 1 = prefix match, 2 = substring match, 3 = other.
    Empty queries rank last so untouched orderings stay stable.
    """
    q = (query or "").strip().lower()
    if not q:
        return 3
    best = 3
    for s in strings or ():
        v = str(s or "").strip().lower()
        if not v:
            continue
        if v == q:
            best = min(best, 0)
        elif v.startswith(q):
            best = min(best, 1)
        elif q in v:
            best = min(best, 2)
    return best


def completeness(values, required=("arabic", "english")):
    """Completeness over the required identity components (and any extras).

    values keys may include "arabic", "english", "code", "identity".
    Returns {"present": {...}, "complete": bool}.
    """
    present = {
        k: bool((values or {}).get(k) and str(values[k]).strip())
        for k in ("arabic", "english", "code", "identity")
        if k in (values or {})
    }
    complete = all(present.get(k, False) for k in required if k in present or k in ("arabic", "english"))
    missing = [k for k in required if not present.get(k, False)]
    return {"present": present, "missing": missing, "complete": complete and not missing}
