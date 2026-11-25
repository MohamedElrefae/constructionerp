"""Fresh authorization and request-local lifecycle guards for P1 WBS.

The dedicated reader opens a separate read-only REPEATABLE READ consistent
snapshot on the site's primary database. Authorization inputs are read from
that snapshot only; the module never substitutes Frappe's cached role,
metadata or User Permission getters for a positive decision.

Reconnect behavior, stated against the installed mysqlclient source (pinned
above): the driver exposes no Python-visible reconnect setting, so an
``auto_reconnect`` attribute assignment would only create a dead Python
attribute and would not affect driver reconnect behavior.  Reconnection is
controlled by the client library's ``MYSQL_OPT_RECONNECT`` option, settable
only through ``ping(reconnect=...)`` and persistent for the connection's
lifetime.  The reader never calls ``ping`` and refuses it on its connection
for the snapshot's lifetime.  The library's reconnect state at connection
creation is not readable from Python, so this module does not claim to have
verified it; transaction-state checks detect demonstrated drift only.
"""

from __future__ import annotations

import ast
import contextlib
import contextvars
import hashlib
import importlib
import re
import sys
import types
from pathlib import Path

import frappe

from construction.services import execution_tree_rules as rules

MAX_DESCENDANT_ROWS = 10000
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]*$")

# The Frappe and ERPNext hook sources are pinned by the reviewed source packet.
# The Construction hook hash is bound to the repaired candidate and is checked
# together with the source-to-serving seal.
PINNED_HOOK_HASHES = {
    "frappe": "31eaac57b360a2f33d97bdaa2d30134d74d50fd532cab932d5b565d45b35d4fe",
    "erpnext": "28c286e338e7e28cdc8d23cc2168d52251da49c012c21de64d839d484be5c310",
    "construction": "d9be9643fae1be421f2e95ae8d7d1d0e250c2d0a8d85d5c58e350ebe45c74766",
}

# The reader's reconnect behavior was reviewed against the installed mysqlclient
# source.  A different driver generation must be re-inspected before use.
PINNED_MYSQLDB_VERSION = (2, 2, 7)

CONSTRUCTION_SERVING_MODULES = (
    ("construction.services.execution_tree_access", "services/execution_tree_access.py"),
    ("construction.services.execution_tree", "services/execution_tree.py"),
    ("construction.services.execution_tree_rules", "services/execution_tree_rules.py"),
    ("construction.api.execution_tree_api", "api/execution_tree_api.py"),
    ("construction.setup.execution_tree_schema", "setup/execution_tree_schema.py"),
    (
        "construction.construction.doctype.execution_breakdown_node.execution_breakdown_node",
        "construction/doctype/execution_breakdown_node/execution_breakdown_node.py",
    ),
    (
        "construction.construction.doctype.execution_code_counter.execution_code_counter",
        "construction/doctype/execution_code_counter/execution_code_counter.py",
    ),
)

PROJECT_CONTROLLER = ("erpnext.projects.doctype.project.project", "Project")
PROJECT_USER_CONTROLLER = ("erpnext.projects.doctype.project_user.project_user", "ProjectUser")

# Stock controller sources are pinned by full-blob SHA-256. The Project anchor
# comes from the reviewed source packet; the Project User anchor is bound to
# the same pinned ERPNext commit 7474d9e786277383de1242ab882f16856d17a9c9.
PINNED_CONTROLLER_SOURCES = {
    "erpnext.projects.doctype.project.project": (
        "projects/doctype/project/project.py",
        "639fda6b7a25ab4b18b067bac65cf6d87705606fad2c0977ab296dd251022918",
    ),
    "erpnext.projects.doctype.project_user.project_user": (
        "projects/doctype/project_user/project_user.py",
        "c8343961c20c4e98bbaed1171edc890f8ace8ed92ec35b62665987370850698c",
    ),
}

# Finite transactional engine allowlist for every authority table queried by
# the fresh snapshot reader.
TRANSACTIONAL_ENGINES = frozenset({"innodb"})

_QUERIED_TABLE_RE = re.compile(r"`tab([^`]+)`|(?<![\w`])tab([A-Za-z][A-Za-z0-9_]*)")

_GUARD = contextvars.ContextVar("construction_execution_tree_guard", default=None)

# A capability authorizes only the permission types implied by its operation.
_GUARD_PTYPES = {
    "read": frozenset({"read", "select"}),
    "create": frozenset({"create"}),
    "update": frozenset({"write"}),
    "move": frozenset({"write"}),
    "set_disabled": frozenset({"write"}),
    "delete": frozenset({"delete"}),
    "counter": frozenset({"read", "write", "create", "delete"}),
}


class AccessDenied(Exception):
    """The caller is not authorized. Never disclose whether a Project exists."""


class UnsupportedProfile(Exception):
    """The installed permission profile is outside the reviewed inventory."""


class IntegrityFailure(Exception):
    """Persisted execution-tree state is inconsistent."""


def _refuse_ping(*args, **kwargs):
    """Refuse every ping on the reader connection.

    The installed mysqlclient exposes no Python-visible reconnect setting.  Its
    client-library ``MYSQL_OPT_RECONNECT`` option is controlled only through
    ``ping(reconnect=...)`` and persists for the connection's lifetime, so
    refusing ping keeps that path from enabling silent reconnection while the
    reader holds its snapshot.
    """

    raise UnsupportedProfile("Reconnect attempt refused")


def _disable_reconnect(connection):
    """Bind the fail-closed ping refusal to the reader connection."""

    connection.ping = _refuse_ping


