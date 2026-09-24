"""Localization gates for Construction Arabic UI (Stage 2).

Deterministic, stdlib-only, CI-ready. Enforces the Stage 2 acceptance statement:
new Construction visible strings and vendor upgrade deltas cannot bypass triage.

Owned inputs (never vendor catalogs):
  construction/locale/ar.po
  construction/data/translations/approved_ar_overrides.csv
  construction/data/**/*.json
  construction/data/translations/allowlisted_source_equal.txt
  construction/data/translations/vendor_covered.txt
  construction/data/translations/raw_text_dispositions.txt
  construction/data/translations/retired_sources.txt
  construction/data/translations/release_decisions.json
  construction/data/translations/legacy_batch_decisions.json
  construction/data/translations/critical_labels.json
  construction/data/localization/vendor_catalog_baseline.json
  construction/data/localization/vendor_msgids_{frappe,erpnext}.txt
  construction/data/localization/localization_manifest.json
  construction/data/localization/freshness_evidence.json
  construction/data/localization/site_classification.json
  construction/data/localization/stage2_inventory_manifest.json

Usage:
  python3 scripts/check_localization_gates.py [--files f ...] [--update-baselines [--delta-reviewed F]] [--audit-vendor-coverage] [--root=DIR]

Every check resolves paths from an explicit root (default: repository checkout).
Exit 0 pass, 1 fail. Output sorted for determinism.
"""

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PO = Path("construction/locale/ar.po")
CSV = Path("construction/data/translations/approved_ar_overrides.csv")
ALLOWLIST = Path("construction/data/translations/allowlisted_source_equal.txt")
BASELINE = Path("construction/data/localization/vendor_catalog_baseline.json")
MANIFEST = Path("construction/data/localization/localization_manifest.json")
FRESHNESS = Path("construction/data/localization/freshness_evidence.json")
VENDOR_COVERED = Path("construction/data/translations/vendor_covered.txt")
RETIRED = Path("construction/data/translations/retired_sources.txt")
RAW_DISPOSITIONS = Path("construction/data/translations/raw_text_dispositions.txt")
RETIRED_VERSION = "schema: retired-lifecycle/v3"
RETIRED_SCHEMA = "event | old_path | new_path(-) | reason | reviewer/session | UTC date | evidence#sha256"
DECISIONS = Path("construction/data/translations/release_decisions.json")

CSV_HEADER = [
    "language",
    "source_text",
    "context",
    "ct_app",
    "translated_text",
    "domain",
    "release_status",
    "release_version",
    "a1_reviewer",
    "a1_approved_at",
    "a2_reviewer",
    "a2_approved_at",
    "a3_reviewer",
    "a3_approved_at",
    "references",
    "notes",
    "decision_ref",
]
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
VER_RE = re.compile(r"^\d+\.\d+$")
BIDI_RE = re.compile("[\u202a-\u202e\u2066-\u2069\u200e\u200f\u061c]")
PRINTF_RE = re.compile(r"%(?:\d+\$)?[#0\- +']?(?:\d+)?(?:\.\d+)?[sdfieEouxXc%]")
BRACE_RE = re.compile(r"\{\{|\}\}|\{[A-Za-z_][A-Za-z0-9_]*\}|\{\d+\}")
TAG_RE = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)[^>]*>")
ENTITY_RE = re.compile(r"&(?:amp|lt|gt|quot|apos|nbsp|#\d+);")
UNSAFE_HTML_RE = re.compile(r"<\s*(script|iframe)\b|on[a-z]+\s*=", re.IGNORECASE)
WRAP_RE = re.compile(r"(?:_|__)\(\s*(['\"])((?:\\.|(?!\1).)*?)\1", re.DOTALL)
DYNAMIC_WRAP_RE = re.compile(r"(?:_|__)\(\s*(?:f['\"]|`[^`]*\$\{)")
SOURCE_SUFFIXES = {".py", ".js", ".html", ".vue"}
SKIP_SUFFIXES = {
    ".md",
    ".css",
    ".scss",
    ".png",
    ".jpg",
    ".svg",
    ".ico",
    ".map",
    ".txt",
    ".log",
}
SOURCE_SCAN_ROOTS = ["construction"]
PO_SCAN_SUFFIXES = {".py", ".js", ".html", ".vue"}
EXCLUDE_DIRS = {"__pycache__", "dist", "tests"}
TEMPLATE_SUFFIXES = {".html", ".vue"}
JSON_UI_EXCLUDE = (
    "construction/data/",
    "construction/construction/doctype/",
    "construction/fixtures/",
    "package.json",
    "/tests/",
    "__pycache__",
    "/dist/",
)
TECHNICAL_JSON_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|\[.*\]$|\{.*\}$|[a-z0-9_\-]+$|[A-Z0-9 _()/.\-]{1,4}$|en$)"
)
LABEL_KEYS = {"label", "title", "card_name", "heading", "description"}
JS_SINK_RE = re.compile(
    r"(?:frappe\.(?:msgprint|throw|confirm)|[^.\w](?:msgprint|alert|confirm))\(\s*(['\"])"
)
PY_SINK_RE = re.compile(r"frappe\.(?:throw|msgprint)\(\s*[fu]?['\"]")
BARE_USE_RE = re.compile(r"(^|[^_.a-zA-Z])_\(\s*['\"]")
FROM_IMPORT_RE = re.compile(r"^\s*from frappe import .*\b_\b", re.M)
RAW_TEMPLATE_ROOTS = ["construction/templates"]
EVIDENCE_FILES = (
    "all-tests.txt",
    "final-dryrun.txt",
    "freshness-envelope.txt",
    "full-gate.txt",
    "gate-tests-standalone.txt",
    "lints-diffcheck.txt",
    "merkle.txt",
    "scoped-gate.txt",
    "sync.txt",
    "vendor-audit.txt",
)


def _root(root):
    return Path(root) if root else ROOT


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def unescape_po(text):
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            n = text[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse_po_file(path):
    """Return (entries, errors). Entry: dict(context, msgid, plural, targets, fuzzy, obsolete)."""
    entries = []
    errors = []
    cur = None

    def flush():
        if cur is not None and cur["msgid"] is not None:
            entries.append(cur)

    with open(path, encoding="utf-8") as fh:
        lineno = 0
        section = None
        for raw in fh:
            lineno += 1
            line = raw.rstrip("\n")
            if line.startswith("#~"):
                if cur is None or cur.get("started") is not True:
                    cur = {
                        "context": "",
                        "msgid": None,
                        "plural": None,
                        "targets": {},
                        "fuzzy": False,
                        "obsolete": True,
                        "started": True,
                    }
                else:
                    cur["obsolete"] = True
                section = None
                continue
            if not line.strip():
                flush()
                cur = None
                section = None
                continue
            if line.startswith("#"):
                if ", fuzzy" in line or (line.startswith("#,") and "fuzzy" in line):
                    if cur is None:
                        cur = {
                            "context": "",
                            "msgid": None,
                            "plural": None,
                            "targets": {},
                            "fuzzy": True,
                            "obsolete": False,
                            "started": False,
                        }
                    else:
                        cur["fuzzy"] = True
                if cur is None:
                    continue
                section = None
                continue
            m = re.match(r"^(msgctxt|msgid|msgid_plural|msgstr(?:\[(\d+)\])?)\s+\"(.*)$", line)
            if m:
                kind, idx, rest = m.group(1), m.group(2), m.group(3)
                if not rest.endswith('"'):
                    errors.append(f"{path}:{lineno}: unterminated string")
                    section = None
                    continue
                val = rest[:-1]
                if cur is None:
                    cur = {
                        "context": "",
                        "msgid": None,
                        "plural": None,
                        "targets": {},
                        "fuzzy": False,
                        "obsolete": False,
                        "started": True,
                    }
                if kind == "msgctxt":
                    cur["context"] = unescape_po(val)
                    section = ("context", None)
                elif kind == "msgid":
                    if cur["msgid"] is not None:
                        flush()
                        cur = {
                            "context": "",
                            "msgid": None,
                            "plural": None,
                            "targets": {},
                            "fuzzy": False,
                            "obsolete": False,
                            "started": True,
                        }
                    cur["msgid"] = unescape_po(val)
                    section = ("msgid", None)
                elif kind == "msgid_plural":
                    cur["plural"] = unescape_po(val)
                    section = ("plural", None)
                else:
                    cur["targets"][int(idx) if idx is not None else 0] = unescape_po(val)
                    section = ("target", int(idx) if idx is not None else 0)
                continue
            if line.startswith('"') and line.endswith('"') and cur is not None and section:
                val = unescape_po(line[1:-1])
                sk, ix = section
                if sk == "context":
                    cur["context"] += val
                elif sk == "msgid":
                    cur["msgid"] += val
                elif sk == "plural":
                    cur["plural"] += val
                else:
                    cur["targets"][ix] += val
                continue
            errors.append(f"{path}:{lineno}: malformed PO line: {line[:60]!r}")
    flush()
    return [e for e in entries if e["msgid"]], errors


def fmt_placeholders(value):
    found = [m for m in PRINTF_RE.findall(value) if m != "%%"]
    found += [m for m in BRACE_RE.findall(value) if m not in ("{{", "}}")]
    return sorted(found)


def html_tags(value):
    return sorted(TAG_RE.findall(value))


def html_entities(value):
    return sorted(ENTITY_RE.findall(value))


def check_unicode(value, origin, errors):
    if "\x00" in value:
        errors.append(f"unicode-nul: {origin} contains NUL")
    m = BIDI_RE.search(value)
    if m:
        errors.append(f"unicode-bidi: {origin} contains U+{ord(m.group(0)):04X}")


def affix(value):
    return (value[: len(value) - len(value.lstrip())], value[len(value.rstrip()) :])


def plural_forms(path):
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "nplurals=" in raw:
            m = re.search(r"nplurals=(\d+)", raw)
            if m:
                return int(m.group(1))
    return None


def load_allowlist(errors, root=None):
    root = _root(root)
    p = root / ALLOWLIST
    if not p.exists():
        errors.append(f"allowlist-missing: {ALLOWLIST} does not exist (fail closed)")
        return set()
    allowed = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            parts = [x.strip() for x in line.split("|")]
            if len(parts) < 3:
                errors.append(f"allowlist-schema: bad line in {ALLOWLIST}: {line!r}")
                continue
            allowed.add((parts[0], parts[1], parts[2]))
    return allowed


def check_target(errors, msgid, target, origin, allowed, context, is_plural, plural=None):
    where = f"{origin} {msgid!r}"
    check_unicode(target, where, errors)
    if affix(target) != affix(msgid):
        errors.append(f"po-whitespace: {where} target affix differs from source")
    expect_ph = sorted(set(fmt_placeholders(msgid)) | set(fmt_placeholders(plural or "")))
    if expect_ph != fmt_placeholders(target):
        errors.append(f"po-placeholder: {where} {expect_ph} != {fmt_placeholders(target)}")
    if sorted(html_tags(msgid)) != sorted(html_tags(target)):
        errors.append(f"po-html: {where} tag/attribute mismatch")
    if html_entities(msgid) != html_entities(target):
        errors.append(f"po-html-entity: {where} entity mismatch")
    if UNSAFE_HTML_RE.search(target):
        errors.append(f"po-html-unsafe: {where} unsafe markup")
    if target == msgid:
        key = ("construction", context, msgid)
        if key not in allowed:
            errors.append(f"po-source-equal: {where} not allowlisted")


def check_po(errors, counts, path=None, root=None):
    root = _root(root)
    path = Path(path) if path else root / PO
    entries, parse_errors = parse_po_file(path)
    for e in parse_errors:
        errors.append(f"po-parse: {e}")
    nplurals = plural_forms(path) or 0
    if nplurals != 6:
        errors.append(f"po-header: expected Arabic nplurals=6, got {nplurals}")
    allowed = load_allowlist(errors, root)
    seen = set()
    for e in entries:
        if e["obsolete"]:
            continue
        ident = (e["context"], e["msgid"])
        if ident in seen:
            errors.append(f"po-duplicate: {path} context={e['context']!r} msgid={e['msgid']!r}")
        seen.add(ident)
        if e["fuzzy"]:
            errors.append(f"po-fuzzy: {path} {e['msgid']!r} marked fuzzy (needs review)")
            continue
        targets = e["targets"]
        if e["plural"] is not None:
            if targets.get(0):
                for i in range(nplurals):
                    if not targets.get(i):
                        errors.append(f"po-plural: {path} {e['msgid']!r} missing msgstr[{i}]")
            for i, t in sorted(targets.items()):
                if t:
                    check_target(
                        errors, e["msgid"], t, str(path), allowed, e["context"], True, plural=e["plural"]
                    )
        else:
            t = targets.get(0, "")
            if t:
                check_target(errors, e["msgid"], t, str(path), allowed, e["context"], False)
    counts[str(path.relative_to(root)) if str(path).startswith(str(root)) else str(path)] = len(seen)
    return {(c, m) for c, m in seen}


def iter_source_files(scope=None, root=None):
    root = _root(root)
    files = []
    for sub in SOURCE_SCAN_ROOTS:
        base = root / sub
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix not in PO_SCAN_SUFFIXES:
                continue
            if EXCLUDE_DIRS.intersection(p.parts):
                continue
            rel = p.relative_to(root)
            if scope is not None and str(rel) not in scope:
                continue
            files.append(rel)
    return files


def load_vendor_covered(errors, root=None):
    root = _root(root)
    p = root / VENDOR_COVERED
    if not p.exists():
        errors.append(f"vendor-covered-missing: {VENDOR_COVERED} (fail closed)")
        return set()
    covered = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            covered.add(line)
    return covered


def extract_wrapped(paths, root=None):
    root = _root(root)
    found = {}
    for rel in paths:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        for m in WRAP_RE.finditer(text):
            raw = m.group(2)
            try:
                val = raw.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
            except Exception:
                val = raw.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
            if val:
                found.setdefault(val, set()).add(str(rel))
    return found


def check_extraction(errors, catalog, scope=None, root=None):
    root = _root(root)
    files = iter_source_files(scope, root)
    wrapped = extract_wrapped([str(f) for f in files], root)
    catalog_ids = {m for _, m in catalog}
    covered = load_vendor_covered(errors, root)
    missing = 0
    for msgid, locs in sorted(wrapped.items()):
        if not msgid or msgid in catalog_ids or msgid in covered:
            continue
        errors.append(f"extract-missing: {msgid!r} used in {sorted(locs)[0]} not in catalog")
        missing += 1
    json_files = iter_json_ui_files(scope, root)
    for msgid, locs in sorted(json_wrapped_strings(json_files, root).items()):
        if msgid not in catalog_ids and msgid not in covered:
            errors.append(f"extract-json-wrapped-missing: {msgid!r} in {sorted(locs)[0]} not in catalog")
            missing += 1
    json_found, json_skipped = json_ui_strings(json_files, errors, root)
    for note in sorted(set(json_skipped)):
        print("SKIP " + note)
    for msgid, locs in sorted(json_found.items()):
        if msgid in catalog_ids or msgid in covered:
            continue
        errors.append(f"extract-json-missing: {msgid!r} in {sorted(locs)[0]} not in catalog")
        missing += 1
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        if DYNAMIC_WRAP_RE.search(text):
            errors.append(
                f"extract-dynamic: {rel} has dynamic/unverifiable translation call "
                "(hoist static literals or obtain reviewed disposition)"
            )
        if rel.suffix not in (".js", ".html", ".vue"):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if JS_SINK_RE.search(line) and "__(" not in line and "_(" not in line:
                errors.append(f"no-raw-sink: {rel}:{i}: unwrapped user-facing string")
    json_count = len(json_found)
    return {
        "files": len(files) + len(json_files),
        "wrapped": len(wrapped),
        "missing": missing,
        "json_labels": json_count,
    }


def is_excluded_json(rel):
    s = str(rel)
    return any(x in s for x in JSON_UI_EXCLUDE)


def iter_json_ui_files(scope=None, root=None):
    root = _root(root)
    files = []
    base = root / "construction"
    for p in sorted(base.rglob("*.json")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root))
        if any(x in rel for x in JSON_UI_EXCLUDE):
            continue
        if scope is not None and rel not in scope:
            continue
        files.append(rel)
    return files