class FreshAuthorityReader:
    """Read-only consistent-snapshot reader on the primary MariaDB server."""

    def __init__(self):
        self._connection = None
        self._cursor = None
        self._queried_tables = set()

    def __enter__(self):
        try:
            import MySQLdb
            import MySQLdb.cursors
            import MySQLdb.release
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise UnsupportedProfile("MySQLdb is unavailable.") from exc
        if MySQLdb.release.version_info[:3] != PINNED_MYSQLDB_VERSION:
            raise UnsupportedProfile("The installed MySQLdb driver is outside the reviewed generation.")
        settings = _connection_settings()
        settings["cursorclass"] = MySQLdb.cursors.DictCursor
        connection = MySQLdb.connect(**settings)
        self._connection = connection
        try:
            _disable_reconnect(connection)
            self._cursor = connection.cursor()
            # MariaDB does not reflect `START TRANSACTION ... READ ONLY` in
            # @@tx_read_only, so the session default must be set for the
            # read-only guarantee to be both enforced and observable here.
            self._cursor.execute("SET SESSION tx_read_only = 1")
            self._cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            self._cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
            self._verify_transaction()
        except Exception:
            self.close()
            raise
        return self

    def _verify_transaction(self):
        self._cursor.execute("SELECT @@tx_isolation AS isolation, @@tx_read_only AS read_only")
        row = self._cursor.fetchone() or {}
        isolation = str(row.get("isolation") or "").upper().replace("_", "-")
        if isolation != "REPEATABLE-READ":
            raise UnsupportedProfile("Unexpected transaction isolation.")
        if int(row.get("read_only") or 0) != 1:
            raise UnsupportedProfile("Authorization transaction is not read-only.")

    def query(self, sql, params=None):
        self._record_tables(sql)
        self._cursor.execute(sql, params or ())
        return list(self._cursor.fetchall() or [])

    def one(self, sql, params=None):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def _record_tables(self, sql):
        for match in _QUERIED_TABLE_RE.finditer(sql):
            name = match.group(1) or match.group(2)
            if name and IDENTIFIER_RE.match(name):
                self._queried_tables.add(name)

    def verify_storage_engines(self):
        """Every table actually queried must exist and be transactional.

        A consistent snapshot does not cover nontransactional storage, so an
        unsupported engine or a missing queried table denies the profile.
        """

        tables = sorted(self._queried_tables)
        if not tables:
            return True
        names = [f"tab{table}" for table in tables]
        rows = self.query(
            "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN (" + ",".join(["%s"] * len(names)) + ")",
            tuple(names),
        )
        engines = {row.get("TABLE_NAME"): str(row.get("ENGINE") or "").lower() for row in rows}
        for name in names:
            engine = engines.get(name)
            if engine is None:
                raise UnsupportedProfile("A queried authority table is missing.")
            if engine not in TRANSACTIONAL_ENGINES:
                raise UnsupportedProfile("A queried authority table is not transactional.")
        return True

    def close(self):
        if self._connection is not None:
            try:
                self._connection.rollback()
            finally:
                try:
                    self._connection.close()
                finally:
                    self._connection = None
                    self._cursor = None

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _connection_settings():
    db = getattr(frappe.local, "db", None)
    if db is None or not hasattr(db, "get_connection_settings"):
        raise UnsupportedProfile("The site database connection is unavailable.")
    settings = dict(db.get_connection_settings())
    return settings


def _read_installed_apps(reader):
    rows = reader.query(
        "SELECT defvalue FROM tabDefaultValue " "WHERE parent='__global' AND defkey='installed_apps'"
    )
    if len(rows) != 1:
        raise UnsupportedProfile("The installed-app registry is missing or ambiguous.")
    try:
        return rules.parse_installed_apps(rows[0].get("defvalue"))
    except rules.RuleViolation as exc:
        raise UnsupportedProfile(str(exc.message)) from exc


def _app_root(app):
    try:
        path = Path(frappe.get_app_path(app)).resolve()
    except Exception as exc:
        raise UnsupportedProfile(f"Cannot resolve the {app} app root.") from exc
    if not path.is_dir():
        raise UnsupportedProfile(f"The {app} app root is unavailable.")
    return path


def _read_regular_source(path, root):
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UnsupportedProfile("A source file escapes its canonical app root.") from exc
    if path.is_symlink() or not resolved.is_file():
        raise UnsupportedProfile("A canonical source file is missing or not regular.")
    raw = resolved.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedProfile("A canonical source file is not UTF-8.") from exc
    return text, hashlib.sha256(raw).hexdigest(), resolved


def _project_profile_source(installed):
    roots = {app: _app_root(app) for app in installed}
    sources = {}
    projections = {}
    dispatch_events = {}
    for app in installed:
        text, digest, resolved = _read_regular_source(roots[app] / "hooks.py", roots[app])
        expected = PINNED_HOOK_HASHES.get(app)
        if expected and digest != expected:
            raise UnsupportedProfile(f"The {app} hook source does not match the reviewed generation.")
        try:
            mode = "construction" if app == "construction" else "vendor"
            projection = rules.extract_hook_projection(text, filename=str(resolved), mode=mode)
            rules.validate_hook_projection(app, projection)
            dispatch_events[app] = rules.extract_relevant_doc_events(text, filename=str(resolved))
        except rules.HookProjectionError as exc:
            raise UnsupportedProfile(str(exc.message)) from exc
        sources[app] = {"path": str(resolved), "sha256": digest}
        projections[app] = projection
    return roots, sources, projections, dispatch_events


def _table_present(reader, table):
    row = reader.one(
        "SELECT COUNT(*) AS total FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s",
        (table,),
    )
    return bool(row and int(row.get("total") or 0))


def _assert_no_enabled_server_scripts(reader):
    if not _table_present(reader, "Server Script"):
        return
    try:
        rows = reader.query("SELECT name FROM `Server Script` WHERE enabled=1 LIMIT 1")
    except Exception as exc:
        raise UnsupportedProfile("Enabled Server Script state is unreadable.") from exc
    if rows:
        raise UnsupportedProfile("An enabled Server Script is outside the supported profile.")


def _assert_no_protected_metadata(reader):
    for doctype in rules.PROTECTED_DOCTYPES:
        for table, column in (
            ("Custom DocPerm", "parent"),
            ("Custom Field", "dt"),
            ("Property Setter", "doc_type"),
        ):
            if not _table_present(reader, table):
                continue
            row = reader.one(
                f"SELECT COUNT(*) AS total FROM `tab{table}` WHERE `{column}`=%s",
                (doctype,),
            )
            if row and int(row.get("total") or 0):
                raise UnsupportedProfile(f"Custom metadata for {doctype} is unsupported.")


def _assert_no_active_workflows(reader):
    if not _table_present(reader, "Workflow"):
        return
    protected = ("Project", "Project User", *rules.PROTECTED_DOCTYPES)
    placeholders = ",".join(["%s"] * len(protected))
    try:
        rows = reader.query(
            f"SELECT name FROM `Workflow` WHERE is_active=1 AND document_type IN ({placeholders}) LIMIT 1",
            protected,
        )
    except Exception as exc:
        raise UnsupportedProfile("Workflow state is unreadable.") from exc
    if rows:
        raise UnsupportedProfile("An active Workflow for a protected DocType is unsupported.")


def _same_constant(expected, actual, path):
    """Structural comparison; ``repr`` is not stable for set iteration order."""

    if isinstance(expected, types.CodeType):
        if not isinstance(actual, types.CodeType):
            return False
        _compare_code(expected, actual, path + "/" + expected.co_name)
        return True
    if isinstance(expected, tuple | list):
        return (
            type(expected) is type(actual)
            and len(expected) == len(actual)
            and all(_same_constant(a, b, path) for a, b in zip(expected, actual, strict=True))
        )
    if isinstance(expected, set | frozenset):
        if type(expected) is not type(actual) or len(expected) != len(actual):
            return False
        remaining = list(actual)
        for item in expected:
            for index, other in enumerate(remaining):
                if type(item) is type(other) and _same_constant(item, other, path):
                    del remaining[index]
                    break
            else:
                return False
        return True
    if isinstance(expected, dict):
        if type(expected) is not type(actual) or len(expected) != len(actual):
            return False
        remaining = list(actual.keys())
        for key in expected:
            for index, other in enumerate(remaining):
                if type(key) is type(other) and _same_constant(key, other, path):
                    if not _same_constant(expected[key], actual[other], path):
                        return False
                    del remaining[index]
                    break
            else:
                return False
        return True
    return type(expected) is type(actual) and expected == actual