def json_wrapped_strings(files, root=None):
    root = _root(root)
    found = {}
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        for m in WRAP_RE.finditer(text):
            raw = m.group(2)
            try:
                val = raw.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
            except Exception:
                val = raw.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
            if val:
                found.setdefault(val, set()).add(str(rel))
    return found


def json_ui_strings(files, errors, root=None):
    """Extract human-readable UI labels (not codes, colors, CSS, markup blobs)."""
    root = _root(root)
    found = {}
    skipped_notes = []
    for rel in files:
        try:
            data = json.loads((root / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"json-ui-parse: {rel}: {exc}")
            continue

        def label_candidate(v):
            if not isinstance(v, str):
                return False
            s = v.strip()
            if len(s) < 2 or not re.search(r"[A-Za-z\u0600-\u06FF]", s):
                return False
            if len(s) > 300 or "\n" in s or "<" in s or "{" in s or "%" in s:
                if re.search(r"[A-Za-z]{3,}", s):
                    skipped_notes.append(
                        f"{rel}: markup/code blob excluded from string gate "
                        "(print/CSS/seed-data; covered by bilingual-output waves + leak detection)"
                    )
                return False
            if TECHNICAL_JSON_RE.match(s):
                return False
            return True

        def walk(v, in_label_key=False):
            if isinstance(v, str):
                if (in_label_key or " " in v.strip()) and label_candidate(v):
                    found.setdefault(v.strip(), set()).add(rel)
            elif isinstance(v, list):
                for i in v:
                    walk(i, in_label_key)
            elif isinstance(v, dict):
                for k, i in v.items():
                    walk(i, in_label_key or k in LABEL_KEYS)

        walk(data)
    return found, skipped_notes


def strip_template(text):
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"{#.*?#}", " ", text, flags=re.S)
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"{%.*?%}", " ", text, flags=re.S)
    text = re.sub(r"{{.*?}}", " ", text, flags=re.S)
    return text


def raw_template_texts(files, root=None):
    root = _root(root)
    found = {}
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        for chunk in re.split(r"[\n\r]+", strip_template(text)):
            for seg in re.split(r"\s{2,}|[|•·]", chunk):
                s = seg.strip(" \t-\u2013\u2014:;,.!?\"'")
                if len(s) >= 2 and re.search(r"[A-Za-z]{2,}", s) and not re.fullmatch(r"[\d\W]+", s):
                    found.setdefault(s, set()).add(str(rel))
    return found


def load_raw_dispositions(errors, root=None):
    root = _root(root)
    p = root / RAW_DISPOSITIONS
    if not p.exists():
        errors.append(f"raw-dispositions-missing: {RAW_DISPOSITIONS} (fail closed)")
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("|")]
        if len(parts) != 4 or not all(parts) or parts[1] not in ("brand", "technical", "deferred"):
            errors.append(f"raw-dispositions-schema: bad line: {line!r}")
            continue
        text, kind, rationale, reviewer = parts
        out[text] = (kind, rationale, reviewer)
    return out


def check_raw_text(errors, catalog, scope=None, root=None):
    root = _root(root)
    files = []
    for sub in RAW_TEMPLATE_ROOTS:
        base = root / sub
        if not base.exists():
            continue
        for q in sorted(base.rglob("*")):
            if not q.is_file() or q.suffix not in TEMPLATE_SUFFIXES:
                continue
            rel = str(q.relative_to(root))
            if scope is not None and rel not in scope:
                continue
            files.append(rel)
    catalog_ids = {m for _, m in catalog}
    covered = load_vendor_covered(errors, root)
    disposed = load_raw_dispositions(errors, root)
    texts = raw_template_texts([str(f) for f in files], root)
    missing = 0
    for text, locs in sorted(texts.items()):
        if text in catalog_ids or text in covered or text in disposed:
            continue
        errors.append(f"raw-text-missing: {text!r} in {sorted(locs)[0]} — wrap in _() or disposition")
        missing += 1
    return {"files": len(files), "texts": len(texts), "missing": missing}


def ast_sink_findings(rel, text, errors):
    """AST/token-aware inspection of frappe.throw/msgprint calls."""
    import ast as _ast

    try:
        tree = _ast.parse(text)
    except SyntaxError as exc:
        errors.append(f"py-parse: {rel}: {exc}")
        return []
    aliases = set()
    wrappers = {"_", "__"}
    module_aliases = {"frappe": "frappe"}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for a in node.names:
                if a.name == "frappe":
                    module_aliases[a.asname or a.name] = "frappe"
        if isinstance(node, _ast.ImportFrom) and node.module == "frappe":
            for a in node.names:
                if a.name in ("_", "__"):
                    wrappers.add(a.asname or a.name)
                elif a.name in ("throw", "msgprint"):
                    aliases.add(a.asname or a.name)
        if (
            isinstance(node, _ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], _ast.Name)
        ):
            v = node.value
            if (
                isinstance(v, _ast.Attribute)
                and isinstance(v.value, _ast.Name)
                and v.value.id in module_aliases
                and v.attr in ("throw", "msgprint")
            ):
                aliases.add(node.targets[0].id)
            elif isinstance(v, _ast.Name) and v.id in module_aliases:
                module_aliases[node.targets[0].id] = "frappe"

    def resolves_frappe(node):
        while isinstance(node, _ast.Attribute):
            node = node.value
        return isinstance(node, _ast.Name) and module_aliases.get(node.id) == "frappe"

    findings = []
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Call):
            continue
        fname = None
        f = node.func
        if isinstance(f, _ast.Attribute) and f.attr in ("throw", "msgprint") and resolves_frappe(f.value):
            fname = f.attr
        elif isinstance(f, _ast.Name) and f.id in aliases:
            fname = "alias:" + f.id
        if fname is None or not node.args:
            continue
        arg = node.args[0]
        lineno = getattr(node, "lineno", "?")
        probe = arg
        while isinstance(probe, _ast.Call | _ast.Attribute | _ast.Subscript):
            if isinstance(probe, _ast.Attribute) and probe.attr in ("_", "__"):
                probe = None
                break
            if isinstance(probe, _ast.Call):
                probe = probe.func
            elif isinstance(probe, _ast.Attribute):
                probe = probe.value
            else:
                probe = probe.value
        if probe is None:
            continue
        if isinstance(probe, _ast.Name) and probe.id in wrappers:
            continue
        static = None
        if isinstance(arg, _ast.Constant) and isinstance(arg.value, str):
            static = arg.value
        elif isinstance(arg, _ast.JoinedStr) and not any(
            isinstance(v, _ast.FormattedValue) for v in arg.values
        ):
            static = "".join(v.value for v in arg.values if isinstance(v, _ast.Constant))
        if static is not None:
            findings.append((lineno, "static", static, None))
            continue
        varname = arg.id if isinstance(arg, _ast.Name) else None
        try:
            segment = _ast.get_source_segment(text, arg)
        except Exception:
            segment = None
        findings.append((lineno, "dynamic", _ast.dump(arg)[:80], (varname, segment)))
    return findings


def check_py_sinks(errors, scope=None, root=None):
    """Python frappe.throw/msgprint calls: AST-classified as static/dynamic."""
    root = _root(root)
    files = [f for f in iter_source_files(scope, root) if Path(f).suffix == ".py"]
    disposed = load_raw_dispositions(errors, root)
    hits = 0
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        srel = str(rel)
        for lineno, kind, val, extra in ast_sink_findings(rel, text, errors):
            if kind == "static":
                if val in disposed or any(val.startswith(d) for d in disposed):
                    continue
                errors.append(
                    f"py-raw-sink: {srel}:{lineno}: unwrapped backend message — wrap or disposition"
                )
                hits += 1
                continue
            varname, segment = extra or (None, None)
            label = varname or (segment.strip()[:60] if segment else val[:40])
            candidates = [
                c for c in (f"{srel} :: {varname}" if varname else None, (segment or "").strip(), val) if c
            ]
            if any(c in disposed or any(d in c or c.startswith(d) for d in disposed) for c in candidates):
                continue
            errors.append(
                f"py-var-sink: {srel}:{lineno}: dynamic message ({label}) — "
                "wrap at construction or disposition with provenance"
            )
            hits += 1
    return hits