def _compare_code(expected, actual, path=""):
    attributes = (
        "co_argcount",
        "co_posonlyargcount",
        "co_kwonlyargcount",
        "co_nlocals",
        "co_flags",
        "co_code",
        "co_names",
        "co_varnames",
        "co_freevars",
        "co_cellvars",
        "co_name",
    )
    for attribute in attributes:
        if getattr(expected, attribute) != getattr(actual, attribute):
            raise UnsupportedProfile(f"Serving code differs from source at {path or expected.co_name}.")
    if len(expected.co_consts) != len(actual.co_consts):
        raise UnsupportedProfile(f"Serving code constants differ at {path or expected.co_name}.")
    for expected_const, actual_const in zip(expected.co_consts, actual.co_consts, strict=True):
        if not _same_constant(expected_const, actual_const, path):
            raise UnsupportedProfile("Serving code constants differ from source.")


def _unwrap_callable(value):
    if isinstance(value, classmethod | staticmethod):
        value = value.__func__
    if isinstance(value, property):
        value = value.fget
    while hasattr(value, "__wrapped__"):
        value = value.__wrapped__
    return value


def _source_defaults(source, filename):
    """Derive expected function defaults from source without executing it.

    Only literal defaults (including previously resolved literal module names)
    are inspectable; any other default expression denies the seal.
    """

    tree = ast.parse(source, filename=str(filename))
    env = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    try:
                        env[target.id] = rules._literal(statement.value, env)
                    except rules.HookProjectionError:
                        env.pop(target.id, None)
    expected = {}

    def visit(body, prefix):
        for child in body:
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                qualname = prefix + child.name
                try:
                    positional = tuple(rules._literal(item, env) for item in child.args.defaults)
                    keyword = {
                        argument.arg: rules._literal(item, env)
                        for argument, item in zip(child.args.kwonlyargs, child.args.kw_defaults, strict=True)
                        if item is not None
                    }
                except rules.HookProjectionError as exc:
                    raise UnsupportedProfile(
                        f"Default values of {qualname} are not source-inspectable."
                    ) from exc
                expected[qualname] = (positional, keyword)
                visit(child.body, qualname + ".")
            elif isinstance(child, ast.ClassDef):
                visit(child.body, prefix + child.name + ".")

    visit(tree.body, "")
    return expected


def _check_defaults(expected_defaults, qualname, function):
    entry = expected_defaults.get(qualname)
    if entry is None:
        return
    positional, keyword = entry
    if tuple(function.__defaults__ or ()) != positional:
        raise UnsupportedProfile(f"Serving defaults differ from source at {qualname}.")
    if dict(function.__kwdefaults__ or {}) != keyword:
        raise UnsupportedProfile(f"Serving keyword defaults differ from source at {qualname}.")


def _seal_class(expected_body, cls, prefix="", expected_defaults=None):
    expected_defaults = expected_defaults or {}
    for const in expected_body.co_consts:
        if not isinstance(const, types.CodeType):
            continue
        if const.co_name == "<lambda>":
            continue
        attribute = getattr(cls, const.co_name, None)
        if attribute is None:
            continue
        function = _unwrap_callable(attribute)
        qualname = f"{prefix}{cls.__name__}.{const.co_name}"
        if isinstance(function, types.FunctionType):
            _compare_code(const, function.__code__, qualname)
            _check_defaults(expected_defaults, qualname, function)
        elif isinstance(function, type):
            _seal_class(
                const, function, prefix=f"{prefix}{cls.__name__}.", expected_defaults=expected_defaults
            )
        else:
            raise UnsupportedProfile(f"Sealed class member {const.co_name} is not a function.")


def _seal_module(module_name, source, filename, root, *, required):
    module = sys.modules.get(module_name)
    if module is None:
        if not required:
            return
        raise UnsupportedProfile(f"Serving module {module_name} is not loaded.")
    module_file = getattr(module, "__file__", None)
    if not module_file:
        raise UnsupportedProfile(f"Serving module {module_name} has no file identity.")
    try:
        if Path(module_file).resolve() != Path(filename).resolve():
            raise UnsupportedProfile(f"Serving module {module_name} resolves to a different source file.")
        Path(module_file).resolve().relative_to(root)
    except ValueError as exc:
        raise UnsupportedProfile(f"Serving module {module_name} is outside its canonical root.") from exc
    compiled = compile(source, str(filename), "exec", dont_inherit=True)
    expected_defaults = _source_defaults(source, filename)
    for const in compiled.co_consts:
        if not isinstance(const, types.CodeType):
            continue
        if const.co_name == "<lambda>":
            continue
        attribute = getattr(module, const.co_name, None)
        if attribute is None:
            continue
        function = _unwrap_callable(attribute)
        qualname = f"{module_name}.{const.co_name}"
        if isinstance(function, types.FunctionType):
            _compare_code(const, function.__code__, qualname)
            _check_defaults(expected_defaults, const.co_name, function)
        elif isinstance(function, type):
            _seal_class(const, function, expected_defaults=expected_defaults)


def _assert_serving_seal(roots):
    construction_root = roots["construction"]
    for module_name, relative in CONSTRUCTION_SERVING_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            raise UnsupportedProfile(f"Serving module {module_name} cannot be loaded.") from exc
        text, _digest, resolved = _read_regular_source(construction_root / relative, construction_root)
        _seal_module(module_name, text, resolved, construction_root, required=True)


def _assert_controller_identity(roots):
    for module_name, class_name in (PROJECT_CONTROLLER, PROJECT_USER_CONTROLLER):
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            raise UnsupportedProfile(f"Stock controller module {module_name} cannot be loaded.") from exc
        module_file = getattr(module, "__file__", None)
        if not module_file:
            raise UnsupportedProfile(f"Stock controller module {module_name} has no file identity.")
        try:
            Path(module_file).resolve().relative_to(roots["erpnext"])
        except ValueError as exc:
            raise UnsupportedProfile(f"Stock controller {class_name} is outside the ERPNext root.") from exc
        controller = getattr(module, class_name, None)
        if not isinstance(controller, type):
            raise UnsupportedProfile(f"Stock controller {class_name} is unavailable.")
        if controller.__module__ != module_name or controller.__qualname__ != class_name:
            raise UnsupportedProfile(f"Stock controller {class_name} has an unexpected origin.")
        from frappe.model.document import Document

        if not issubclass(controller, Document):
            raise UnsupportedProfile(f"Stock controller {class_name} is not a Document controller.")
        relative, expected_hash = PINNED_CONTROLLER_SOURCES[module_name]
        text, digest, resolved = _read_regular_source(roots["erpnext"] / relative, roots["erpnext"])
        if digest != expected_hash:
            raise UnsupportedProfile(
                f"Stock controller {class_name} source does not match the pinned generation."
            )
        if Path(module_file).resolve() != resolved:
            raise UnsupportedProfile(f"Stock controller {class_name} is loaded from a different source file.")
        # Seal the loaded controller code (including lifecycle methods such as
        # before_rename/validate/on_trash) against the hash-verified source.
        _seal_module(module_name, text, resolved, roots["erpnext"], required=True)


def _normalize_hook_value(value):
    """Canonicalize a hook value for source/serving comparison.

    ``frappe.get_hooks`` listifies handler registrations per key (mapping a
    scalar handler to a one-element list), while the AST projection preserves
    the literal scalar. Normalize both sides to ordered lists so comparison is
    structural rather than dependent on which representation was observed.
    """

    if not value:
        return {}
    if isinstance(value, dict):
        return {key: _normalize_hook_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_hook_scalar(item) for item in value]
    return [_normalize_hook_scalar(value)]


def _normalize_hook_scalar(item):
    if isinstance(item, dict):
        return {key: _normalize_hook_value(value) for key, value in item.items()}
    if isinstance(item, list | tuple):
        return [_normalize_hook_scalar(value) for value in item]
    return item


def _assert_loaded_hooks_match(installed, projections, dispatch_events):
    """Compare the bound source projection with the serving hook module.

    ``frappe.get_hooks`` is only a comparison subject here; it never
    establishes what the registration should be. ``doc_events`` is compared
    in full for Construction and over the relevant dispatch inventory for the
    vendor apps, whose complete event dictionaries are additionally bound by
    their pinned full-blob hook hashes.
    """

    for app in installed:
        for hook in (
            "has_permission",
            "permission_query_conditions",
            "override_doctype_class",
            "extend_doctype_class",
            "get_child_provider",
        ):
            try:
                loaded = frappe.get_hooks(hook, app_name=app)
            except Exception as exc:
                raise UnsupportedProfile("Loaded hook registrations are uninspectable.") from exc
            if _normalize_hook_value(loaded) != _normalize_hook_value(projections[app].get(hook)):
                raise UnsupportedProfile(
                    f"Loaded {hook} registrations for {app} do not match the bound source."
                )
        try:
            loaded_events = frappe.get_hooks("doc_events", app_name=app)
        except Exception as exc:
            raise UnsupportedProfile("Loaded doc_events registrations are uninspectable.") from exc
        if app == "construction":
            expected_events = projections[app].get("doc_events") or {}
            if _normalize_hook_value(loaded_events) != _normalize_hook_value(expected_events):
                raise UnsupportedProfile(
                    "Loaded doc_events registrations for construction do not match the bound source."
                )
        else:
            loaded_subset = {
                doctype: loaded_events.get(doctype)
                for doctype in rules.RELEVANT_DISPATCH_DOCTYPES
                if doctype in (loaded_events or {})
            }
            if _normalize_hook_value(loaded_subset) != _normalize_hook_value(dispatch_events.get(app) or {}):
                raise UnsupportedProfile(
                    f"Loaded relevant doc_events registrations for {app} do not match the bound source."
                )


def _assert_dispatch_map_match(installed, dispatch_events):
    """Compare the materialized serving event dispatch map with bound source.

    A stale ``frappe.local.doc_events_hooks`` map (for example one captured
    before a Project before_rename or DocShare validate registration changed)
    must deny even when the per-app loaded hook values still match.
    """

    expected = rules.merge_doc_events([dispatch_events[app] for app in installed])
    try:
        actual = frappe.get_doc_hooks()
    except Exception as exc:
        raise UnsupportedProfile("The serving event dispatch map is uninspectable.") from exc
    for doctype in sorted(rules.RELEVANT_DISPATCH_DOCTYPES):
        if _normalize_hook_value(actual.get(doctype) or {}) != _normalize_hook_value(
            expected.get(doctype) or {}
        ):
            raise UnsupportedProfile(
                f"The serving dispatch map for {doctype} does not match the bound source."
            )


def _assert_supported_profile(reader):
    installed = _read_installed_apps(reader)
    roots, sources, projections, dispatch_events = _project_profile_source(installed)
    _assert_loaded_hooks_match(installed, projections, dispatch_events)
    _assert_dispatch_map_match(installed, dispatch_events)
    _assert_no_enabled_server_scripts(reader)
    _assert_no_active_workflows(reader)
    _assert_no_protected_metadata(reader)
    _assert_controller_identity(roots)
    _assert_serving_seal(roots)
    return {
        "installed": installed,
        "sources": sources,
        "roots": roots,
        "projections": projections,
        "dispatch_events": dispatch_events,
    }


def _recheck_profile(profile):
    installed = profile["installed"]
    roots, sources, projections, dispatch_events = _project_profile_source(installed)
    if sources != profile["sources"] or roots != profile["roots"]:
        raise UnsupportedProfile("The deployment generation changed during authorization.")
    if projections != profile["projections"] or dispatch_events != profile["dispatch_events"]:
        raise UnsupportedProfile("A relevant hook registration changed during authorization.")
    _assert_loaded_hooks_match(installed, projections, dispatch_events)
    _assert_dispatch_map_match(installed, dispatch_events)
    _assert_controller_identity(roots)
    _assert_serving_seal(roots)
    return True


def _settings(reader, doctype, fields):
    rows = reader.query(
        "SELECT field, value FROM tabSingles WHERE doctype=%s AND field IN ("
        + ",".join(["%s"] * len(fields))
        + ")",
        tuple([doctype, *fields]),
    )
    return {row["field"]: row["value"] for row in rows}


def _read_user(reader, user):
    row = reader.one(
        "SELECT name, enabled, user_type FROM tabUser WHERE name=%s",
        (user,),
    )
    if not row:
        raise AccessDenied("User is unavailable.")
    if int(row.get("enabled") or 0) != 1:
        raise AccessDenied("User is disabled.")
    return row


AUTOMATIC_ROLES = frozenset({"Guest", "All", "Desk User", "Administrator"})


def _read_roles(reader, user, user_type):
    rows = reader.query(
        "SELECT role FROM `tabHas Role` WHERE parenttype='User' AND parent=%s ORDER BY idx",
        (user,),
    )
    roles = {row["role"] for row in rows if row.get("role") and row.get("role") not in AUTOMATIC_ROLES}
    roles.update({"All", "Guest"})
    if user_type == "System User":
        roles.add("Desk User")
    return roles


def _validate_permission_rows(rows):
    for row in rows:
        if not isinstance(row.get("role"), str) or not row.get("role"):
            raise UnsupportedProfile("A permission row has no role identity.")
        permlevel = row.get("permlevel")
        if not isinstance(permlevel, int) or isinstance(permlevel, bool) or permlevel < 0:
            raise UnsupportedProfile("A permission row has an invalid permlevel.")
        for right in rules.PERMISSION_RIGHTS:
            value = row.get(right)
            if value not in (0, 1, None):
                raise UnsupportedProfile("A permission row has an invalid flag value.")
        if row.get("if_owner") not in (0, 1, None):
            raise UnsupportedProfile("A permission row has an invalid owner flag.")
    return rows