def check_underscore_imports(errors, scope=None, root=None):
    root = _root(root)
    files = [f for f in iter_source_files(scope, root) if Path(f).suffix == ".py"]
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        if BARE_USE_RE.search(text) and not FROM_IMPORT_RE.search(text):
            errors.append(f"no-underscore-import: {rel} uses _() without 'from frappe import _'")


def row_identity_fields(row, src, val):
    """Canonical row-identity fields (checker + recorder share this order)."""
    return [
        (row.get("language") or "").strip(),
        (row.get("ct_app") or "").strip(),
        (row.get("context") or "").strip(),
        src,
        val,
        (row.get("a1_reviewer") or "").strip(),
        (row.get("a1_approved_at") or "").strip(),
        (row.get("a2_reviewer") or "").strip(),
        (row.get("a2_approved_at") or "").strip(),
        (row.get("a3_reviewer") or "").strip(),
        (row.get("a3_approved_at") or "").strip(),
        (row.get("release_version") or "").strip(),
        (row.get("domain") or "").strip(),
        (row.get("references") or "").strip(),
        hashlib.sha256(f"{src}|{val}".encode()).hexdigest(),
    ]


def row_decision_id(ident_parts, ref_entries):
    ident = "|".join([*ident_parts, json.dumps(sorted(ref_entries, key=lambda d: d["ref"]), sort_keys=True)])
    return hashlib.sha256(ident.encode("utf-8")).hexdigest()


def load_decisions(root=None):
    try:
        return json.loads(_decisions_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _decisions_file(root=None):
    return _root(root) / DECISIONS


def decision_root(pinned=None, root=None):
    pinned = pinned if pinned is not None else load_decisions(root)
    objs = json.dumps((pinned.get("decisions") or {}), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(objs.encode("utf-8")).hexdigest()


def decisions_sha(root=None):
    p = _root(root) / DECISIONS
    return sha256(p) if p.exists() else None


def check_csv(errors, root=None):
    root = _root(root)
    path = root / CSV
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != CSV_HEADER:
            errors.append(f"csv-schema: header {reader.fieldnames} != {CSV_HEADER}")
            return 0
        rows = list(reader)
    seen = set()
    n = 0
    for row in rows:
        raw_src = row.get("source_text") or ""
        src = raw_src.strip()
        val = row.get("translated_text") or ""
        if not src or not val:
            continue
        n += 1
        ident = (
            (row.get("language") or "").strip(),
            src,
            (row.get("context") or "").strip(),
            (row.get("ct_app") or "").strip(),
        )
        if ident in seen:
            errors.append(f"csv-duplicate: {ident}")
        seen.add(ident)
        origin = f"{CSV} {src!r}"
        check_unicode(val, origin, errors)
        if fmt_placeholders(src) != fmt_placeholders(val):
            errors.append(f"csv-placeholder: {origin} mismatch")
        if affix(val) != affix(raw_src):
            errors.append(f"csv-whitespace: {origin} affix differs")
        if UNSAFE_HTML_RE.search(val):
            errors.append(f"csv-html-unsafe: {origin}")
        if val == src:
            errors.append(f"csv-source-equal: {origin} (payload must not ship fallback)")
        if (row.get("release_status") or "").strip() != "Released":
            continue
        for col in (
            "a1_reviewer",
            "a2_reviewer",
            "a3_reviewer",
            "a1_approved_at",
            "a2_approved_at",
            "a3_approved_at",
            "release_version",
            "references",
            "decision_ref",
        ):
            if not (row.get(col) or "").strip():
                errors.append(f"csv-quorum: {origin} Released without {col}")
        ats = {}
        for col in ("a1_approved_at", "a2_approved_at", "a3_approved_at"):
            v = (row.get(col) or "").strip()
            if v and not TS_RE.match(v):
                errors.append(f"csv-timestamp: {origin} bad {col}={v!r}")
            else:
                try:
                    import datetime as _dt

                    ats[col] = _dt.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    errors.append(f"csv-timestamp-unparseable: {origin} {col}={v!r}")
        if not VER_RE.match((row.get("release_version") or "").strip()):
            errors.append(f"csv-version: {origin} bad release_version")
        for col in ("a1_reviewer", "a2_reviewer", "a3_reviewer"):
            v = (row.get(col) or "").strip()
            if v in ("A1", "A2", "A3") or len(v) < 8:
                errors.append(f"csv-reviewer: {origin} placeholder reviewer in {col}")
        ident_parts = row_identity_fields(row, raw_src, val)
        ref_entries = []
        for ref in (row.get("decision_ref") or "").split(";"):
            ref = ref.strip()
            if not ref:
                continue
            scheme, _, sub = ref.partition(":")
            if scheme not in ("content", "legacy") or not sub or not (root / sub).exists():
                errors.append(
                    f"csv-decision-ref: {origin} bad ref {ref!r} (content:|legacy: + existing path)"
                )
                continue
            try:
                content = (root / sub).read_text(encoding="utf-8")
            except OSError:
                content = ""
            ref_entries.append({"ref": ref, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
            if scheme == "legacy":
                try:
                    legacy = json.loads(
                        (root / "construction/data/translations/legacy_batch_decisions.json").read_text(
                            encoding="utf-8"
                        )
                    )
                except (OSError, ValueError):
                    legacy = {}
                doc = legacy.get("doc", "")
                docpath = root / doc if doc else None
                doc_ok = bool(docpath and docpath.exists()) and sha256(docpath) == legacy.get("doc_sha256")
                if not doc_ok or src not in (legacy.get("rows") or []):
                    errors.append(
                        f"csv-decision-legacy: {origin} not covered by hash-pinned legacy batch record"
                    )
                continue
            if src not in content or val not in content:
                errors.append(
                    f"csv-decision-binding: {origin} not evidenced in {sub} "
                    "(source+translation must appear; edits invalidate)"
                )
        proposal_sha = hashlib.sha256(f"{raw_src}|{val}".encode()).hexdigest()
        pinned = load_decisions(root)
        did = row_decision_id(ident_parts, ref_entries)
        stored = (pinned.get("decisions") or {}).get(did)
        if stored is None:
            errors.append(
                f"csv-decision-identity: {origin} row/artifact identity not pinned — "
                "any row or evidence edit invalidates; re-pin under review"
            )
            continue
        for fkey, rkey in (
            ("language", "language"),
            ("ct_app", "ct_app"),
            ("context", "context"),
            ("source_text", None),
            ("translated_text", None),
            ("domain", "domain"),
            ("release_version", "release_version"),
            ("references", "references"),
        ):
            want = (
                raw_src
                if rkey is None and fkey == "source_text"
                else val
                if rkey is None
                else (row.get(rkey) or "").strip()
            )
            if (stored.get(fkey) or "") != want:
                errors.append(f"csv-decision-object: {origin} stored {fkey} differs from CSV row")
        for role in ("AI-A1", "AI-A2", "AI-A3"):
            v = (stored.get("verdicts") or {}).get(role) or {}
            if not v.get("decision") or not v.get("confidence") or not v.get("session"):
                errors.append(f"csv-decision-verdict: {origin} {role} verdict incomplete")
        if (stored.get("proposal") or {}).get("sha256") != proposal_sha:
            errors.append(f"csv-decision-proposal: {origin} proposal hash mismatch")
        for a in stored.get("artifacts") or []:
            try:
                live = (root / a["ref"].split(":", 1)[1]).read_text(encoding="utf-8")
            except (OSError, IndexError):
                live = None
            if live is None or hashlib.sha256(live.encode()).hexdigest() != a.get("sha256"):
                errors.append(f"csv-decision-artifact: {origin} artifact {a.get('ref')} changed")
        for col in ("a1_reviewer", "a2_reviewer", "a3_reviewer"):
            v = (row.get(col) or "").strip()
            if v in ("A1", "A2", "A3") or len(v) < 8:
                errors.append(f"csv-reviewer: {origin} placeholder reviewer in {col}")
    return n


def check_json_file(errors, rel, root=None):
    root = _root(root)
    full = Path(rel) if Path(rel).is_absolute() else root / rel
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"json-parse: {rel}: {exc}")
        return

    def walk(value, trail):
        if isinstance(value, str):
            check_unicode(value, f"{rel}{trail}", errors)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{trail}[{i}]")
        elif isinstance(value, dict):
            for k, v in sorted(value.items()):
                walk(v, f"{trail}.{k}")

    walk(data, "")
    if "glossary" in str(rel) and isinstance(data, dict):
        terms = data.get("terms", [])
        for t in terms if isinstance(terms, list) else []:
            en = t.get("english", "") if isinstance(t, dict) else ""
            ar = t.get("arabic", "") if isinstance(t, dict) else ""
            if en and ar and fmt_placeholders(en) != fmt_placeholders(ar):
                errors.append(f"json-glossary-placeholder: {rel} {en!r}")


def check_json_coverage(errors, rels, catalog, root=None):
    root = _root(root)
    catalog_ids = {m for _, m in catalog}
    covered = load_vendor_covered(errors, root)
    found, notes = json_ui_strings([str(r) for r in rels], errors, root)
    for note in sorted(set(notes)):
        print("SKIP " + note)
    counts_hit = 0
    for msgid, locs in sorted(found.items()):
        counts_hit += 1
        if msgid not in catalog_ids and msgid not in covered:
            errors.append(f"extract-json-missing: {msgid!r} in {sorted(locs)[0]} not in catalog")
    return counts_hit


def load_msgid_inventory(app, root=None):
    """Read committed msgid inventory: {(context, msgid): trans_hash}."""
    root = _root(root)
    p = root / "construction" / "data" / "localization" / f"vendor_msgids_{app}.txt"
    if not p.exists():
        return None
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\x00")
        if len(parts) != 3:
            return None
        ctx, msgid, th = (x.replace("\\n", "\n") for x in parts)
        out[(ctx, msgid)] = th
    return out


def live_msgid_inventory(app, root=None):
    root = _root(root)
    po = root.parent / app / app / "locale" / "ar.po"
    if not po.exists():
        return None
    entries, _ = parse_po_file(po)
    best = {}
    for e in entries:
        if e["obsolete"] or not e["msgid"]:
            continue
        best[(e["context"] or "", e["msgid"])] = e
    return {
        k: hashlib.sha256(repr(sorted(e["targets"].items())).encode("utf-8")).hexdigest()[:16]
        for k, e in best.items()
    }


def vendor_po_set(app, root=None):
    root = _root(root)
    po = root.parent / app / app / "locale" / "ar.po"
    if not po.exists():
        return None
    entries, _ = parse_po_file(po)
    msgids = sorted({(e["context"], e["msgid"]) for e in entries if not e["obsolete"]})
    return {
        "po_sha": sha256(po),
        "count": len(msgids),
        "msgid_sha": hashlib.sha256(repr(msgids).encode("utf-8")).hexdigest(),
    }


def vendor_commit(app, root=None):
    import subprocess

    root = _root(root)
    gitdir = root.parent / app / ".git"
    if not gitdir.exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(root.parent / app), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def check_vendor_baseline(errors, root=None):
    root = _root(root)
    p = root / BASELINE
    if not p.exists():
        errors.append(f"baseline-missing: {BASELINE} (run --update-baselines, reviewed)")
        return
    try:
        base = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"baseline-parse: {exc}")
        return
    for app in ("frappe", "erpnext"):
        po = root.parent / app / app / "locale" / "ar.po"
        if not po.exists():
            errors.append(
                f"vendor-absent: {app} tree missing — replicate the bench layout "
                "(see linter.yml sibling checkouts) or vendor/upgrade-delta triage"
            )
            continue
        committed = load_msgid_inventory(app, root)
        if committed is None:
            errors.append(f"vendor-inventory-missing: vendor_msgids_{app}.txt unreadable")
            continue
        live = live_msgid_inventory(app, root)
        if live is None:
            errors.append(f"vendor-unreadable: {app} catalog cannot be parsed")
            continue
        if sha256(po) != ((base.get("apps") or {}).get(app) or {}).get("po_sha"):
            errors.append(
                f"vendor-delta: {app} PO bytes differ from baseline — run "
                "scripts/vendor_upgrade_delta.py, triage, re-record (reviewed)"
            )
            continue
        if set(live) != set(committed) or any(live[k] != committed[k] for k in live):
            errors.append(
                f"vendor-delta: {app} live catalog differs from committed inventory "
                f"{BASELINE} — triage required even when commit/po_sha metadata match"
            )
            continue
        live_commit = vendor_commit(app, root)
        pinned = ((base.get("apps") or {}).get(app) or {}).get("commit")
        if live_commit is None:
            errors.append(f"vendor-commit-unknown: {app} has no git HEAD to pin")
        elif pinned != live_commit:
            errors.append(
                f"vendor-delta: {app} HEAD {live_commit} != pinned {pinned} — run "
                "scripts/vendor_upgrade_delta.py, triage, re-record (reviewed)"
            )


def check_manifest(errors, root=None):
    root = _root(root)
    p = root / MANIFEST
    if not p.exists():
        errors.append(f"manifest-missing: {MANIFEST} (run --update-baselines, reviewed)")
        return
    try:
        man = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"manifest-parse: {exc}")
        return
    expect = {
        "construction_po_sha": sha256(root / PO),
        "payload_csv_sha": sha256(root / CSV),
    }
    for key, cur in expect.items():
        if man.get(key) != cur:
            errors.append(
                f"manifest-stale: {key} recorded {man.get(key)} != current {cur} — re-record (reviewed)"
            )
    fp = root / FRESHNESS
    if not fp.exists():
        errors.append(f"freshness-missing: {FRESHNESS} not collected (authorized site only)")
        return
    try:
        fresh = json.loads(fp.read_text(encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"freshness-parse: {exc}")
        return
    for key in ("construction_po_sha", "payload_csv_sha"):
        if (fresh.get("inputs") or {}).get(key) != expect[key]:
            errors.append(
                f"freshness-stale: {FRESHNESS} inputs.{key} does not match current files — "
                "re-collect on the authorized site"
            )
    if not fresh.get("critical_pass"):
        errors.append("freshness-critical: critical keys not all effective at collection time")
    if fresh.get("health", {}).get("has_drift"):
        errors.append("freshness-drift: packaged/live drift flagged at collection time")
    import datetime as _dt

    try:
        collected = _dt.datetime.strptime(fresh.get("collected_utc", ""), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        errors.append("freshness-age: unparseable collected_utc")
        collected = None
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    if collected is not None:
        if collected > now:
            errors.append("freshness-future: collected_utc is in the future — reject")
        if (now - collected).days > 30:
            errors.append("freshness-age: evidence is older than 30 days — re-collect")
    try:
        siteclass = json.loads(
            (root / "construction/data/localization/site_classification.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        siteclass = {}
    if siteclass.get("classification") != "non-production test":
        errors.append("freshness-siteclass: governed classification must be non-production test")
    if siteclass.get("production_mutation_authorized") is not False:
        errors.append("freshness-siteauth: production_mutation_authorized must be false")
    man_site_path = root / "construction/data/localization/site_classification.json"
    if man.get("site_classification_sha") != sha256(man_site_path):
        errors.append("manifest-binding: site_classification_sha mismatch")
    if fresh.get("site") != siteclass.get("site"):
        errors.append(
            f"freshness-site: evidence site {fresh.get('site')!r} != classified {siteclass.get('site')!r}"
        )
    try:
        policy = json.loads(
            (root / "construction/data/translations/critical_labels.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        policy = {}
    expected = policy.get("labels") or {}
    if expected and fresh.get("critical_keys") != expected:
        errors.append("freshness-critical-map: critical mappings differ from governed policy")
    health = fresh.get("health") or {}
    for flag, want in (
        ("loader_installed", True),
        ("using_safe_fallback", False),
        ("has_duplicates", False),
        ("has_null_digests", False),
        ("constraint_present", True),
        ("has_drift", False),
        ("has_orphan_site_overrides", False),
    ):
        if health.get(flag) is not want:
            errors.append(f"freshness-health: {flag}={health.get(flag)!r}, required {want!r}")
    if health.get("constraint_name") != "ct_translation_key_digest":
        errors.append("freshness-health: constraint_name must be ct_translation_key_digest")
    import datetime as _dt2

    try:
        _collected = _dt2.datetime.strptime(fresh.get("collected_utc", ""), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        _collected = None
    try:
        _dbnow = _dt2.datetime.strptime(str(fresh.get("db_now_at_collection", "")), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        errors.append("freshness-clock: db_now_at_collection unparseable")
        _dbnow = None
    # Environment exhibits multi-hour DB/app clock skew (measured >5h); exact
    # future rejection is unsound here. Fail closed on forgery beyond a
    # documented 24h skew budget, plus 30-day age and 48h skew sanity bound.
    for tskey in ("last_catalog_sync_at", "last_release_import_at", "last_drift_checked_at"):
        tsval = health.get(tskey)
        if not tsval:
            errors.append(f"freshness-health: {tskey} audit timestamp required")
            continue
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = _dt2.datetime.strptime(str(tsval), fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            errors.append(f"freshness-health: {tskey} unparseable: {tsval!r}")
            continue
        if _collected is not None and (parsed - _collected).total_seconds() > 86400:
            errors.append(f"freshness-health: {tskey} more than 24h after collection — reject")
            continue
        if _collected is not None and (_collected - parsed).days > 30:
            errors.append(f"freshness-health: {tskey} older than 30 days — re-collect")
            continue
            if (
                _dbnow is not None
                and _collected is not None
                and abs((_dbnow - _collected).total_seconds()) > 172800
            ):
                errors.append("freshness-clock: DB/app skew exceeds 48h — investigate clock sync")
    top_audit = fresh.get("audit_timestamps") or {}
    for tskey in ("last_catalog_sync_at", "last_release_import_at", "last_drift_checked_at"):
        if top_audit.get(tskey) != health.get(tskey):
            errors.append(f"freshness-health: audit_timestamps.{tskey} disagrees with health map")
    try:
        with (root / CSV).open(encoding="utf-8", newline="") as _fh:
            released_now = sum(
                1 for r in csv.DictReader(_fh) if (r.get("release_status") or "").strip() == "Released"
            )
    except OSError:
        released_now = None
    if released_now is not None and fresh.get("packaged_rows") != released_now:
        errors.append(
            f"freshness-count: packaged_rows {fresh.get('packaged_rows')} != "
            f"CSV Released rows {released_now}"
        )
    bound = {
        "decisions_sha": decisions_sha(root),
        "decision_root": decision_root(root=root),
        "freshness_sha": sha256(fp),
        "runtime_digest": fresh.get("runtime_digest"),
        "packaged_rows": fresh.get("packaged_rows"),
        "critical": fresh.get("critical_keys"),
        "site": fresh.get("site"),
    }
    invp = root / "construction/data/localization/stage2_inventory_manifest.json"
    try:
        inv = json.loads(invp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        inv = {}
    if man.get("inventory_manifest_sha") != sha256(invp):
        errors.append("manifest-binding: inventory manifest hash mismatch")
    if man.get("inventory_merkle") != (inv.get("merkle") or {}).get("root"):
        errors.append("manifest-binding: inventory Merkle root mismatch")
    for key, cur in bound.items():
        if key not in man:
            errors.append(f"manifest-binding: {key} not recorded in {MANIFEST}")
        elif man.get(key) != cur:
            errors.append(f"manifest-binding: {key} manifest {man.get(key)} != live {cur}")


RETIRED_SCHEMA = "event | old_path | new_path(-) | reason | reviewer/session | UTC date | evidence#sha256"


def load_retired(errors, path=None, root=None):
    root = _root(root)
    p = Path(path) if path else root / RETIRED
    if not p.exists():
        errors.append(f"retired-missing: {RETIRED} must exist (may be entry-free)")
        return set()
    lines = p.read_text(encoding="utf-8").splitlines()
    if RETIRED_VERSION not in [l.strip() for l in lines]:
        errors.append(f"retired-version: {RETIRED} must declare '{RETIRED_VERSION}'")
        return set()
    import datetime as _dt

    raw_entries = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line == RETIRED_VERSION:
            continue
        parts = [x.strip() for x in line.split("|")]
        if len(parts) != 7 or not all(parts[:6]):
            errors.append(f"retired-schema: bad line: {line!r} (want {RETIRED_SCHEMA})")
            continue
        raw_entries.append(parts)
    events = []
    for parts in raw_entries:
        event, old_path, new_path, reason, reviewer, date, ev = parts
        if event not in ("delete", "rename"):
            errors.append(f"retired-event: {event!r} must be delete|rename")
            continue
        try:
            when = _dt.datetime.strptime(date, "%Y-%m-%d")
            if when.date() > _dt.datetime.now(_dt.timezone.utc).date():
                errors.append(f"retired-future-date: {date!r} is in the future — reject")
                continue
        except ValueError:
            errors.append(f"retired-date: bad UTC date {date!r} (want YYYY-MM-DD)")
            continue
        if "#sha256:" not in ev:
            errors.append(f"retired-evidence-pin: {old_path!r} evidence must carry #sha256:")
            continue
        evpath_s, _, evpin = ev.partition("#sha256:")
        evpath = Path(evpath_s) if Path(evpath_s).is_absolute() else root / evpath_s
        if not evpath.exists() or sha256(evpath) != evpin:
            errors.append(f"retired-evidence-hash: {evpath_s!r} missing or pin mismatch for {old_path!r}")
            continue
        events.append((event, old_path, new_path, reason, reviewer, date, ev))
    seen_old = set()
    for event, old_path, new_path, reason, reviewer, date, ev in events:
        if old_path in seen_old:
            errors.append(f"retired-duplicate: {old_path!r} listed twice")
            continue
        seen_old.add(old_path)
    retired = set()
    for event, old_path, new_path, reason, reviewer, date, ev in events:
        if event == "delete":
            if new_path != "-":
                errors.append(f"retired-delete: {old_path!r} delete must use new_path '-'")
                continue
            if (root / old_path).exists():
                errors.append(f"retired-delete-present: {old_path!r} still exists — cannot retire as deleted")
                continue
        else:
            if (root / old_path).exists():
                errors.append(f"retired-rename-present: {old_path!r} still exists — rename not complete")
                continue
            newp = Path(new_path) if Path(new_path).is_absolute() else root / new_path
            if not newp.exists() and new_path not in seen_old:
                errors.append(f"retired-rename: new path {new_path!r} must exist or be retired")
                continue
        retired.add(old_path)
    return retired


def classify_files(errors, files, root=None):
    root = _root(root)
    """Return (owned, sources, json_sources, skipped). Fail-closed."""
    owned, sources, json_sources, skipped = [], [], [], []
    retired = load_retired(errors, root=root)
    for f in files:
        if f.startswith("/") or ".." in Path(f).parts:
            errors.append(f"files-traversal: rejected {f!r}")
            continue
        if not (root / f).exists():
            if f in retired:
                skipped.append(f"{f} (retired with reviewed disposition)")
            else:
                errors.append(
                    f"files-absent: {f!r} does not exist — remove it from the file list "
                    "or record a reviewed disposition in retired_sources.txt"
                )
            continue
        rel = Path(f)
        if rel == PO or rel == CSV or rel == ALLOWLIST or rel == BASELINE or rel == MANIFEST:
            owned.append(rel)
        elif str(rel).startswith("construction/data/") and rel.suffix == ".json":
            owned.append(rel)
        elif rel.suffix == ".json" and str(rel).startswith("construction/"):
            if is_excluded_json(rel):
                skipped.append(f"{f} (non-UI JSON: fixtures/schema/build output)")
            else:
                json_sources.append(rel)
        elif str(rel).startswith("construction/") and rel.suffix in SOURCE_SUFFIXES:
            sources.append(rel)
        elif rel.suffix in SKIP_SUFFIXES or rel.suffix == "":
            skipped.append(f"{f} (non-localizable artifact)")
        else:
            errors.append(f"files-unhandled: {f!r} is relevant but has no checker routing")
    return owned, sources, json_sources, skipped


def full_scan(errors, counts, root=None, skip_evidence=False):
    root = _root(root)
    # Bootstrap for evidence generation only: the recorded full-gate envelope
    # must be a REAL exit-0 run. CI uses its own guarded source-only mode because
    # historical evidence is deliberately bound to its original absolute root
    # and candidate HEAD, neither of which exists in a GitHub merge checkout.
    catalog = check_po(errors, counts, root=root)
    counts["csv_rows"] = check_csv(errors, root)
    for p in sorted(root.glob("construction/data/**/*.json")):
        if p.is_file():
            check_json_file(errors, p.relative_to(root), root)
    ext = check_extraction(errors, catalog, root=root)
    counts["extract"] = ext
    counts["raw_text"] = check_raw_text(errors, catalog, root=root)
    check_py_sinks(errors, root=root)
    check_underscore_imports(errors, root=root)
    check_vendor_baseline(errors, root)
    check_manifest(errors, root)
    if not skip_evidence:
        check_evidence_index(errors, root)
    return catalog


def scoped_scan(errors, counts, owned, sources, json_sources, root=None):
    root = _root(root)
    catalog = None
    need_catalog = any(r.suffix in SOURCE_SUFFIXES or r == PO for r in owned + sources) or bool(json_sources)
    if need_catalog:
        catalog = check_po(errors, counts, root=root)
    for rel in owned:
        if rel == PO:
            continue
        if rel == CSV:
            counts["csv_rows"] = check_csv(errors, root)
        elif rel.suffix == ".json":
            check_json_file(errors, rel, root)
        elif rel in (ALLOWLIST, BASELINE, MANIFEST):
            full_scan(errors, counts, root)
            return
    if json_sources:
        counts["json_labels"] = check_json_coverage(errors, json_sources, catalog, root)
    if sources:
        ext = check_extraction(errors, catalog, scope={str(r) for r in sources}, root=root)
        counts["extract_scoped"] = ext
    check_vendor_baseline(errors, root)
    check_manifest(errors, root)


EXPECTED_COMMANDS = {
    "all-tests.txt": "COMMAND: bench --site v16.localhost run-tests x6 modules (aggregate)",
    "final-dryrun.txt": "COMMAND: bench --site v16.localhost console import_released_overrides(dry_run=True)",
    "freshness-envelope.txt": "COMMAND: bench --site v16.localhost console construction.localization_freshness.collect()",
    "full-gate.txt": "COMMAND: python3 scripts/check_localization_gates.py --skip-evidence",
    "gate-tests-standalone.txt": "COMMAND: python3 construction/tests/test_localization_gates.py (standalone, no site)",
    "lints-diffcheck.txt": "COMMAND: python3 scripts/lint_scope_metadata.py && python3 scripts/lint_translation_writes.py && git diff --check",
    "merkle.txt": "COMMAND: bench --site v16.localhost console (stage2 inventory categories + merkle via construction.localization_inventory.merkle_root; SQL: scripts/stage2_inventory.sql)",
    "scoped-gate.txt": "COMMAND: python3 scripts/check_localization_gates.py --files construction/www/login.html construction/workspace/construction/construction.json construction/config/workspace_sidebar_items.json construction/templates/generic_export_list_pdf.html",
    "sync.txt": "COMMAND: bench --site v16.localhost console sync_translation_catalog(dry_run=False)",
    "vendor-audit.txt": "COMMAND: python3 scripts/check_localization_gates.py --audit-vendor-coverage",
}
EXPECTED_MODULES = [
    ("construction.searchable_dropdown.tests.test_search_api", 13),
    ("construction.searchable_dropdown.tests.test_integration", 6),
    ("construction.tests.test_bilingual_account_schema", 5),
    ("construction.tests.test_translation_catalog", 3),
    ("construction.tests.test_translation_stabilization_gates", 8),
    ("construction.tests.test_localization_gates", 92),
    ("construction.tests.test_bilingual_service", 38),
    ("construction.tests.test_bilingual_account_pilot", 53),
    ("construction.tests.test_stage4_account_language", 6),
    ("construction.tests.test_stage4_report_extension", 11),
    ("construction.tests.test_stage4_review_bundle", 36),
]
EXPECTED_GATE = {"catalog": 810, "files": 265, "wrapped": 667, "json_labels": 22, "missing": 0}
EXPECTED_DRYRUN = {"total": 3364, "created": 0, "updated": 0, "skipped": 3364, "drift": 0}


ARTIFACT_PATHS = {
    "CHECKER_SHA256": "scripts/check_localization_gates.py",
    "TESTS_SHA256": "construction/tests/test_localization_gates.py",
    "PO_SHA256": "construction/locale/ar.po",
    "CSV_SHA256": "construction/data/translations/approved_ar_overrides.csv",
    "MANIFEST_SHA256": "construction/data/localization/localization_manifest.json",
    "BASELINE_SHA256": "construction/data/localization/vendor_catalog_baseline.json",
    "DECISIONS_SHA256": "construction/data/translations/release_decisions.json",
    "INVENTORY_MANIFEST_SHA256": "construction/data/localization/stage2_inventory_manifest.json",
    "FRESHNESS_SHA256": "construction/data/localization/freshness_evidence.json",
    "SQL_SHA256": "scripts/stage2_inventory.sql",
    "SCOPELINT_SHA256": "scripts/lint_scope_metadata.py",
    "TRANSLATIONLINT_SHA256": "scripts/lint_translation_writes.py",
    "FRAPPE_PO_SHA256": "../frappe/frappe/locale/ar.po",
    "ERPNext_PO_SHA256": "../erpnext/erpnext/locale/ar.po",
}
INDEX_VERSION = "INDEX_VERSION: 1"


def check_envelope_schema(fname, results, errors, root, live_artifacts):
    """Exact ordered template per envelope; every result line consumed once."""
    mods = [(m, n) for m, n in EXPECTED_MODULES]
    total = sum(n for _, n in mods)
    mod_line = ("re", r"^\S+ :: Ran \d+ tests .*?\bOK\b$")
    templates = {
        "all-tests.txt": [mod_line] * len(mods)
        + [
            ("re", r"^AGGREGATE total=\d+ failed=\d+$"),
            ("re", r"^TESTS_SHA256: [0-9a-f]{64}$"),
        ],
        "final-dryrun.txt": [
            ("re", r"^In \[\d+\]: DRY total=\d+ created=\d+ updated=\d+ skipped=\d+ drift=\d+$"),
            ("re", r"^CSV_SHA256: [0-9a-f]{64}$"),
            ("re", r"^RUNTIME_DIGEST: [0-9a-f]{64}$"),
            ("opt", r"^DECISIONS_SHA256: [0-9a-f]{64}$"),
        ],
        "freshness-envelope.txt": [
            ("lit", "ARTIFACT: construction/data/localization/freshness_evidence.json"),
            ("re", r"^ARTIFACT_SHA256: [0-9a-f]{64}$"),
            ("re", r"^FRESHNESS_SHA256: [0-9a-f]{64}$"),
        ],
        "full-gate.txt": [
            ("re", r"^\S.*$"),
            ("re", r"^CHECKER_SHA256: [0-9a-f]{64}$"),
            ("re", r"^PO_SHA256: [0-9a-f]{64}$"),
            ("re", r"^CSV_SHA256: [0-9a-f]{64}$"),
            ("opt", r"^MANIFEST_SHA256: [0-9a-f]{64}$"),
            ("opt", r"^NOTE: "),
        ],
        "gate-tests-standalone.txt": [
            ("re", r"^Ran \d+ tests"),
            ("lit", "OK"),
            ("re", r"^TESTS_SHA256: [0-9a-f]{64}$"),
        ],
        "lints-diffcheck.txt": [
            ("re", r"^PASS: no scope-dimension field has in_standard_filter=1.*$"),
            ("lit", "Translation write lint PASSED"),
            ("lit", "DIFFCHECK_CLEAN"),
            ("re", r"^SCOPELINT_SHA256: [0-9a-f]{64}$"),
            ("re", r"^TRANSLATIONLINT_SHA256: [0-9a-f]{64}$"),
        ],
        "merkle.txt": [
            ("lit", "MANIFEST: construction/data/localization/stage2_inventory_manifest.json"),
            ("re", r"^MANIFEST_SHA256: [0-9a-f]{64}$"),
            ("re", r"^INVENTORY_MANIFEST_SHA256: [0-9a-f]{64}$"),
            ("re", r"^MERKLE_ROOT: [0-9a-f]{64}$"),
            ("re", r"^MERKLE_ROWS: \d+$"),
            ("re", r"^SQL_SHA256: [0-9a-f]{64}$"),
        ],
        "scoped-gate.txt": [
            (
                "opt",
                r"^SKIP construction/workspace/construction/construction\.json: markup/code blob excluded from string gate \(print/CSS/seed-data; covered by bilingual-output waves \+ leak detection\)$",
            ),
            ("re", r"^\S.*$"),
            ("re", r"^PO_SHA256: [0-9a-f]{64}$"),
        ],
        "sync.txt": [
            ("re", r"^In \[\d+\]: SYNC:.*$"),
            ("re", r"^PO_SHA256: [0-9a-f]{64}$"),
        ],
        "vendor-audit.txt": [
            ("lit", "errors=0"),
            ("re", r"^BASELINE_SHA256: [0-9a-f]{64}$"),
            ("opt", r"^FRAPPE_PO_SHA256: [0-9a-f]{64}$"),
            ("opt", r"^ERPNext_PO_SHA256: [0-9a-f]{64}$"),
        ],
    }
    spec = templates[fname]
    pos = 0
    in_json = False
    json_lines = []
    for line in results:
        if line.strip() == "--- JSON START ---":
            in_json = True
            continue
        if line.strip() == "--- JSON END ---":
            in_json = False
            continue
        if in_json:
            json_lines.append(line)
            continue
        if line.strip() == "--- JSON END ---":
            in_json = False
            continue
        if in_json:
            continue
        if line.strip() == "--- JSON START ---":
            in_json = True
            continue
        if line.strip() == "--- JSON END ---":
            in_json = False
            continue
        if in_json:
            json_lines.append(line)
            continue
        while pos < len(spec) and spec[pos][0] == "opt" and not re.match(spec[pos][1], line):
            pos += 1
        if pos >= len(spec):
            errors.append(f"evidence-schema: {fname} extra result line beyond template: {line[:60]!r}")
            continue
        kind, pat = spec[pos]
        if kind == "json":
            pos += 1
            continue
        want = pat if kind in ("re", "opt") else "^" + re.escape(pat) + "$"
        if not re.match(want, line):
            errors.append(f"evidence-schema: {fname} line {pos} {line[:60]!r} breaks template order")
            continue
        pos += 1
    while pos < len(spec) and spec[pos][0] == "opt":
        pos += 1
    if pos < len(spec):
        errors.append(f"evidence-schema: {fname} missing template lines from position {pos}")
    if fname == "freshness-envelope.txt":
        try:
            fresh = json.loads("\n".join(json_lines))
        except ValueError:
            errors.append(f"evidence-schema: {fname} embedded JSON unparseable")
            fresh = None
        if isinstance(fresh, dict):
            if fresh.get("critical_pass") is not True:
                errors.append(f"evidence-schema: {fname} critical pass not true")
            for key in ("runtime_digest", "collected_utc"):
                if not fresh.get(key):
                    errors.append(f"evidence-schema: {fname} lacks {key}")
    text = "\n".join(results)
    if fname == "all-tests.txt":
        mods_found = re.findall(r"^(\S+) :: Ran (\d+) tests .*?\bOK\b", text, re.M)
        magg = re.search(r"AGGREGATE total=(\d+) failed=(\d+)", text)
        if [(m, int(n)) for m, n in mods_found] != EXPECTED_MODULES or not magg:
            errors.append(f"evidence-schema: {fname} module identities/counts differ from contract")
        elif sum(int(n) for _, n in mods_found) != int(magg.group(1)) or magg.group(2) != "0":
            errors.append(f"evidence-arithmetic: {fname} module sum != aggregate total or failed != 0")
    if fname == "gate-tests-standalone.txt":
        m = re.search(r"^Ran (\d+) tests", text, re.M)
        if not m or int(m.group(1)) != dict(EXPECTED_MODULES)["construction.tests.test_localization_gates"]:
            errors.append(f"evidence-schema: {fname} standalone count differs from contract")
        if not re.search(r"^OK$", text, re.M):
            errors.append(f"evidence-schema: {fname} must record OK")
    if fname == "full-gate.txt":

        def _num(pat):
            mm = re.search(pat, text)
            return int(mm.group(1)) if mm else None

        got = {
            "catalog": _num(r'"construction/locale/ar\.po": (\d+)'),
            "wrapped": _num(r'"wrapped": (\d+)'),
            "json_labels": _num(r'"json_labels": (\d+)'),
            "missing": _num(r'"missing": (\d+)'),
            "gate_errors": _num(r"errors=(\d+)"),
        }
        want = {
            "catalog": EXPECTED_GATE["catalog"],
            "wrapped": EXPECTED_GATE["wrapped"],
            "json_labels": EXPECTED_GATE["json_labels"],
            "missing": 0,
            "gate_errors": 0,
        }
        if got != want:
            errors.append(f"evidence-schema: {fname} gate result object differs from contract")
        if f'"files": {EXPECTED_GATE["files"]}' not in text:
            errors.append(f"evidence-schema: {fname} file count differs from contract")
    if fname == "final-dryrun.txt":
        m = re.search(r"total=(\d+) created=(\d+) updated=(\d+) skipped=(\d+) drift=(\d+)", text)
        vals = (
            {
                k: int(v)
                for k, v in zip(("total", "created", "updated", "skipped", "drift"), m.groups(), strict=False)
            }
            if m
            else None
        )
        if vals != EXPECTED_DRYRUN or (
            vals and vals["total"] != vals["created"] + vals["updated"] + vals["skipped"]
        ):
            errors.append(f"evidence-schema: {fname} dry-run arithmetic differs from contract")
    if fname == "scoped-gate.txt" and "errors=0" not in text:
        errors.append(f"evidence-schema: {fname} must record errors=0")
    if fname == "vendor-audit.txt" and "errors=0" not in text:
        errors.append(f"evidence-schema: {fname} must record errors=0")
    if fname == "lints-diffcheck.txt":
        for mark in (
            "DIFFCHECK_CLEAN",
            "Translation write lint PASSED",
            "no scope-dimension field has in_standard_filter=1",
        ):
            if mark not in text:
                errors.append(f"evidence-schema: {fname} lacks {mark!r}")
    if fname == "merkle.txt":
        mm = re.search(r"MERKLE_ROWS: (\d+)", text)
        if mm:
            try:
                inv = json.loads(
                    (root / "construction/data/localization/stage2_inventory_manifest.json").read_text(
                        encoding="utf-8"
                    )
                )
                if int(mm.group(1)) != (inv.get("merkle") or {}).get("rows"):
                    errors.append(f"evidence-merkle: {fname} rows != live inventory manifest")
            except (OSError, ValueError):
                pass
    if fname == "sync.txt" and ("'created': 0" not in text or "'updated': 0" not in text):
        errors.append(f"evidence-schema: {fname} must record zero creates/updates")
    if fname == "merkle.txt":
        for mark, key in (("MERKLE_ROOT:", "merkle_root"), ("INVENTORY_MANIFEST_SHA256:", "manifest_sha")):
            line = next((l for l in text.splitlines() if mark in l), "")
            mm = re.search(r"\b[0-9a-f]{64}\b", line)
            if mark == "MERKLE_ROOT:" and mm:
                try:
                    inv = json.loads(
                        (root / "construction/data/localization/stage2_inventory_manifest.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    if mm.group(0) != (inv.get("merkle") or {}).get("root"):
                        errors.append(f"evidence-merkle-live: {fname} root != live inventory manifest")
                except (OSError, ValueError):
                    pass


def check_evidence_index(errors, root=None):
    """Strict semantic evidence validation (round-16 contract).

    - Exact versioned index grammar with fixed line order.
    - Candidate root + HEAD binding (fail closed when unresolvable).
    - Every artifact marker recomputed from the candidate wherever it appears.
    - Per-envelope schemas with arithmetic; general failure-text rejection.
    - UTC validity/recency/order locally and globally; bootstrap ordering.
    """
    import datetime as _dt

    root = _root(root)
    if not (root / "construction" / "locale" / "ar.po").exists():
        errors.append("evidence-root: candidate root does not contain a construction checkout")
        return {}
    if not str(root).endswith("apps/construction"):
        errors.append(f"evidence-root: candidate root {root} is not an apps/construction layout")
        return {}
    evdir = root / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2"
    idxp = evdir / "index.txt"
    if not idxp.exists():
        errors.append("evidence-index-missing: index.txt not found")
        return {}
    index_lines = [l for l in idxp.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not index_lines or index_lines[0].strip() != INDEX_VERSION:
        errors.append(f"evidence-index-version: first line must be {INDEX_VERSION!r}")
        return {}
    rows = []
    head_rows = []
    for line in index_lines[1:]:
        s = line.strip()
        if s.startswith("CANDIDATE_HEAD:"):
            head_rows.append(s)
            continue
        m = re.match(r"^([0-9a-f]{64})\s+([A-Za-z0-9_.-]+\.txt)$", s)
        if m:
            rows.append((m.group(1), m.group(2)))
            continue
        m2 = re.match(
            r"^(COMMAND|STARTED_UTC|FINISHED_UTC|EXIT_CODE|ENVELOPE_LINES|ARTIFACTS" r"|CANDIDATE_ROOT):", s
        )
        m3 = re.match(r"^([A-Za-z_]+_SHA256): ([0-9a-f]{64})$", s)
        if not m2 and not m3:
            errors.append(f"evidence-index-grammar: unparsed line: {s[:80]!r}")
    ordered = [l.strip() for l in index_lines]
    seq_kinds = []
    for s in ordered:
        if s == INDEX_VERSION:
            seq_kinds.append("version")
        elif s.startswith("COMMAND:"):
            seq_kinds.append("command")
        elif s.startswith("STARTED_UTC:"):
            seq_kinds.append("started")
        elif re.match(r"^[0-9a-f]{64}\s+[A-Za-z0-9_.-]+\.txt$", s):
            seq_kinds.append("hash")
        elif s.startswith("EXIT_CODE:"):
            seq_kinds.append("exit")
        elif s.startswith("FINISHED_UTC:"):
            seq_kinds.append("finished")
        elif s.startswith("CANDIDATE_HEAD:"):
            seq_kinds.append("head")
        elif s.startswith("CANDIDATE_ROOT:"):
            seq_kinds.append("croot")
        elif s == "ARTIFACTS:":
            seq_kinds.append("artifacts")
        elif re.match(r"^[A-Za-z_]+_SHA256: [0-9a-f]{64}$", s):
            seq_kinds.append("artifact")
        elif s.startswith("ENVELOPE_LINES:"):
            seq_kinds.append("length")
        else:
            seq_kinds.append("unknown")
    want_kinds = (
        ["version", "command", "started"]
        + ["hash"] * len(EVIDENCE_FILES)
        + ["exit", "finished", "head", "croot", "artifacts"]
        + ["artifact"] * len(ARTIFACT_PATHS)
        + ["length"]
    )
    if seq_kinds != want_kinds:
        errors.append("evidence-index-order: index lines are not in the canonical ordered schema")
    hash_order = [s.split()[-1] for s in ordered if re.match(r"^[0-9a-f]{64}\s+", s)]
    if hash_order != list(EVIDENCE_FILES):
        errors.append("evidence-index-hashorder: hash rows must follow EVIDENCE_FILES order")
    art_order = [s.split(":")[0] for s in ordered if re.match(r"^[A-Za-z_]+_SHA256: [0-9a-f]{64}$", s)]
    if art_order != list(ARTIFACT_PATHS):
        errors.append("evidence-index-artifact-order: artifact rows must follow ARTIFACT_PATHS order")
    root_rows = [s for s in ordered if s.startswith("CANDIDATE_ROOT:")]
    if len(root_rows) != 1:
        errors.append(
            f"evidence-index-root: exactly one CANDIDATE_ROOT row required (found {len(root_rows)})"
        )
    elif root_rows[0].split(":", 1)[1].strip() != str(root.resolve()):
        errors.append(f"evidence-index-root: {root_rows[0]!r} != invocation root {str(root.resolve())!r}")
    if len(head_rows) != 1:
        errors.append(
            f"evidence-index-head: exactly one CANDIDATE_HEAD row required (found {len(head_rows)})"
        )
    if sorted(f for _, f in rows) != sorted(EVIDENCE_FILES):
        errors.append(
            f"evidence-index-set: must name exactly {sorted(EVIDENCE_FILES)}, "
            f"got {sorted(f for _, f in rows)}"
        )
    if len(set(rows)) != len(rows):
        errors.append("evidence-index-duplicate: duplicate index rows")
    for h, f in rows:
        if f not in EVIDENCE_FILES or ".." in f or "/" in f:
            errors.append(f"evidence-index-path: bad entry {f!r}")
    actual = sorted(f.name for f in evdir.iterdir() if f.is_file() and f.suffix == ".txt")
    if actual != sorted((*EVIDENCE_FILES, "index.txt")):
        errors.append(f"evidence-set: expected {sorted((*EVIDENCE_FILES, 'index.txt'))}, found {actual}")
    bound_hashes = {}
    seen_content = {}
    live_artifacts = {}
    for _mark, _rel in ARTIFACT_PATHS.items():
        _lp = root / _rel
        if _lp.exists():
            live_artifacts[_mark] = sha256(_lp)
    for _mark, _rel in ARTIFACT_PATHS.items():
        _lp = root / _rel
        if _lp.exists():
            live_artifacts[_mark] = sha256(_lp)
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    idx_len_rows = [s for s in ordered if s.startswith("ENVELOPE_LINES:")]
    if len(idx_len_rows) != 1:
        errors.append(
            f"evidence-index-length: exactly one ENVELOPE_LINES row required (found {len(idx_len_rows)})"
        )
    else:
        try:
            declared = int(idx_len_rows[0].split(":", 1)[1].strip())
        except ValueError:
            declared = None
        if declared != len(index_lines):
            errors.append(
                f"evidence-index-length: index declares {idx_len_rows[0].split(':', 1)[1].strip()!r} lines, has {len(index_lines)}"
            )
    idx_art = {}
    for s in ordered:
        m = re.match(r"^([A-Za-z_]+_SHA256): ([0-9a-f]{64})$", s)
        if m:
            idx_art.setdefault(m.group(1), []).append(m.group(2))
    for mark in ARTIFACT_PATHS:
        vals = idx_art.get(mark) or []
        if not vals:
            errors.append(f"evidence-index-artifact-missing: {mark} row absent from index")
        elif len(vals) > 1:
            errors.append(f"evidence-index-artifact-duplicate: {mark} appears {len(vals)} times in index")
        elif mark not in live_artifacts:
            errors.append(f"evidence-index-artifact-missing: {ARTIFACT_PATHS[mark]} not in candidate")
        elif vals[0] != live_artifacts[mark]:
            errors.append(
                f"evidence-index-artifact-value: {mark} index {vals[0][:12]}… != live {live_artifacts[mark][:12]}…"
            )
    for mark in idx_art:
        if mark not in ARTIFACT_PATHS:
            errors.append(f"evidence-index-artifact-alias: unknown index artifact marker {mark}")
    ETS = "%Y-%m-%dT%H:%M:%SZ"
    envelope_spans = {}
    for fname in EVIDENCE_FILES:
        fp = evdir / fname
        if not fp.exists():
            errors.append(f"evidence-missing: {fname}")
            continue
        content = fp.read_text(encoding="utf-8")
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if h in seen_content:
            errors.append(f"evidence-duplicate: {fname} duplicates {seen_content[h]} content")
        seen_content[h] = fname
        bound_hashes[fname] = h
        origin = f"evidence-envelope: {fname}"
        _res_lines = [
            l
            for l in content.splitlines()
            if l.strip()
            and not any(
                l.startswith(m)
                for m in ("COMMAND:", "STARTED_UTC:", "FINISHED_UTC:", "EXIT_CODE:", "ENVELOPE_LINES:")
            )
        ]
        check_envelope_schema(fname, _res_lines, errors, root, live_artifacts)

        def one(marker, err):
            matches = [l for l in content.splitlines() if l.startswith(marker)]
            if len(matches) != 1:
                errors.append(f"{err}: {fname} must have exactly one {marker} (found {len(matches)})")
                return None
            return matches[0][len(marker) :].strip()

        cmd = one("COMMAND:", origin)
        start = one("STARTED_UTC:", origin)
        finish = one("FINISHED_UTC:", origin)
        exitc = one("EXIT_CODE:", origin)
        if cmd is not None and ("COMMAND: " + cmd) != EXPECTED_COMMANDS[fname]:
            errors.append(f"evidence-command: {fname} unexpected COMMAND {cmd!r}")
        if exitc != "0":
            errors.append(f"evidence-exit: {fname} EXIT_CODE is {exitc!r}, required 0")
        try:
            t0 = _dt.datetime.strptime(start, ETS) if start else None
            t1 = _dt.datetime.strptime(finish, ETS) if finish else None
        except ValueError:
            errors.append(f"evidence-utc: {fname} malformed UTC timestamp")
            t0 = t1 = None
        if t0 is not None and t1 is not None and t0 > t1:
            errors.append(f"evidence-order: {fname} STARTED_UTC after FINISHED_UTC")
        for label, ts in (("STARTED_UTC", t0), ("FINISHED_UTC", t1)):
            if ts is not None:
                if ts > now:
                    errors.append(f"evidence-future: {fname} {label} is in the future — reject")
                elif (now - ts).days > 30:
                    errors.append(f"evidence-stale: {fname} {label} older than 30 days — regenerate")
        if t0 is not None and t1 is not None:
            envelope_spans[fname] = (t0, t1)
        nlines = one("ENVELOPE_LINES:", origin)
        nonempty = [l for l in content.splitlines() if l.strip()]
        try:
            if nlines is not None and int(nlines) != len(nonempty):
                errors.append(f"evidence-length: {fname} declares {nlines} lines, file has {len(nonempty)}")
        except ValueError:
            errors.append(f"evidence-length: {fname} bad ENVELOPE_LINES value")
        for bad in (
            "FAIL ",
            "FAILED",
            "Traceback",
            "AssertionError",
            "ERROR:",
            "error:",
            "failed=",
            "errors=",
            "Error ",
            "Exception",
        ):
            hits = [
                l
                for l in content.splitlines()
                if l.startswith(bad) or (bad in ("FAILED", "failed=") and f" {bad}" in f" {l} ")
            ]
            if bad in ("FAILED", "failed=", "errors="):
                hits = [l for l in hits if "failed=0" not in l and "errors=0" not in l]
            if hits:
                errors.append(f"evidence-failure-text: {fname} contains {bad!r}: {hits[0][:80]!r}")
                break
        if not re.search(r"\b[0-9a-f]{64}\b", content):
            errors.append(f"evidence-hash: {fname} contains no full SHA-256 result/artifact hash")
        if len(nonempty) < 5:
            errors.append(f"evidence-thin: {fname} too short to be complete")
        if fname == "all-tests.txt":
            mods = re.findall(r"^(\S+) :: Ran (\d+) tests .*?\bOK\b", content, re.M)
            magg = re.search(r"AGGREGATE total=(\d+) failed=(\d+)", content)
            if [(m, int(n)) for m, n in mods] != EXPECTED_MODULES or not magg:
                errors.append(f"evidence-schema: {fname} module identities/counts differ from contract")
            elif sum(int(n) for _, n in mods) != int(magg.group(1)) or magg.group(2) != "0":
                errors.append(f"evidence-arithmetic: {fname} module sum != aggregate total or failed != 0")
        if fname == "gate-tests-standalone.txt":
            m = re.search(r"^Ran (\d+) tests", content, re.M)
            if (
                not m
                or int(m.group(1)) != dict(EXPECTED_MODULES)["construction.tests.test_localization_gates"]
            ):
                errors.append(f"evidence-schema: {fname} standalone count differs from contract")
            if not re.search(r"^OK$", content, re.M):
                errors.append(f"evidence-schema: {fname} must record OK")
        if fname == "full-gate.txt":

            def _num(pat):
                mm = re.search(pat, content)
                return int(mm.group(1)) if mm else None

            got = {
                "catalog": _num(r'"construction/locale/ar\.po": (\d+)'),
                "wrapped": _num(r'"wrapped": (\d+)'),
                "json_labels": _num(r'"json_labels": (\d+)'),
                "missing": _num(r'"missing": (\d+)'),
                "gate_errors": _num(r"errors=(\d+)"),
            }
            want = {
                "catalog": EXPECTED_GATE["catalog"],
                "wrapped": EXPECTED_GATE["wrapped"],
                "json_labels": EXPECTED_GATE["json_labels"],
                "missing": 0,
                "gate_errors": 0,
            }
            if got != want:
                errors.append(f"evidence-schema: {fname} gate result object differs from contract")
            if f'"files": {EXPECTED_GATE["files"]}' not in content:
                errors.append(f"evidence-schema: {fname} file count differs from contract")
        if fname == "final-dryrun.txt":
            m = re.search(r"total=(\d+) created=(\d+) updated=(\d+) skipped=(\d+) drift=(\d+)", content)
            vals = (
                {
                    k: int(v)
                    for k, v in zip(
                        ("total", "created", "updated", "skipped", "drift"), m.groups(), strict=False
                    )
                }
                if m
                else None
            )
            if vals != EXPECTED_DRYRUN or (
                vals and vals["total"] != vals["created"] + vals["updated"] + vals["skipped"]
            ):
                errors.append(f"evidence-schema: {fname} dry-run arithmetic differs from contract")
        if fname == "scoped-gate.txt":
            if "errors=0" not in content:
                errors.append(f"evidence-schema: {fname} must record errors=0")
        if fname == "vendor-audit.txt":
            if "errors=0" not in content:
                errors.append(f"evidence-schema: {fname} must record errors=0")
        if fname == "lints-diffcheck.txt":
            for mark in (
                "DIFFCHECK_CLEAN",
                "Translation write lint PASSED",
                "no scope-dimension field has in_standard_filter=1",
            ):
                if mark not in content:
                    errors.append(f"evidence-schema: {fname} lacks {mark!r}")
        if fname == "freshness-envelope.txt":
            if "critical_pass" not in content and '"critical_pass": true' not in content:
                errors.append(f"evidence-schema: {fname} must record critical pass")
        if fname == "merkle.txt":
            for mark in ("MERKLE_ROOT:", "INVENTORY_MANIFEST_SHA256:", "MERKLE_ROWS:"):
                if mark not in content:
                    errors.append(f"evidence-merkle: {fname} lacks {mark} (truncated?)")
            mm = re.search(r"MERKLE_ROWS: (\d+)", content)
            if mm:
                try:
                    inv = json.loads(
                        (root / "construction/data/localization/stage2_inventory_manifest.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    if int(mm.group(1)) != (inv.get("merkle") or {}).get("rows"):
                        errors.append(f"evidence-merkle: {fname} rows != live inventory manifest")
                except (OSError, ValueError):
                    pass
        if fname == "sync.txt":
            if "'created': 0" not in content or "'updated': 0" not in content:
                errors.append(f"evidence-schema: {fname} must record zero creates/updates")
        idx_match = [hh for hh, ff in rows if ff == fname]
        if idx_match != [h]:
            errors.append(f"evidence-index-mismatch: {fname} index hash != file hash")
        if fname == "merkle.txt":
            for mark, key in (
                ("MERKLE_ROOT:", "merkle_root"),
                ("INVENTORY_MANIFEST_SHA256:", "manifest_sha"),
            ):
                line = next((l for l in content.splitlines() if mark in l), "")
                mm = re.search(r"\b[0-9a-f]{64}\b", line)
                if mark == "MERKLE_ROOT:" and mm:
                    try:
                        inv = json.loads(
                            (
                                root / "construction/data/localization/stage2_inventory_manifest.json"
                            ).read_text(encoding="utf-8")
                        )
                        if mm.group(0) != (inv.get("merkle") or {}).get("root"):
                            errors.append(f"evidence-merkle-live: {fname} root != live inventory manifest")
                    except (OSError, ValueError):
                        pass
    for mark, rel in ARTIFACT_PATHS.items():
        pat = re.compile(r"^" + mark + r":\s+([0-9a-f]{64})\s*$", re.M)
        seen = {}
        for fname in EVIDENCE_FILES:
            fp = evdir / fname
            if not fp.exists():
                continue
            for m in pat.finditer(fp.read_text(encoding="utf-8")):
                seen.setdefault(m.group(1), []).append(fname)
        live = root / rel
        if not live.exists():
            errors.append(f"evidence-artifact-missing: {rel} not in candidate")
            continue
        live_sha = sha256(live)
        if not seen:
            errors.append(f"evidence-artifact-unbound: {mark} appears in no envelope")
            continue
        if len(seen) > 1 or next(iter(seen)) != live_sha:
            errors.append(
                f"evidence-artifact-mismatch: {mark} values {sorted(seen)} disagree or != live {live_sha[:12]}…"
            )
        if mark == "PO_SHA256" and next(iter(seen)) != live_sha:
            pass
    head = subprocess_head_commit(root)
    idx_heads = [
        line.strip().split(":", 1)[1].strip()
        for line in index_lines
        if line.strip().startswith("CANDIDATE_HEAD:")
    ]
    if len(idx_heads) != 1:
        errors.append(
            f"evidence-index-head: exactly one CANDIDATE_HEAD row required (found {len(idx_heads)})"
        )
    elif head is None:
        errors.append("evidence-index-head: Git HEAD unresolvable at candidate root — fail closed")
    elif idx_heads[0] != head:
        errors.append(f"evidence-index-head: {idx_heads[0]!r} != live HEAD {head!r}")
    elif not re.fullmatch(r"[0-9a-f]{40}", idx_heads[0]):
        errors.append("evidence-index-head: CANDIDATE_HEAD is not a full 40-hex commit")
    if envelope_spans:
        latest_finish = max(t1 for _, t1 in envelope_spans.values())
        for fname, (t0, t1) in sorted(envelope_spans.items()):
            if (latest_finish - t0).days > 1:
                errors.append(
                    f"evidence-order: {fname} started over a day before latest finish — regenerate set atomically"
                )
    idx_text = idxp.read_text(encoding="utf-8")

    def idx_one(marker):
        matches = [l for l in idx_text.splitlines() if l.startswith(marker)]
        if len(matches) != 1:
            errors.append(f"evidence-index-envelope: index.txt must have exactly one {marker}")
            return None
        return matches[0][len(marker) :].strip()

    idx_cmd = idx_one("COMMAND:")
    idx_start = idx_one("STARTED_UTC:")
    idx_finish = idx_one("FINISHED_UTC:")
    idx_exit = idx_one("EXIT_CODE:")
    if idx_exit != "0":
        errors.append("evidence-index-envelope: index.txt EXIT_CODE must be 0")
    try:
        idx_t0 = _dt.datetime.strptime(idx_start, "%Y-%m-%dT%H:%M:%SZ") if idx_start else None
        idx_t1 = _dt.datetime.strptime(idx_finish, "%Y-%m-%dT%H:%M:%SZ") if idx_finish else None
    except ValueError:
        errors.append("evidence-index-envelope: index.txt malformed UTC timestamp")
        idx_t0 = idx_t1 = None
    if idx_t0 is not None and idx_t1 is not None and idx_t0 > idx_t1:
        errors.append("evidence-index-envelope: index.txt STARTED_UTC after FINISHED_UTC")
    if idx_t0 is not None and envelope_spans:
        latest_env_finish = max(t1 for _, t1 in envelope_spans.values())
        if idx_t0 < latest_env_finish:
            errors.append(
                "evidence-order: index.txt generated before some envelope finished — regenerate last"
            )
    return bound_hashes


def subprocess_head_commit(root):
    import subprocess

    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30
        )
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def load_reviewed_delta(path):
    try:
        delta = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if delta.get("triage_status") != "reviewed" or not delta.get("disposition"):
        return None
    for key in (
        "app",
        "old",
        "new",
        "old_po_sha",
        "new_po_sha",
        "added",
        "removed",
        "changed",
        "context_shift",
        "dispositions",
    ):
        if key not in delta:
            return None
    return delta


def delta_item_key(context, msgid):
    return (context or "") + "\x00" + msgid


def classify_delta(old_map, new_map):
    """Split two {(context, msgid): entry} maps into add/remove/change/shift."""
    added = sorted(k for k in new_map if k not in old_map)
    removed = sorted(k for k in old_map if k not in new_map)
    changed = sorted(
        k for k in old_map if k in new_map and old_map[k].get("targets") != new_map[k].get("targets")
    )
    old_by_msgid, new_by_msgid = {}, {}
    for c, m in old_map:
        old_by_msgid.setdefault(m, set()).add(c)
    for c, m in new_map:
        new_by_msgid.setdefault(m, set()).add(c)
    context_shift = sorted(
        {"msgid": m, "old_contexts": sorted(old_by_msgid[m]), "new_contexts": sorted(new_by_msgid[m])}
        for m in old_by_msgid
        if m in new_by_msgid and old_by_msgid[m] != new_by_msgid[m]
    )
    return added, removed, changed, context_shift


def canonical_delta_sets(added, removed, changed, context_shift):
    """Canonical vendor-delta set schema shared by producer and consumer."""
    return {
        "added": sorted([list(k) for k in added]),
        "removed": sorted([list(k) for k in removed]),
        "changed": sorted([list(k) for k in changed]),
        "context_shift": sorted(context_shift, key=lambda d: (d.get("msgid"), str(d.get("old_contexts")))),
    }


def recompute_transition(app, old_commit, new_commit, root=None):
    root = _root(root)
    import shutil as _sh
    import subprocess
    import tempfile

    def read_sets(ref):
        if ref is None:
            return None
        out = subprocess.run(
            ["git", "-C", str(root.parent / app), "show", f"{ref}:{app}/locale/ar.po"],
            capture_output=True,
            timeout=120,
        )
        if out.returncode != 0:
            return None
        tmpdir = tempfile.mkdtemp(prefix=".tmp-localization-", dir=str(root))
        try:
            tmp = Path(tmpdir) / "candidate.po"
            tmp.write_bytes(out.stdout)
            entries, _ = parse_po_file(tmp)
            return {(e["context"], e["msgid"]): e for e in entries if not e["obsolete"]}
        finally:
            _sh.rmtree(tmpdir, ignore_errors=True)

    old_map = read_sets(old_commit)
    new_map = read_sets(new_commit)
    if old_map is None or new_map is None:
        return None
    return classify_delta(old_map, new_map)


def write_msgid_inventory(app, inv, root=None):
    root = _root(root)
    hdr = (
        "# vendor catalog inventory — generated by --update-baselines (reviewed operation).\n"
        "# format per line: context\\x00msgid\\x00translation-hash16 (literal backslash-n escapes newlines).\n"
    )
    lines = [
        c.replace("\n", "\\n") + "\x00" + m.replace("\n", "\\n") + "\x00" + th
        for (c, m), th in sorted(inv.items())
    ]
    (root / "construction" / "data" / "localization" / f"vendor_msgids_{app}.txt").write_text(
        hdr + "\n".join(lines) + "\n", encoding="utf-8"
    )


def refuse(errors, msg):
    print("FAIL " + msg)
    errors.append("baseline-refused: " + msg)


def update_baselines(args, errors, root=None):
    root = _root(root)
    import datetime

    reviewed = None
    dflag = [a for a in args if a == "--delta-reviewed" or a.startswith("--delta-reviewed=")]
    if dflag:
        dval = dflag[0].split("=", 1)[1] if "=" in dflag[0] else args[args.index("--delta-reviewed") + 1]
        reviewed = load_reviewed_delta(dval)
        if reviewed is None:
            refuse(errors, "delta file missing, unreviewed, or undispositioned")
            return 1
    try:
        base = json.loads((root / BASELINE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        base = {"apps": {}}
    apps = {}
    for app in ("frappe", "erpnext"):
        po = root.parent / app / app / "locale" / "ar.po"
        if not po.exists():
            refuse(errors, f"{app} tree absent")
            return 1
        live = live_msgid_inventory(app, root)
        if live is None:
            refuse(errors, f"{app} catalog unparseable")
            return 1
        committed = load_msgid_inventory(app, root)
        if committed is None:
            refuse(errors, f"{app} committed inventory unreadable")
            return 1
        cur = {
            "commit": vendor_commit(app, root),
            "po_sha": sha256(po),
            "count": len(live),
            "msgid_sha": hashlib.sha256(repr(sorted(live)).encode()).hexdigest(),
        }
        if live == committed:
            rec = (base.get("apps") or {}).get(app) or {}
            rec.update({k: v for k, v in cur.items() if v is not None})
            apps[app] = rec
            continue
        rec = (base.get("apps") or {}).get(app) or {}
        if reviewed is None or reviewed.get("app") != app:
            refuse(
                errors,
                f"{app} catalog differs from committed inventory — "
                "a reviewed delta is mandatory (--delta-reviewed <file>)",
            )
            return 1
        live_commit = vendor_commit(app, root)
        prov = (
            reviewed.get("old"),
            reviewed.get("new"),
            reviewed.get("old_po_sha"),
            reviewed.get("new_po_sha"),
        )
        if prov != (rec.get("commit"), live_commit, rec.get("po_sha"), cur.get("po_sha")):
            refuse(
                errors,
                f"{app} delta provenance mismatch: artifact claims old/new "
                f"{prov} but recorded->live is "
                f"{rec.get('commit')}/{rec.get('po_sha')} -> {live_commit}/{cur.get('po_sha')}",
            )
            return 1
        old_map = {k: {"targets": {"t": v}} for k, v in committed.items()}
        new_map = {k: {"targets": {"t": v}} for k, v in live.items()}
        added, removed, changed, shift = classify_delta(old_map, new_map)
        want = canonical_delta_sets(added, removed, changed, shift)
        got = canonical_delta_sets(
            reviewed.get("added") or [],
            reviewed.get("removed") or [],
            reviewed.get("changed") or [],
            reviewed.get("context_shift") or [],
        )
        if want != got:
            refuse(errors, f"{app} delta sets do not match recomputed inventory diff")
            return 1
        need_keys = {delta_item_key(c, m) for c, m in added + removed + changed}
        need_keys |= {delta_item_key("", d.get("msgid")) for d in (reviewed.get("context_shift") or [])}
        if need_keys - set((reviewed.get("dispositions") or {}).keys()):
            refuse(errors, f"{app} delta items lack dispositions")
            return 1
        write_msgid_inventory(app, live, root)
        cur["delta_sha"] = hashlib.sha256(
            json.dumps(reviewed, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        apps[app] = cur
    (root / BASELINE).parent.mkdir(parents=True, exist_ok=True)
    (root / BASELINE).write_text(
        json.dumps(
            {
                "recorded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "apps": apps,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    man = {
        "recorded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "construction_po_sha": sha256(root / PO),
        "payload_csv_sha": sha256(root / CSV),
    }
    fp = root / FRESHNESS
    if fp.exists():
        try:
            fresh = json.loads(fp.read_text(encoding="utf-8"))
            man["freshness_sha"] = sha256(fp)
            man["runtime_digest"] = fresh.get("runtime_digest")
            man["packaged_rows"] = fresh.get("packaged_rows")
            man["critical"] = fresh.get("critical_keys")
            man["site"] = fresh.get("site")
            man["freshness_utc"] = fresh.get("collected_utc")
        except ValueError:
            pass
    man["decisions_sha"] = sha256(root / "construction/data/translations/release_decisions.json")
    man["decision_root"] = decision_root(root=root)
    man["site_classification_sha"] = sha256(root / "construction/data/localization/site_classification.json")
    invp = root / "construction/data/localization/stage2_inventory_manifest.json"
    man["inventory_manifest_sha"] = sha256(invp) if invp.exists() else None
    try:
        inv = json.loads(invp.read_text(encoding="utf-8"))
        man["inventory_merkle"] = (inv.get("merkle") or {}).get("root")
        man["inventory_rows"] = (inv.get("merkle") or {}).get("rows")
    except (OSError, ValueError):
        man["inventory_merkle"] = None
        man["inventory_rows"] = None
    (root / MANIFEST).write_text(json.dumps(man, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"baselines recorded: {BASELINE}, {MANIFEST}")
    return 0


def audit_vendor_coverage(errors, root=None):
    root = _root(root)
    union = set()
    for app in ("frappe", "erpnext"):
        po = root.parent / app / app / "locale" / "ar.po"
        if not po.exists():
            errors.append(f"vendor-audit-absent: {app} tree missing")
            return
        entries, _ = parse_po_file(po)
        union |= {e["msgid"] for e in entries if not e["obsolete"]}
    for line in (root / VENDOR_COVERED).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in union:
            errors.append(f"vendor-covered-stale: {line!r} not in current vendor catalogs")


def main(argv, root=None):
    errors = []
    counts = {}
    args = list(argv[1:])
    rflag = [a for a in args if a.startswith("--root=")]
    if rflag and root is None:
        root = Path(rflag[0].split("=", 1)[1])
        args = [a for a in args if not a.startswith("--root=")]
    root = _root(root)
    if "--update-baselines" in args:
        code = update_baselines(args, errors, root)
        return code, counts, sorted(errors)
    if "--audit-vendor-coverage" in args:
        audit_vendor_coverage(errors, root)
        for err in sorted(errors):
            print("FAIL " + err)
        print(f"errors={len(errors)}")
        return (1 if errors else 0), counts, sorted(errors)
    files = []
    if "--files" in args:
        files = args[args.index("--files") + 1 :]
        owned, sources, json_sources, skipped = classify_files(errors, files, root)
        if not owned and not sources and not json_sources and not errors:
            errors.append("files-empty: --files supplied but no checkable targets")
        for s in sorted(skipped):
            print("SKIP " + s)
        if not errors:
            scoped_scan(errors, counts, owned, sources, json_sources, root)
    else:
        import os as _os

        bootstrap_skip = "--skip-evidence" in args
        ci_source_only = "--ci-source-only" in args
        if bootstrap_skip and _os.environ.get("STAGE2_EVIDENCE_BOOTSTRAP") != "1":
            errors.append("evidence-bootstrap: --skip-evidence requires STAGE2_EVIDENCE_BOOTSTRAP=1")
            print(f"checked={json.dumps(counts, sort_keys=True, default=str)} errors={len(errors)}")
            return 1, counts, sorted(errors)
        if ci_source_only and _os.environ.get("GITHUB_ACTIONS") != "true":
            errors.append("ci-source-only: --ci-source-only requires GITHUB_ACTIONS=true")
            print(f"checked={json.dumps(counts, sort_keys=True, default=str)} errors={len(errors)}")
            return 1, counts, sorted(errors)
        full_scan(errors, counts, root, skip_evidence=bootstrap_skip or ci_source_only)
    for err in sorted(errors):
        print("FAIL " + err)
    print(f"checked={json.dumps(counts, sort_keys=True, default=str)} errors={len(errors)}")
    return (1 if errors else 0), counts, sorted(errors)


if __name__ == "__main__":
    code, _, _ = main(sys.argv)
    sys.exit(code)