def _read_project(reader, project):
    row = reader.one("SELECT * FROM tabProject WHERE name=%s", (project,))
    if not row:
        raise AccessDenied("Project is unavailable.")
    return row


def _read_fields(reader, doctype):
    stock_rows = reader.query(
        "SELECT fieldname, fieldtype, options, ignore_user_permissions, permlevel, idx, hidden, reqd, read_only, is_virtual "
        "FROM `tabDocField` WHERE parent=%s ORDER BY idx",
        (doctype,),
    )
    custom_rows = reader.query(
        "SELECT fieldname, fieldtype, options, ignore_user_permissions, permlevel, idx, hidden, reqd, read_only, is_virtual "
        "FROM `tabCustom Field` WHERE dt=%s ORDER BY idx",
        (doctype,),
    )
    fields = []
    stock_names = set()
    for row in stock_rows:
        field = _normalize_field(row)
        name = field.get("fieldname")
        if not name or name in stock_names:
            raise UnsupportedProfile("Duplicate or empty stock field definition.")
        if field.get("is_virtual"):
            raise UnsupportedProfile("A virtual or computed field is unsupported.")
        stock_names.add(name)
        fields.append(field)
    index = {field["fieldname"]: field for field in fields}
    if doctype in ("Project", "Project User"):
        _validate_stock_metadata(reader, doctype, fields)
    custom_names = set()
    for row in custom_rows:
        field = _normalize_field(row)
        name = field.get("fieldname")
        if not name or name in custom_names:
            raise UnsupportedProfile("Duplicate custom field definition.")
        custom_names.add(name)
        if name in stock_names:
            raise UnsupportedProfile("A custom field shadows a stock field.")
        if field.get("is_virtual"):
            raise UnsupportedProfile("A virtual or computed custom field is unsupported.")
        try:
            rules.validate_custom_field_definition(field, doctype=doctype)
        except rules.RuleViolation as exc:
            raise UnsupportedProfile(str(exc.message)) from exc
        if field.get("fieldtype") == "Link":
            _assert_custom_link_storage(reader, doctype, name)
        fields.append(field)
        index[name] = field

    setters = reader.query(
        "SELECT field_name, property, value, property_type, doctype_or_field "
        "FROM `tabProperty Setter` WHERE doc_type=%s",
        (doctype,),
    )
    seen_setters = set()
    for setter in setters:
        if setter.get("doctype_or_field") != "DocField":
            raise UnsupportedProfile("DocType-level Property Setters are unsupported.")
        field_name = setter.get("field_name")
        field = index.get(field_name)
        if field is None:
            raise UnsupportedProfile("A Property Setter targets a missing field.")
        prop = setter.get("property")
        key = (field_name, prop)
        if key in seen_setters:
            raise UnsupportedProfile("Duplicate or conflicting Property Setters are unsupported.")
        seen_setters.add(key)
        try:
            field[prop] = rules.cast_property_setter(
                prop, setter.get("value"), setter.get("property_type"), fieldname=field_name
            )
        except rules.RuleViolation as exc:
            raise UnsupportedProfile(str(exc.message)) from exc
    return fields


def _assert_custom_link_storage(reader, doctype, fieldname):
    """Require a supported custom Link to be an ordinary physical column."""

    if not IDENTIFIER_RE.match(doctype or "") or not IDENTIFIER_RE.match(fieldname or ""):
        raise UnsupportedProfile("Unsupported custom Link identity.")
    row = reader.one(
        "SELECT DATA_TYPE AS data_type FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (f"tab{doctype}", fieldname),
    )
    if not row:
        raise UnsupportedProfile("A custom Link field has no physical storage column.")
    data_type = str(row.get("data_type") or "").lower()
    if data_type not in ("char", "varchar", "text", "mediumtext", "longtext"):
        raise UnsupportedProfile("A custom Link field has an unsupported storage type.")


def _int_or_original(value):
    if value is None:
        return 0
    if isinstance(value, bool):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _normalize_field(row):
    return {
        "fieldname": row.get("fieldname"),
        "fieldtype": row.get("fieldtype"),
        "options": row.get("options"),
        "ignore_user_permissions": _int_or_original(row.get("ignore_user_permissions")),
        "permlevel": _int_or_original(row.get("permlevel")),
        "hidden": _int_or_original(row.get("hidden")),
        "reqd": _int_or_original(row.get("reqd")),
        "read_only": _int_or_original(row.get("read_only")),
        "is_virtual": _int_or_original(row.get("is_virtual")),
    }


def _validate_stock_metadata(reader, doctype, fields):
    _assert_doctype_stock_identity(reader, doctype, istable=1 if doctype == "Project User" else 0)
    try:
        rules.validate_stock_field_projection(doctype, fields)
    except rules.RuleViolation as exc:
        raise UnsupportedProfile(str(exc.message)) from exc
    index = {field["fieldname"]: field for field in fields}
    if doctype == "Project":
        for name, target in rules.PROJECT_LINK_TARGETS.items():
            field = index.get(name)
            if not field or field.get("fieldtype") != "Link" or field.get("options") != target:
                raise UnsupportedProfile(f"Stock Project Link {name} is missing or altered.")
            _assert_custom_link_storage(reader, doctype, name)
        users = index.get("users")
        if (
            not users
            or users.get("fieldtype") != "Table"
            or users.get("options") != "Project User"
            or users.get("permlevel") != 1
        ):
            raise UnsupportedProfile("The stock Project User table is missing or altered.")
        forbidden = rules.FORBIDDEN_CUSTOM_FIELDTYPES - {"Table"}
        for field in fields:
            fieldtype = field.get("fieldtype")
            if fieldtype == "Table":
                # The sole supported table is the validated stock ``users``
                # child table above; any other table is an unsupported extension.
                if field.get("fieldname") != "users":
                    raise UnsupportedProfile("An additional Project child table is unsupported.")
                continue
            if fieldtype in forbidden:
                raise UnsupportedProfile("A forbidden field type is present on Project.")
    else:
        user = index.get("user")
        if not user or user.get("fieldtype") != "Link" or user.get("options") != "User":
            raise UnsupportedProfile("The stock Project User Link is missing or altered.")
        _assert_custom_link_storage(reader, doctype, "user")
        for field in fields:
            if field.get("fieldtype") in rules.FORBIDDEN_CUSTOM_FIELDTYPES:
                raise UnsupportedProfile("A forbidden field type is present on Project User.")
    for field in fields:
        if not rules.validate_field_flags(field):
            raise UnsupportedProfile("A stock or custom field carries untyped flags.")


def _read_permissions(reader, doctype):
    custom = reader.query(
        "SELECT role, permlevel, `read`, `write`, `create`, `delete`, `submit`, `cancel`, `amend`, "
        "`report`, `export`, `print`, `email`, `share`, `select`, `import`, `if_owner` "
        "FROM `tabCustom DocPerm` WHERE parent=%s ORDER BY idx",
        (doctype,),
    )
    if custom:
        return _validate_permission_rows(custom), True
    stock = reader.query(
        "SELECT role, permlevel, `read`, `write`, `create`, `delete`, `submit`, `cancel`, `amend`, "
        "`report`, `export`, `print`, `email`, `share`, `select`, `import`, `if_owner` "
        "FROM `tabDocPerm` WHERE parent=%s ORDER BY idx",
        (doctype,),
    )
    return _validate_permission_rows(stock), False


def _tree_meta(reader, doctype):
    row = reader.one(
        "SELECT name, module, istable, issingle, is_tree, is_virtual, nsm_parent_field "
        "FROM tabDocType WHERE name=%s",
        (doctype,),
    )
    if not row:
        return None
    return row


def _assert_doctype_stock_identity(reader, doctype, *, istable):
    meta = _tree_meta(reader, doctype)
    if not meta:
        raise UnsupportedProfile(f"The {doctype} DocType metadata is unavailable.")
    if int(meta.get("istable") or 0) != int(istable):
        raise UnsupportedProfile(f"The {doctype} DocType child identity is altered.")
    if int(meta.get("issingle") or 0) != 0 or int(meta.get("is_tree") or 0) != 0:
        raise UnsupportedProfile(f"The {doctype} DocType is not an ordinary persisted DocType.")
    if int(meta.get("is_virtual") or 0) != 0:
        raise UnsupportedProfile(f"The {doctype} DocType is virtual or computed.")
    if meta.get("module") not in ("Projects", "Project"):
        raise UnsupportedProfile(f"The {doctype} DocType does not belong to the stock Projects module.")


def _expand_nested_set(reader, doctype, value):
    if not IDENTIFIER_RE.match(doctype or ""):
        raise UnsupportedProfile("Unsupported descendant DocType name.")
    meta = _tree_meta(reader, doctype)
    if not meta or not int(meta.get("is_tree") or 0):
        return [value]
    table = f"`tab{doctype}`"
    bounds = reader.one(
        f"SELECT lft, rgt FROM {table} WHERE name=%s",
        (value,),
    )
    if not bounds:
        raise AccessDenied("User Permission target is unavailable.")
    rows = reader.query(
        f"SELECT name FROM {table} WHERE lft > %s AND rgt < %s LIMIT %s",
        (bounds["lft"], bounds["rgt"], MAX_DESCENDANT_ROWS + 1),
    )
    if len(rows) > MAX_DESCENDANT_ROWS:
        raise UnsupportedProfile("User Permission descendant expansion exceeded its bound.")
    return [value] + [row["name"] for row in rows]


def _read_user_permissions(reader, user):
    rows = reader.query(
        "SELECT allow, for_value, applicable_for, is_default, hide_descendants "
        "FROM `tabUser Permission` WHERE user=%s ORDER BY name",
        (user,),
    )
    result = {}
    for row in rows:
        allow = row.get("allow")
        if not allow:
            continue
        if allow not in rules.SUPPORTED_USER_PERMISSION_TARGETS:
            raise UnsupportedProfile("A User Permission target is outside the supported profile.")
        values = [row.get("for_value")]
        if not int(row.get("hide_descendants") or 0):
            values = _expand_nested_set(reader, allow, row.get("for_value"))
        bucket = result.setdefault(allow, [])
        for index, doc in enumerate(values):
            bucket.append(
                {
                    "doc": doc,
                    "applicable_for": row.get("applicable_for"),
                    "is_default": int(row.get("is_default") or 0) if index == 0 else 0,
                    "hide_descendants": int(row.get("hide_descendants") or 0) if index == 0 else 0,
                }
            )
    return result


def _link_fields(fields):
    return [
        field
        for field in fields
        if field.get("fieldtype") == "Link" and field.get("fieldname") and field.get("options")
    ]


def _read_child_rows(reader, project, child_doctype):
    if not IDENTIFIER_RE.match(child_doctype or ""):
        raise UnsupportedProfile("Unsupported child DocType name.")
    meta = _tree_meta(reader, child_doctype)
    if not meta or not int(meta.get("istable") or 0):
        raise UnsupportedProfile("Project child metadata is unavailable.")
    fields = _read_fields(reader, child_doctype)
    inconsistent = reader.one(
        f"SELECT COUNT(*) AS total FROM `tab{child_doctype}` "
        "WHERE parent=%s AND (parenttype IS NULL OR parentfield IS NULL "
        "OR parenttype<>'Project' OR parentfield<>'users')",
        (project,),
    )
    if inconsistent and int(inconsistent.get("total") or 0):
        raise IntegrityFailure("An inconsistently attached Project User row was found.")
    rows = reader.query(
        f"SELECT * FROM `tab{child_doctype}` "
        "WHERE parent=%s AND parenttype='Project' AND parentfield='users' ORDER BY idx",
        (project,),
    )
    links = _link_fields(fields)
    for row in rows:
        row["_link_fields"] = links
    return rows, links


def _share_allowed(reader, project, user, ptype):
    if ptype not in ("read", "write", "share", "submit", "email", "print"):
        return False
    right = "read" if ptype in ("email", "print") else ptype
    rows = reader.query(
        "SELECT `user`, everyone, `read`, `write`, `share` FROM `tabDocShare` "
        "WHERE share_doctype='Project' AND share_name=%s",
        (project,),
    )
    for row in rows:
        if not rules.share_grants(row_user=row.get("user"), everyone=row.get("everyone"), actor=user):
            continue
        if int(row.get(right) or 0) == 1:
            return True
    return False


def _assert_no_protected_shares(reader):
    rows = reader.query(
        "SELECT COUNT(*) AS total FROM `tabDocShare` WHERE share_doctype IN (%s, %s)",
        rules.PROTECTED_DOCTYPES,
    )
    if rows and int(rows[0].get("total") or 0):
        raise IntegrityFailure("Protected DocType shares already exist.")


def _cost_center_subtree_contains(reader, root_cost_center, project_cost_center):
    if not root_cost_center or not project_cost_center:
        return True
    if root_cost_center == project_cost_center:
        return True
    root = reader.one("SELECT lft, rgt FROM `tabCost Center` WHERE name=%s", (root_cost_center,))
    target = reader.one("SELECT lft, rgt FROM `tabCost Center` WHERE name=%s", (project_cost_center,))
    if not root or not target:
        raise AccessDenied("Cost Center hierarchy is unavailable.")
    return root["lft"] < target["lft"] and target["rgt"] < root["rgt"]


def _organizational_allowed(reader, actor, project_row, user_permissions):
    settings = _settings(reader, "Construction Settings", ("enable_scope_context",))
    try:
        enabled = rules.parse_scope_enabled(settings.get("enable_scope_context"))
    except rules.RuleViolation as exc:
        raise AccessDenied(str(exc.message)) from exc
    if not enabled:
        return True, None
    scope = reader.one(
        "SELECT company, project, cost_center FROM `tabUser Scope Context` WHERE user=%s",
        (actor,),
    )
    subtree = True
    if scope and scope.get("cost_center") and project_row.get("cost_center"):
        subtree = _cost_center_subtree_contains(
            reader, scope.get("cost_center"), project_row.get("cost_center")
        )
    allowed = rules.organizational_allows(
        scope_enabled=True,
        scope=dict(scope) if scope else None,
        project=project_row.get("name"),
        project_company=project_row.get("company"),
        project_cost_center=project_row.get("cost_center"),
        cost_center_in_scope_subtree=subtree,
    )
    return allowed, dict(scope) if scope else None


def _project_company_consistent(reader, project_row):
    cost_center = project_row.get("cost_center")
    if not cost_center:
        return
    row = reader.one("SELECT company FROM `tabCost Center` WHERE name=%s", (cost_center,))
    if not row:
        raise IntegrityFailure("The Project Cost Center is missing.")
    company = project_row.get("company")
    if company and row.get("company") and row.get("company") != company:
        raise IntegrityFailure("The Project Cost Center belongs to a different Company.")


def _project_link_values(project_row, fields):
    values = {}
    for field in _link_fields(fields):
        values[field["fieldname"]] = project_row.get(field["fieldname"])
    values["name"] = project_row.get("name")
    return values


def _evaluate(reader, project, operation):
    actor = frappe.session.user
    if not actor or actor == "Guest":
        raise AccessDenied("Authentication is required.")

    # Deployment-profile integrity and protected-share checks run for every
    # actor, including the literal Administrator. The native role/permission
    # bypass granted to Administrator does not bypass these invariants.
    profile = _assert_supported_profile(reader)
    _assert_no_protected_shares(reader)

    if actor == "Administrator":
        project_row = _read_project(reader, project)
        _project_company_consistent(reader, project_row)
        _recheck_profile(profile)
        reader.verify_storage_engines()
        actions = {name: True for name in rules.OPERATIONS}
        return {
            "allowed": True,
            "reason": "administrator",
            "project": project_row.get("name"),
            "company": project_row.get("company"),
            "cost_center": project_row.get("cost_center"),
            "actions": actions,
            "scope": None,
        }

    user_row = _read_user(reader, actor)
    roles = _read_roles(reader, actor, user_row.get("user_type"))
    project_row = _read_project(reader, project)
    _project_company_consistent(reader, project_row)
    _read_fields(reader, "Project User")

    fields = _read_fields(reader, "Project")
    permissions, custom = _read_permissions(reader, "Project")
    user_permissions = _read_user_permissions(reader, actor)
    settings = _settings(
        reader,
        "System Settings",
        ("apply_strict_user_permissions", "disable_document_sharing"),
    )
    try:
        strict = rules.parse_required_binary_setting(
            settings.get("apply_strict_user_permissions"), field="apply_strict_user_permissions"
        )
        rules.parse_required_binary_setting(
            settings.get("disable_document_sharing"), field="disable_document_sharing"
        )
    except rules.RuleViolation as exc:
        raise UnsupportedProfile(str(exc.message)) from exc
    child_rows, _child_links = _read_child_rows(reader, project, "Project User")
    doc_values = _project_link_values(project_row, fields)
    is_owner = (project_row.get("owner") or "").lower() == actor.lower()
    user_allowed = rules.user_permission_allows(
        doctype="Project",
        docname=project_row.get("name"),
        doc_values=doc_values,
        link_fields=_link_fields(fields),
        user_permissions=user_permissions,
        strict=strict,
        child_rows=child_rows,
    )

    native = {}
    for ptype in ("read", "write"):
        native[ptype] = rules.evaluate_native_document_permission(
            permissions=permissions,
            roles=roles,
            is_owner=is_owner,
            ptype=ptype,
            user_permission_allowed=user_allowed,
            share_allowed=_share_allowed(reader, project_row.get("name"), actor, ptype),
            controller_denied=False,
        )

    organizational, scope = _organizational_allowed(reader, actor, project_row, user_permissions)
    actions = {}
    for name in rules.OPERATIONS:
        actions[name] = rules.decide_operation_access(
            operation=name,
            roles=roles,
            native_read=native["read"]["allowed"],
            native_write=native["write"]["allowed"],
            organizational_allowed=organizational,
        )["allowed"]

    decision = rules.decide_operation_access(
        operation=operation,
        roles=roles,
        native_read=native["read"]["allowed"],
        native_write=native["write"]["allowed"],
        organizational_allowed=organizational,
    )
    if not decision["allowed"]:
        raise AccessDenied("Not permitted.")
    _recheck_profile(profile)
    reader.verify_storage_engines()
    return {
        "allowed": True,
        "reason": decision["reason"],
        "project": project_row.get("name"),
        "company": project_row.get("company"),
        "cost_center": project_row.get("cost_center"),
        "actions": actions,
        "scope": scope,
        "custom_permissions": custom,
    }


def authorize(project, operation, payload_reader=None):
    """Authorize one operation and optionally read data in the same snapshot."""
    rules.validate_operation(operation)
    project = rules.validate_identifier(project, field="Project")
    try:
        with FreshAuthorityReader() as reader:
            decision = _evaluate(reader, project, operation)
            payload = payload_reader(reader) if payload_reader else None
            # Payload reads (for example the bounded tree) query additional
            # tables; prove transactional storage for those as well before
            # any result is returned.
            reader.verify_storage_engines()
    except (AccessDenied, UnsupportedProfile, IntegrityFailure):
        raise
    return decision, payload


def has_protected_permission(doc, ptype, user=None, **kwargs):
    guard = _GUARD.get()
    if guard is None:
        return False
    actor = user or frappe.session.user
    if actor != guard["actor"]:
        return False
    if doc.doctype != guard["doctype"]:
        return False
    if guard.get("document") is not None and doc is not guard["document"]:
        return False
    if guard["name"] and doc.get("name") and doc.get("name") != guard["name"]:
        return False
    if guard["project"] and doc.get("project") and doc.get("project") != guard["project"]:
        return False
    if doc.get("project") and not guard["project"]:
        return False
    permitted = _GUARD_PTYPES.get(guard["operation"], frozenset())
    if ptype not in permitted:
        return False
    if doc.doctype == rules.COUNTER_DOCTYPE and ptype not in ("read", "write", "create", "delete"):
        return False
    return True


def protected_query_conditions(user, doctype=None):
    return "1=0"


def reject_protected_share(doc, method=None):
    if doc.get("share_doctype") in rules.PROTECTED_DOCTYPES or doc.get("share_doctype") == rules.AUDIT_DOCTYPE:
        frappe.throw(
            frappe._("Sharing execution tree records is not permitted."),
            frappe.PermissionError,
        )


@contextlib.contextmanager
def establish_guard(
    *,
    actor,
    operation,
    project,
    doctype,
    document,
    name=None,
    company=None,
    code=None,
    from_value=None,
    to_value=None,
    targets=None,
):
    """Establish a private, request-local capability.

    The capability is bound to the exact document object (including an unsaved
    create object), its derived Company, an allocated code, an allowed field
    transition and, for counters, a monotonic transition.
    """

    if _GUARD.get() is not None:
        raise IntegrityFailure("Nested execution tree guards are not permitted.")
    if operation not in rules.OPERATIONS and operation != "counter":
        raise IntegrityFailure("Unknown guarded operation.")
    if document is None:
        raise IntegrityFailure("A capability requires its exact document object.")
    before = {}
    getter = getattr(document, "get", None)
    if callable(getter):
        for field in (
            "name",
            "project",
            "company",
            "ebs_code",
            "title",
            "parent_node",
            "is_group",
            "disabled",
            "last_issued",
        ):
            before[field] = getter(field)
    guard = {
        "actor": actor,
        "operation": operation,
        "project": project,
        "doctype": doctype,
        "document": document,
        "name": name,
        "company": company,
        "code": code,
        "from_value": from_value,
        "to_value": to_value,
        "targets": dict(targets or {}),
        "before": before,
    }
    token = _GUARD.set(guard)
    try:
        yield guard
    finally:
        _GUARD.reset(token)


def current_guard():
    guard = _GUARD.get()
    if not guard:
        return None
    return {key: value for key, value in guard.items() if key != "document"}


def current_operation():
    guard = _GUARD.get()
    return guard["operation"] if guard else None


def require_guard(doctype, operation, project, name=None, document=None):
    guard = _GUARD.get()
    if guard is None:
        raise frappe.PermissionError(frappe._("Not permitted."))
    if guard["actor"] != frappe.session.user:
        raise frappe.PermissionError(frappe._("Not permitted."))
    if guard["doctype"] != doctype or guard["operation"] != operation:
        raise frappe.PermissionError(frappe._("Not permitted."))
    if guard["project"] != project:
        raise frappe.PermissionError(frappe._("Not permitted."))
    if document is not None and guard["document"] is not document:
        # Only the deletion lifecycle reloads the document: ``frappe.delete_doc``
        # calls ``on_trash`` on a fresh object. Every other operation must use
        # the exact object the capability was bound to.
        if not (
            operation == "delete"
            and guard["operation"] == "delete"
            and guard["name"]
            and document.get("name") == guard["name"]
            and document.get("project") == guard["project"]
            and getattr(document, "doctype", None) == guard["doctype"]
        ):
            raise frappe.PermissionError(frappe._("Not permitted."))
    if guard["name"] and name and guard["name"] != name:
        raise frappe.PermissionError(frappe._("Not permitted."))
    return guard


def require_guard_transition(guard, *, document, field, value):
    """Enforce the closed field-transition set bound to the capability.

    A field explicitly listed in ``targets`` must equal its authorized value.
    Every other field must remain exactly at the value captured when the
    capability was created; an omitted but changed field is a borrowed
    transition and denies. Fields outside the captured inventory deny.
    """

    targets = guard.get("targets") or {}
    before = guard.get("before") or {}
    if field in targets:
        if targets[field] != value:
            raise frappe.PermissionError(frappe._("Not permitted."))
    elif field in before:
        if before[field] != value:
            raise frappe.PermissionError(frappe._("Not permitted."))
    else:
        raise frappe.PermissionError(frappe._("Not permitted."))
    if "company" in guard and guard.get("company") is not None:
        if _document_value(document, "company") != guard["company"]:
            raise frappe.PermissionError(frappe._("Not permitted."))
    if "code" in guard and guard.get("code") is not None:
        if _document_value(document, "ebs_code") != guard["code"]:
            raise frappe.PermissionError(frappe._("Not permitted."))


def _document_value(document, field):
    getter = getattr(document, "get", None)
    if callable(getter):
        return getter(field)
    return getattr(document, field, None)


def has_counter_guard(project, document=None):
    guard = _GUARD.get()
    return bool(
        guard
        and guard["doctype"] == rules.COUNTER_DOCTYPE
        and guard["operation"] == "counter"
        and guard["project"] == project
        and guard["actor"] == frappe.session.user
        and (document is None or guard.get("document") is document)
    )


def preflight_conflicts(reader=None):
    """Fail closed when incompatible installed objects already exist.

    This mirrors the installer preflight over the same tables so callers that
    hold a snapshot do not rely on a narrower inventory.
    """

    def _count(source, table, where, params):
        if not _table_present(source, table):
            return 0
        row = source.one(f"SELECT COUNT(*) AS total FROM `tab{table}` WHERE {where}", params)
        return int(row.get("total") or 0) if row else 0

    def _check_with(source):
        from construction.setup import execution_tree_schema as schema

        for doctype in rules.PROTECTED_DOCTYPES:
            rows = source.query(
                "SELECT name, module, custom, istable, issingle, is_tree, is_virtual "
                "FROM tabDocType WHERE name=%s",
                (doctype,),
            )
            if rows:
                if rows[0].get("module") != "construction":
                    raise IntegrityFailure(f"An unrelated {doctype} DocType already exists.")
                existing_fields = source.query(
                    "SELECT fieldname, fieldtype, options, permlevel, ignore_user_permissions, "
                    "hidden, reqd, read_only, is_virtual FROM `tabDocField` "
                    "WHERE parent=%s ORDER BY idx",
                    (doctype,),
                )
                try:
                    rules.validate_protected_definition(
                        doctype,
                        rows[0],
                        existing_fields,
                        schema.candidate_protected_definition(doctype),
                    )
                except rules.RuleViolation as exc:
                    raise IntegrityFailure(str(exc.message)) from exc
            if _count(source, "DocPerm", "parent=%s", (doctype,)):
                raise IntegrityFailure(f"Stock DocPerm rows already exist for {doctype}.")
            if _count(source, "Custom DocPerm", "parent=%s", (doctype,)):
                raise IntegrityFailure(f"Custom DocPerm already exists for {doctype}.")
            if _count(source, "DocShare", "share_doctype=%s", (doctype,)):
                raise IntegrityFailure(f"Shares already exist for {doctype}.")
            if _count(source, "Custom Field", "dt=%s", (doctype,)):
                raise IntegrityFailure(f"Custom Fields already exist for {doctype}.")
            if _count(source, "Property Setter", "doc_type=%s", (doctype,)):
                raise IntegrityFailure(f"Property Setters already exist for {doctype}.")
            if _count(
                source,
                "Workflow",
                "document_type=%s AND is_active=1",
                (doctype,),
            ):
                raise IntegrityFailure(f"An active Workflow already exists for {doctype}.")
        return True

    if reader is not None:
        result = _check_with(reader)
        reader.verify_storage_engines()
        return result
    with FreshAuthorityReader() as local:
        result = _check_with(local)
        local.verify_storage_engines()
        return result
