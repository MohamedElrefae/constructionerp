# P1 pinned framework source evidence

Prepared for the local Stage 1 architect and independent reviewer. These are exact selected lines from Git objects, with hashes of each full source blob. This packet is a plan input committed in the dedicated WBS review baseline. Native evidence is NOT RUN.

Source excerpts retain upstream attribution and licensing. Frappe and ERPNext source is identified below by its Git commit, path, line range and full-blob hash. Construction-specific excerpts are identified the same way. This source inventory pertains to the pinned app set. Confirm the target's installed hooks and metadata in the later disposable lab.

## Source identity

- frappe commit `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b`
- erpnext commit `7474d9e786277383de1242ab882f16856d17a9c9`

## frappe/permissions.py

Full blob SHA-256 `ae3c1285b87094fef39c27c4a5f73c258da11f955ce45169ca6b4996558f6bd8`

Lines 81–223

```python
def has_permission(
	doctype,
	ptype="read",
	doc=None,
	user=None,
	*,
	parent_doctype=None,
	print_logs=True,
	debug=False,
	ignore_share_permissions=False,
) -> bool:
	"""Return True if user has permission `ptype` for given `doctype`.
	If `doc` is passed, also check user, share and owner permissions.

	:param doctype: DocType to check permission for
	:param ptype: Permission Type to check
	:param doc: Check User Permissions for specified document.
	:param user: User to check permission for. Defaults to current user.
	:param print_logs: If True, will display a message using frappe.msgprint
	                which explains why the permission check failed.
	:param parent_doctype:
	        Required when checking permission for a child DocType (unless doc is specified)
	"""

	if not user:
		user = frappe.session.user

	if user == "Administrator":
		debug and _debug_log("Allowed everything because user is Administrator")
		return True

	if ptype == "share" and frappe.get_system_settings("disable_document_sharing"):
		debug and _debug_log("User can't share because sharing is disabled globally from system settings")
		return False

	if not doc and hasattr(doctype, "doctype"):
		# first argument can be doc or doctype
		doc = doctype
		doctype = doc.doctype

	if frappe.is_table(doctype):
		return has_child_permission(
			doctype,
			ptype,
			doc,
			user,
			parent_doctype,
			debug=debug,
			print_logs=print_logs,
		)

	meta = frappe.get_meta(doctype)

	# docname == doctype for single doctypes
	if not doc and meta.issingle:
		doc = meta.name

	if doc:
		if isinstance(doc, str | int):
			# perf: Avoid loading child tables for perm checks
			doc = frappe.get_lazy_doc(meta.name, doc)
		perm = get_doc_permissions(doc, user=user, ptype=ptype, debug=debug).get(ptype)
		if not perm:
			debug and _debug_log(
				"Permission check failed from role permission system. Check if user's role grant them permission to the document."
			)
			if not frappe.flags.get("has_permission_check_logs"):
				msg = _("User {0} does not have access to this document").format(frappe.bold(user))
				if meta.issingle:
					msg += f": {_(doc.doctype)}"
				elif has_permission(doc.doctype, print_logs=False):
					msg += f": {_(doc.doctype)} - {doc.name}"
				push_perm_check_log(msg, debug=debug)
	else:
		if ptype == "submit" and not cint(meta.is_submittable):
			push_perm_check_log(_("Document Type is not submittable"), debug=debug)
			return False

		if ptype == "import" and not cint(meta.allow_import):
			push_perm_check_log(_("Document Type is not importable"), debug=debug)
			return False

		role_permissions = get_role_permissions(meta, user=user, debug=debug)
		debug and _debug_log(
			"User has following permissions using role permission system: "
			+ frappe.as_json(role_permissions, indent=8)
		)

		perm = role_permissions.get(ptype)

		if not perm:
			push_perm_check_log(
				_("User {0} does not have doctype access via role permission for document {1}").format(
					frappe.bold(user), frappe.bold(_(doctype))
				),
				debug=debug,
			)

	def false_if_not_shared():
		share_rights = ["read", "write", "share", "submit", "email", "print"]
		custom_rights = get_doctype_ptype_map().get(doctype, [])

		if ptype not in share_rights + custom_rights:
			debug and _debug_log(f"Permission type {ptype} can not be shared")
			return False

		rights = ["read" if ptype in ("email", "print") else ptype]

		if doc:
			doc_name = get_doc_name(doc)
			shared = frappe.share.get_shared(
				doctype,
				user,
				rights=rights,
				filters=[["share_name", "=", doc_name]],
				limit=1,
			)
			debug and _debug_log(f"Document is shared with user for {ptype}? {bool(shared)}")
			return bool(shared)

		elif frappe.share.get_shared(doctype, user, rights=rights, limit=1):
			# if atleast one shared doc of that type, then return True
			# this is used in db_query to check if permission on DocType
			debug and _debug_log(f"At least one document is shared with user with perm: {rights}")
			return True

		return False

	if not perm and not ignore_share_permissions:
		debug and _debug_log("Checking if document/doctype is explicitly shared with user")
		perm = false_if_not_shared()

	# select permission is implied by read permission
	if not perm and ptype == "select":
		perm = has_permission(
			doctype,
			ptype="read",
			doc=doc,
			user=user,
			parent_doctype=parent_doctype,
			print_logs=print_logs,
			debug=debug,
			ignore_share_permissions=ignore_share_permissions,
```

Lines 229–344

```python
def get_doc_permissions(doc, user=None, ptype=None, debug=False):
	"""Return a dict of evaluated permissions for given `doc` like `{"read":1, "write":1}`"""
	if not user:
		user = frappe.session.user

	meta = frappe.get_meta(doc.doctype)

	def is_user_owner():
		return (doc.get("owner") or "").lower() == user.lower()

	if not has_controller_permissions(doc, ptype, user=user, debug=debug):
		push_perm_check_log(_("Not allowed via controller permission check"), debug=debug)
		return {ptype: 0}

	permissions = copy.deepcopy(get_role_permissions(meta, user=user, is_owner=is_user_owner(), debug=debug))

	debug and _debug_log(
		"User has following permissions using role permission system: "
		+ frappe.as_json(permissions, indent=8)
	)

	if not cint(meta.is_submittable):
		permissions["submit"] = 0

	if not cint(meta.allow_import):
		permissions["import"] = 0

	# Override with `if_owner` perms irrespective of user
	if permissions.get("has_if_owner_enabled"):
		# apply owner permissions on top of existing permissions
		# some access might be only for the owner
		# eg. everyone might have read access but only owner can delete
		permissions.update(permissions.get("if_owner", {}))
		debug and _debug_log(
			"User is owner of document, so permissions are updated to: " + frappe.as_json(permissions)
		)

	if not has_user_permission(doc, user, debug=debug, ptype=ptype):
		if is_user_owner():
			# replace with owner permissions
			permissions = permissions.get("if_owner", {})
			# if_owner does not come with create rights...
			permissions["create"] = 0
			debug and _debug_log("User has only 'If owner' permissions because of User Permissions")
		else:
			debug and _debug_log("User has no permissions because of User Permissions")
			permissions = {}

	debug and _debug_log(
		"Final applicable permissions after evaluating user permissions: "
		+ frappe.as_json(permissions, indent=8)
	)
	return permissions


def get_role_permissions(doctype_meta, user=None, is_owner=None, debug=False):
	"""
	Return dict of evaluated role permissions like:
	        {
	                "read": 1,
	                "write": 0,
	                // if "if_owner" is enabled
	                "if_owner":
	                        {
	                                "read": 1,
	                                "write": 0
	                        }
	        }
	"""
	if isinstance(doctype_meta, str):
		doctype_meta = frappe.get_meta(doctype_meta)  # assuming doctype name was passed

	if not user:
		user = frappe.session.user

	cache_key = (doctype_meta.name, user, bool(is_owner))

	if user == "Administrator":
		debug and _debug_log("all permissions granted because user is Administrator")
		return allow_everything(doctype_meta.name)

	if not frappe.local.role_permissions.get(cache_key) or debug:
		perms = frappe._dict(if_owner={})

		roles = frappe.get_roles(user)
		debug and _debug_log("User has following roles: " + str(roles))

		def is_perm_applicable(perm):
			return perm.role in roles and cint(perm.permlevel) == 0

		def has_permission_without_if_owner_enabled(ptype):
			return any(p.get(ptype, 0) and not p.get("if_owner", 0) for p in applicable_permissions)

		applicable_permissions = list(filter(is_perm_applicable, getattr(doctype_meta, "permissions", [])))
		has_if_owner_enabled = any(p.get("if_owner", 0) for p in applicable_permissions)
		perms["has_if_owner_enabled"] = has_if_owner_enabled

		for ptype in get_rights(doctype_meta.name):
			pvalue = any(p.get(ptype, 0) for p in applicable_permissions)
			# check if any perm object allows perm type
			perms[ptype] = cint(pvalue)
			if (
				pvalue
				and has_if_owner_enabled
				and not has_permission_without_if_owner_enabled(ptype)
				and ptype != "create"
			):
				perms["if_owner"][ptype] = cint(pvalue and is_owner)
				# has no access if not owner
				# only provide select or read access so that user is able to at-least access list
				# (and the documents will be filtered based on owner sin further checks)
				perms[ptype] = 1 if ptype in ("select", "read") else 0

		frappe.local.role_permissions[cache_key] = perms

	return frappe.local.role_permissions[cache_key]
```

Lines 353–489

```python
def has_user_permission(doc, user=None, debug=False, *, ptype=None):
	"""Return True if User is allowed to view considering User Permissions."""
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	user_permissions = get_user_permissions(user)

	if not user_permissions:
		# no user permission rules specified for this doctype
		debug and _debug_log("User is not affected by any user permissions")
		return True

	doctype = doc.get("doctype")
	docname = doc.get("name")

	# don't apply strict user permissions for single doctypes since they contain empty link fields
	apply_strict_user_permissions = (
		False if doc.meta.issingle else frappe.get_system_settings("apply_strict_user_permissions")
	)
	if apply_strict_user_permissions:
		debug and _debug_log("Strict user permissions will be applied")

	if (
		apply_strict_user_permissions
		and doc.get("__islocal")
		and ptype in ("read", "write")
		and (not docname or (docname and not frappe.db.exists(doctype, docname, cache=True)))
	):
		apply_strict_user_permissions = False
		debug and _debug_log("Strict permissions will be skipped on local document")

	# STEP 1: ---------------------
	# check user permissions on self
	if doctype in user_permissions:
		doctype_up = user_permissions.get(doctype, [])
		allowed_docs = get_allowed_docs_for_doctype(doctype_up, doctype)

		# if allowed_docs is empty it states that there is no applicable permission under the current doctype

		# only check if allowed_docs is not empty
		if allowed_docs:
			not_permitted = True
			if doc.meta.is_tree and ptype == "create":
				if parent := doc.get(doc.nsm_parent_field):
					doc_hide_descendants = {d.doc: d.hide_descendants for d in doctype_up}
					for d in _get_parent_and_ancestors(doctype, parent):
						if d in allowed_docs and not doc_hide_descendants[d]:
							not_permitted = False
							break
			else:
				not_permitted = not docname or str(docname) not in allowed_docs

			if not_permitted:
				# no user permissions for this doc specified
				debug and _debug_log(
					"User doesn't have access to this document because of User Permissions, allowed documents: "
					+ str(allowed_docs)
				)
				push_perm_check_log(_("Not allowed for {0}: {1}").format(_(doctype), docname), debug=debug)
				return False

		debug and _debug_log(f"User Has access to {docname} via User Permissions.")

	# STEP 2: ---------------------------------
	# check user permissions in all link fields

	def check_user_permission_on_link_fields(d):
		# check user permissions for all the link fields of the given
		# document object d
		#
		# called for both parent and child records

		meta = frappe.get_meta(d.doctype)

		# check all link fields for user permissions
		for field in meta.get_link_fields():
			if field.ignore_user_permissions:
				continue

			# empty value, do you still want to apply user permissions?
			if not d.get(field.fieldname) and not apply_strict_user_permissions:
				continue

			if field.options not in user_permissions:
				continue

			# get the list of all allowed values for this link
			allowed_docs = get_allowed_docs_for_doctype(user_permissions.get(field.options, []), doctype)

			if allowed_docs and str(d.get(field.fieldname)) not in allowed_docs:
				# restricted for this link field, and no matching values found
				# make the right message and exit
				if d.get("parentfield"):
					# "You are not allowed to access this Employee record because it is linked
					# to Company 'Restricted Company' in row 3, field Reference Type"
					msg = _(
						"You are not allowed to access this {0} record because it is linked to {1} '{2}' in row {3}, field {4}"
					).format(
						_(meta.name),
						_(field.options),
						d.get(field.fieldname) or _("empty"),
						d.idx,
						_(field.label, context=field.parent) if field.label else field.fieldname,
					)
				else:
					# "You are not allowed to access Company 'Restricted Company' in field Reference Type"
					msg = _(
						"You are not allowed to access this {0} record because it is linked to {1} '{2}' in field {3}"
					).format(
						_(meta.name),
						_(field.options),
						d.get(field.fieldname) or _("empty"),
						_(field.label, context=field.parent) if field.label else field.fieldname,
					)

				push_perm_check_log(msg, debug=debug)

				return False

		return True

	if not check_user_permission_on_link_fields(doc):
		return False

	for d in doc.get_all_children(include_computed=True):
		if not check_user_permission_on_link_fields(d):
			return False

	return True


def has_controller_permissions(doc, ptype, user=None, debug=False) -> bool:
	"""Return controller permissions if denied, True if not defined.

	Controllers can only deny permission, they can not explicitly grant any permission that wasn't
	already present."""
	if not user:
		user = frappe.session.user
```

Lines 491–506

```python
	hooks = frappe.get_hooks("has_permission")
	methods = hooks.get(doc.doctype, []) + hooks.get("*", [])

	for method in reversed(methods):
		controller_permission = frappe.call(method, doc=doc, ptype=ptype, user=user, debug=debug)
		debug and _debug_log(f"Controller permission check from {method}: {controller_permission}")
		if not controller_permission:
			return bool(controller_permission)

	return True


def get_doctypes_with_read(user: str | None = None):
	return list({cstr(p.parent) for p in get_valid_perms(user=user) if p.parent and p.read})


```

Lines 542–577

```python
def get_roles(user=None, with_standard=True):
	"""get roles of current user"""
	if not user:
		user = frappe.session.user

	if user == "Guest" or not user:
		return [GUEST_ROLE]

	def get():
		if user == "Administrator":
			return frappe.get_all("Role", pluck="name")  # return all available roles
		else:
			table = DocType("Has Role")
			roles = (
				frappe.qb.from_(table)
				.where(
					(table.parenttype == "User")
					& (table.parent == user)
					& (table.role.notin(AUTOMATIC_ROLES))
				)
				.select(table.role)
				.run(pluck=True)
			)
			roles += [ALL_USER_ROLE, GUEST_ROLE]
			if is_system_user(user):
				roles.append(SYSTEM_USER_ROLE)
			return roles

	roles = frappe.cache.hget("roles", user, get)

	# filter standard if required
	if not with_standard:
		roles = [r for r in roles if r not in AUTOMATIC_ROLES]

	return roles

```

Lines 790–806

```python
def get_allowed_docs_for_doctype(user_permissions, doctype):
	"""Return all the docs from the passed `user_permissions` that are allowed under provided doctype."""
	return filter_allowed_docs_for_doctype(user_permissions, doctype, with_default_doc=False)


def filter_allowed_docs_for_doctype(user_permissions, doctype, with_default_doc=True):
	"""Return all the docs from the passed `user_permissions` that are
	allowed under provided doctype along with default doc value if `with_default_doc` is set."""
	allowed_doc = []
	default_doc = None
	for doc in user_permissions:
		if not doc.get("applicable_for") or doc.get("applicable_for") == doctype:
			allowed_doc.append(doc.get("doc"))
			if doc.get("is_default") or (len(user_permissions) == 1 and with_default_doc):
				default_doc = doc.get("doc")

	return (allowed_doc, default_doc) if with_default_doc else allowed_doc
```

## frappe/share.py

Full blob SHA-256 `8dce30fbd4eb512d000ea884a504b47485ff6f99bbf88e9f7684a68241234c44`

Lines 170–204

```python
def get_shared(doctype, user=None, rights=None, *, filters=None, limit=None):
	"""Get list of shared document names for given user and DocType.

	:param doctype: DocType of which shared names are queried.
	:param user: User for which shared names are queried.
	:param rights: List of rights for which the document is shared. List of `read`, `write`, `share`"""

	if not user:
		user = frappe.session.user

	if not rights:
		rights = ["read"]

	share_filters = [[right, "=", 1] for right in rights]
	share_filters += [["share_doctype", "=", doctype]]
	if filters:
		share_filters += filters

	or_filters = [["user", "=", user]]
	if user != "Guest":
		or_filters += [["everyone", "=", 1]]

	shared_docs = frappe.get_all(
		"DocShare",
		fields=["share_name"],
		filters=share_filters,
		or_filters=or_filters,
		order_by=None,
		limit_page_length=limit,
	)

	return [doc.share_name for doc in shared_docs]


def get_shared_doctypes(user=None):
```

## frappe/model/meta.py

Full blob SHA-256 `69ef491ea40574622ccd1030d7a5928942701ac18bbd51c85ded1cbc8397994c`

Lines 72–91

```python
def get_meta(doctype: "str | DocType", cached: bool = True) -> "_Meta":
	"""Get metadata for a doctype.

	Args:
	    doctype: The doctype as a string object.
	    cached: Whether to use cached metadata (default: True).

	Returns:
	    Meta object for the given doctype.
	"""
	if (
		cached
		and isinstance(doctype, str)
		and (meta := frappe.client_cache.get_value(f"doctype_meta::{doctype}"))
	):
		return meta

	meta = Meta(doctype)

	key = f"doctype_meta::{meta.name}"
```

Lines 166–184

```python
	def process(self):
		# don't process for special doctypes
		# prevents circular dependency
		if self.name in self.special_doctypes:
			if self.name == "DocPerm":
				self.add_custom_fields()
			self.init_field_caches()
			return

		self.add_custom_fields()
		self.apply_property_setters()
		self.init_field_caches()
		self.sort_fields()
		self.get_valid_columns()
		self.set_custom_permissions()
		self.add_custom_links_and_actions()
		self.check_if_large_table()

	def as_dict(self, no_nulls=False):
```

Lines 410–450

```python
	def add_custom_fields(self):
		if not frappe.db.table_exists("Custom Field"):
			return

		custom_fields = frappe.db.get_values(
			"Custom Field",
			filters={"dt": self.name},
			fieldname="*",
			as_dict=True,
			order_by="idx",
			update={"is_custom_field": 1},
		)

		if not custom_fields:
			return

		self.extend("fields", custom_fields)

	def apply_property_setters(self):
		if not frappe.db.table_exists("Property Setter"):
			return

		property_setters = frappe.db.get_values(
			"Property Setter",
			filters={"doc_type": self.name},
			fieldname="*",
			as_dict=True,
		)

		if not property_setters:
			return

		for ps in property_setters:
			if ps.doctype_or_field == "DocType":
				self.set(ps.property, cast(ps.property_type, ps.value))

			elif ps.doctype_or_field == "DocField":
				for d in self.fields:
					if d.fieldname == ps.field_name:
						d.set(ps.property, cast(ps.property_type, ps.value))
						break
```

Lines 640–654

```python
	def set_custom_permissions(self):
		"""Reset `permissions` with Custom DocPerm if exists"""
		if frappe.flags.in_patch or frappe.flags.in_install:
			return

		if not self.istable and self.name not in ("DocType", "DocField", "DocPerm", "Custom DocPerm"):
			custom_perms = frappe.get_all(
				"Custom DocPerm",
				fields="*",
				filters=dict(parent=self.name),
				update=dict(doctype="Custom DocPerm"),
			)
			if custom_perms:
				self.permissions = [Document(d) for d in custom_perms]

```

## frappe/core/doctype/user_permission/user_permission.py

Full blob SHA-256 `79331ad9c35f82701975111eaad8dd572a31d6039876509f6b200b0c0cdf610d`

Lines 34–46

```python
	def validate(self):
		self.validate_user_permission()
		self.validate_default_permission()

	def on_update(self):
		frappe.cache.hdel("user_permissions", self.user)
		frappe.publish_realtime("update_user_permissions", user=self.user, after_commit=True)

	def on_trash(self):
		frappe.cache.hdel("user_permissions", self.user)
		frappe.publish_realtime("update_user_permissions", user=self.user, after_commit=True)

	def validate_user_permission(self):
```

Lines 95–149

```python
def get_user_permissions(user: str | None = None):
	"""Get all users permissions for the user as a dict of doctype"""
	if not user:
		user = frappe.session.user

	if not user or user in ("Administrator", "Guest"):
		return {}

	cached_user_permissions = frappe.cache.hget("user_permissions", user)

	if cached_user_permissions is not None:
		return cached_user_permissions

	out = {}

	def add_doc_to_perm(perm, doc_name, is_default, hide_descendants):
		# group rules for each type
		# for example if allow is "Customer", then build all allowed customers
		# in a list
		if not out.get(perm.allow):
			out[perm.allow] = []

		out[perm.allow].append(
			frappe._dict(
				{
					"doc": doc_name,
					"applicable_for": perm.get("applicable_for"),
					"is_default": is_default,
					"hide_descendants": hide_descendants,
				}
			)
		)

	try:
		for perm in frappe.get_all(
			"User Permission",
			fields=["allow", "for_value", "applicable_for", "is_default", "hide_descendants"],
			filters=dict(user=user),
		):
			meta = frappe.get_meta(perm.allow)
			add_doc_to_perm(perm, perm.for_value, perm.is_default, perm.hide_descendants)

			if meta.is_nested_set() and not perm.hide_descendants:
				decendants = frappe.db.get_descendants(perm.allow, perm.for_value)
				for doc in decendants:
					add_doc_to_perm(perm, doc, False, False)

		out = frappe._dict(out)
		frappe.cache.hset("user_permissions", user, out)
	except frappe.db.SQLError as e:
		if frappe.db.is_table_missing(e):
			# called from patch
			pass

	return out
```

## frappe/database/database.py

Full blob SHA-256 `dc9fe0620ab7ceb300bee2b5da5c247d8979727139c785bb591e0a54e3bebf15`

Lines 1171–1177

```python
	def begin(self, *, read_only=False):
		read_only = read_only or frappe.flags.read_only
		mode = "READ ONLY" if read_only else ""
		self.sql(f"START TRANSACTION {mode}")

	def commit(self, *, chain=False):
		"""Commit current transaction. Calls SQL `COMMIT`."""
```

Lines 1196–1218

```python
	def rollback(self, *, save_point=None, chain=False):
		"""`ROLLBACK` current transaction. Optionally rollback to a known save_point."""
		if save_point:
			self.sql(f"rollback to savepoint {save_point}")
			self.value_cache.clear()
		elif not self._disable_transaction_control:
			self.before_commit.reset()
			self.after_commit.reset()

			self.before_rollback.run()

			if chain:
				self.sql("rollback and chain")
				self.value_cache.clear()
			else:
				self.sql("rollback")
				self.begin()

			self.value_cache.clear()
			self.after_rollback.run()
		else:
			warnings.warn(message=TRANSACTION_DISABLED_MSG, stacklevel=2)

```

## frappe/database/mariadb/mysqlclient.py

Full blob SHA-256 `22c991d033bf4b1d5174cd9c0879a659eafa49960ecd94d19a84e1dd99cb3b53`

Lines 109–151

```python


class MariaDBConnectionUtil:
	def get_connection(self):
		conn = self._get_connection()
		conn.auto_reconnect = True
		return conn

	def _get_connection(self) -> "MySQLdb.Connection":
		return self.create_connection()

	def create_connection(self):
		return MySQLdb.connect(**self.get_connection_settings())

	def set_execution_timeout(self, seconds: int):
		self.sql("set session max_statement_time = %s", int(seconds))

	def get_connection_settings(self) -> dict:
		conn_settings = {
			"user": self.user,
			"conv": self.CONVERSION_MAP,
			"charset": "utf8mb4",
			"use_unicode": True,
			"local_infile": False,
			"multi_statements": False,
		}

		if self.cur_db_name:
			conn_settings["database"] = self.cur_db_name

		if self.socket:
			conn_settings["unix_socket"] = self.socket
		else:
			conn_settings["host"] = self.host
			if self.port:
				conn_settings["port"] = int(self.port)

		if self.password:
			conn_settings["password"] = self.password

		# Configure SSL settings
		if frappe.conf.db_ssl_ca:
			ssl_config = {
```

## frappe/model/rename_doc.py

Full blob SHA-256 `b000bc9ebc7d49c1b50568ff0fe88ff3a4d177c5a974ea69a35eb1c2babf8a49`

Lines 146–188

```python
	merge = sbool(merge)
	meta = frappe.get_meta(doctype)

	if meta.naming_rule == "Autoincrement":
		old = cint(old)
		new = cint(new)

	if validate:
		old_doc = doc or frappe.get_doc(doctype, old)
		out = old_doc.run_method("before_rename", old, new, merge) or {}
		new = (out.get("new") or new) if isinstance(out, dict) else (out or new)
		new = validate_rename(
			doctype=doctype,
			old=old,
			new=new,
			meta=meta,
			merge=merge,
			force=force,
			ignore_permissions=ignore_permissions,
			ignore_if_exists=ignore_if_exists,
			old_doc=old_doc,
		)

	if not merge:
		rename_parent_and_child(doctype, old, new, meta)
	else:
		update_assignments(old, new, doctype)

	# update link fields' values
	link_fields = get_link_fields(doctype)
	update_link_field_values(link_fields, old, new, doctype)

	rename_dynamic_links(doctype, old, new)

	# save the user settings in the db
	update_user_settings(old, new, link_fields)

	if doctype == "DocType":
		rename_doctype(doctype, old, new)
		update_customizations(old, new)

	update_attachments(doctype, old, new)

```

Lines 418–452

```python
def update_link_field_values(link_fields: list[dict], old: str, new: str, doctype: str) -> None:
	for field in link_fields:
		if field["issingle"]:
			try:
				single_doc = frappe.get_doc(field["parent"])
				if single_doc.get(field["fieldname"]) == old:
					single_doc.set(field["fieldname"], new)
					# update single docs using ORM rather then query
					# as single docs also sometimes sets defaults!
					single_doc.flags.ignore_mandatory = True
					single_doc.flags.ignore_links = True
					single_doc.save(ignore_permissions=True)
			except ImportError:
				# fails in patches where the doctype has been renamed
				# or no longer exists
				pass
		else:
			parent = field["parent"]
			docfield = field["fieldname"]

			# Handles the case where one of the link fields belongs to
			# the DocType being renamed.
			# Here this field could have the current DocType as its value too.

			# In this case while updating link field value, the field's parent
			# or the current DocType table name hasn't been renamed yet,
			# so consider it's old name.
			if parent == new and doctype == "DocType":
				parent = old

			# when a document with autoincrement naming is renamed, the old and new values are int
			# but link field values are always stored as varchar, so casting the values to string
			frappe.db.set_value(parent, {docfield: cstr(old)}, docfield, cstr(new), update_modified=False)

		# update cached link_fields as per new
```

## frappe/model/document.py

Full blob SHA-256 `abf33ec888226c60b63b8f670e28ffb88d0371422413921a42ab4be4e35c6078`

Lines 576–600

```python

		self.flags.ignore_version = frappe.in_test if ignore_version is None else ignore_version

		if self.get("__islocal") or not self.get("name"):
			return self.insert()

		self.check_if_locked()
		self._set_defaults()
		self._restore_masked_fields_from_db()
		self.check_permission("write", "save")

		self.set_user_and_timestamp()
		self.set_docstatus()
		self.check_if_latest()
		self.set_parent_in_children()
		self.set_name_in_children()

		self.validate_higher_perm_levels()
		self._validate_links()
		self.run_before_save_methods()

		if self._action != "cancel":
			self._validate()

		if self._action == "update_after_submit":
```

Lines 1426–1440

```python
	def load_doc_before_save(self, *, raise_exception: bool = False):
		"""load existing document from db before saving"""

		self._doc_before_save = None

		if self.is_new():
			return

		try:
			self._doc_before_save = frappe.get_doc(self.doctype, self.name, for_update=True)
		except frappe.DoesNotExistError:
			if raise_exception:
				raise

			return frappe.clear_last_message()
```

## frappe/installer.py

Full blob SHA-256 `5c7694601658991c7abc0ea8f785f6138207dbf95d8bfa8ea72c6558113619a4`

Lines 350–378

```python
		frappe.setup_module_map(include_all_apps=True)

	sync_for(name, force=force, reset_permissions=True)

	if name == "frappe":
		# The framework's own rows can only be written after the sync, because a bare site has no
		# `tabModule Def` for them to go in, which is why the call above skips `frappe`.
		#
		# They used to arrive as a side effect of `make_module_and_roles`, which gives a module a
		# row when one of its doctypes is synced, so a module shipping no doctype got none. That
		# never mattered until the framework split its navigation, and a nav-only module carrying
		# a workspace and a sidebar now falls through it. The fixtures still import, since
		# `import_file` ignores links, but a module with no row does not exist as far as the site
		# is concerned: it is absent from every module list the desk builds, so the module is
		# missing from the dock on a fresh site and present on a migrated one.
		add_module_defs(name, ignore_if_duplicate=True)

	add_to_installed_apps(name)

	frappe.get_doc("Portal Settings", "Portal Settings").sync_menu()

	if set_as_patched:
		set_all_patches_as_completed(name)

	for after_install in app_hooks.after_install or []:
		frappe.get_attr(after_install)()

	for fn in frappe.get_hooks("after_app_install"):
		frappe.get_attr(fn)(name)
```

## erpnext/projects/doctype/project/project.py

Full blob SHA-256 `639fda6b7a25ab4b18b067bac65cf6d87705606fad2c0977ab296dd251022918`

Lines 89–121

```python

	def before_print(self, settings=None):
		self.onload()

	def validate(self):
		if not self.is_new():
			self.copy_from_template()
			self.control_access_for_project_users()
		self.send_welcome_email()
		self.update_costing()
		self.update_percent_complete()
		self.validate_from_to_dates("expected_start_date", "expected_end_date")
		self.validate_from_to_dates("actual_start_date", "actual_end_date")

	def copy_from_template(self):  # nosemgrep
		"""
		Copy tasks from template
		"""
		if self.project_template and not frappe.db.get_all("Task", dict(project=self.name), limit=1):
			# has a template, and no loaded tasks, so lets create
			if not self.expected_start_date:
				# project starts today
				self.expected_start_date = today()

			template = frappe.get_doc("Project Template", self.project_template)

			if not self.project_type:
				self.project_type = template.project_type

			# create tasks from template
			project_tasks = []
			tmp_task_details = []
			for task in template.tasks:
```

Lines 207–229

```python
		if self.sales_order:
			frappe.db.set_value("Sales Order", self.sales_order, "project", self.name)
		self.control_access_for_project_users()

	def on_trash(self):
		frappe.db.set_value("Sales Order", {"project": self.name}, "project", "")

	def update_percent_complete(self):
		if self.status == "Completed":
			if (
				len(frappe.get_all("Task", dict(project=self.name))) == 0
			):  # A project without tasks should be able to complete
				self.percent_complete_method = "Manual"
				self.percent_complete = 100

		if self.percent_complete_method == "Manual":
			if self.status == "Completed":
				self.percent_complete = 100
			elif flt(self.percent_complete) < 0 or flt(self.percent_complete) > 100:
				frappe.throw(_("% Complete must be between 0 and 100"))
			return

		total = frappe.db.count("Task", dict(project=self.name))
```

## erpnext/projects/doctype/project/project.json

Full blob SHA-256 `29aa376d3bc270c7885de02250d1fa73cfdcdcd7614c28eb9722a59fcded0f7b`

Lines 1–645

```json
{
 "actions": [],
 "allow_import": 1,
 "allow_rename": 1,
 "autoname": "naming_series:",
 "creation": "2013-03-07 11:55:07",
 "description": "A piece of work with tasks, time and costs.",
 "doctype": "DocType",
 "document_type": "Setup",
 "documentation": "https://docs.frappe.io/erpnext/user/manual/en/project",
 "engine": "InnoDB",
 "field_order": [
  "naming_series",
  "project_name",
  "status",
  "project_type",
  "percent_complete_method",
  "column_break_5",
  "project_template",
  "priority",
  "department",
  "is_active",
  "percent_complete",
  "section_break_18",
  "expected_start_date",
  "actual_start_date",
  "actual_time",
  "column_break_20",
  "expected_end_date",
  "actual_end_date",
  "costing_tab",
  "project_details",
  "estimated_costing",
  "total_costing_amount",
  "total_purchase_cost",
  "company",
  "column_break_28",
  "total_sales_amount",
  "total_billable_amount",
  "total_billed_amount",
  "total_consumed_material_cost",
  "cost_center",
  "margin",
  "gross_margin",
  "column_break_37",
  "per_gross_margin",
  "monitor_progress_tab",
  "collect_progress",
  "holiday_list",
  "frequency",
  "from_time",
  "to_time",
  "first_email",
  "second_email",
  "daily_time_to_send",
  "day_to_send",
  "weekly_time_to_send",
  "column_break_45",
  "subject",
  "message",
  "more_info_tab",
  "customer_details",
  "customer",
  "column_break_14",
  "sales_order",
  "users_section",
  "users",
  "copied_from",
  "section_break0",
  "notes",
  "connections_tab"
 ],
 "fields": [
  {
   "fieldname": "project_name",
   "fieldtype": "Data",
   "in_global_search": 1,
   "label": "Project Name",
   "oldfieldtype": "Data",
   "reqd": 1,
   "unique": 1
  },
  {
   "default": "Open",
   "fieldname": "status",
   "fieldtype": "Select",
   "in_import_template": 1,
   "in_standard_filter": 1,
   "label": "Status",
   "no_copy": 1,
   "oldfieldname": "status",
   "oldfieldtype": "Select",
   "options": "Open\nOn hold\nCompleted\nCancelled",
   "search_index": 1
  },
  {
   "fieldname": "project_type",
   "fieldtype": "Link",
   "in_import_template": 1,
   "in_list_view": 1,
   "in_standard_filter": 1,
   "label": "Project Type",
   "oldfieldname": "project_type",
   "oldfieldtype": "Data",
   "options": "Project Type"
  },
  {
   "fieldname": "is_active",
   "fieldtype": "Select",
   "label": "Is Active",
   "oldfieldname": "is_active",
   "oldfieldtype": "Select",
   "options": "Yes\nNo"
  },
  {
   "default": "Task Completion",
   "fieldname": "percent_complete_method",
   "fieldtype": "Select",
   "label": "% Complete Method",
   "options": "Manual\nTask Completion\nTask Progress\nTask Weight"
  },
  {
   "bold": 1,
   "fieldname": "percent_complete",
   "fieldtype": "Percent",
   "in_list_view": 1,
   "label": "% Completed",
   "no_copy": 1,
   "read_only_depends_on": "eval:doc.percent_complete_method != 'Manual'"
  },
  {
   "fieldname": "column_break_5",
   "fieldtype": "Column Break"
  },
  {
   "allow_in_quick_entry": 1,
   "fieldname": "project_template",
   "fieldtype": "Link",
   "label": "From Template",
   "options": "Project Template",
   "set_only_once": 1
  },
  {
   "bold": 1,
   "fieldname": "expected_start_date",
   "fieldtype": "Date",
   "in_import_template": 1,
   "in_list_view": 1,
   "label": "Expected Start Date",
   "oldfieldname": "project_start_date",
   "oldfieldtype": "Date"
  },
  {
   "bold": 1,
   "fieldname": "expected_end_date",
   "fieldtype": "Date",
   "in_import_template": 1,
   "in_list_view": 1,
   "label": "Expected End Date",
   "oldfieldname": "completion_date",
   "oldfieldtype": "Date"
  },
  {
   "fieldname": "priority",
   "fieldtype": "Select",
   "in_standard_filter": 1,
   "label": "Priority",
   "oldfieldname": "priority",
   "oldfieldtype": "Select",
   "options": "Medium\nLow\nHigh"
  },
  {
   "fieldname": "department",
   "fieldtype": "Link",
   "label": "Department",
   "options": "Department"
  },
  {
   "collapsible": 1,
   "fieldname": "customer_details",
   "fieldtype": "Section Break",
   "label": "Customer Details",
   "oldfieldtype": "Section Break",
   "options": "fa fa-user"
  },
  {
   "fieldname": "customer",
   "fieldtype": "Link",
   "in_global_search": 1,
   "in_import_template": 1,
   "label": "Customer",
   "no_copy": 1,
   "oldfieldname": "customer",
   "oldfieldtype": "Link",
   "options": "Customer",
   "print_hide": 1,
   "search_index": 1
  },
  {
   "fieldname": "column_break_14",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "sales_order",
   "fieldtype": "Link",
   "label": "Sales Order",
   "no_copy": 1,
   "options": "Sales Order"
  },
  {
   "collapsible": 1,
   "fieldname": "users_section",
   "fieldtype": "Section Break",
   "label": "Users"
  },
  {
   "description": "Project will be accessible on the website to these users",
   "fieldname": "users",
   "fieldtype": "Table",
   "label": "Users",
   "options": "Project User",
   "permlevel": 1
  },
  {
   "fieldname": "copied_from",
   "fieldtype": "Data",
   "hidden": 1,
   "label": "Copied From",
   "permlevel": 1,
   "read_only": 1
  },
  {
   "collapsible": 1,
   "fieldname": "section_break0",
   "fieldtype": "Section Break",
   "label": "Notes",
   "oldfieldtype": "Section Break",
   "options": "fa fa-list"
  },
  {
   "fieldname": "notes",
   "fieldtype": "Text Editor",
   "label": "Notes",
   "oldfieldname": "notes",
   "oldfieldtype": "Text Editor"
  },
  {
   "collapsible": 1,
   "fieldname": "section_break_18",
   "fieldtype": "Section Break",
   "label": "Timeline"
  },
  {
   "fieldname": "actual_start_date",
   "fieldtype": "Date",
   "label": "Actual Start Date (via Timesheet)",
   "read_only": 1
  },
  {
   "fieldname": "actual_time",
   "fieldtype": "Float",
   "label": "Actual Time in Hours (via Timesheet)",
   "read_only": 1
  },
  {
   "fieldname": "column_break_20",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "actual_end_date",
   "fieldtype": "Date",
   "label": "Actual End Date (via Timesheet)",
   "oldfieldname": "act_completion_date",
   "oldfieldtype": "Date",
   "read_only": 1
  },
  {
   "fieldname": "project_details",
   "fieldtype": "Section Break",
   "label": "Costing and Billing",
   "oldfieldtype": "Section Break",
   "options": "fa fa-money"
  },
  {
   "fieldname": "estimated_costing",
   "fieldtype": "Currency",
   "in_import_template": 1,
   "in_list_view": 1,
   "label": "Estimated Cost",
   "oldfieldname": "project_value",
   "oldfieldtype": "Currency",
   "options": "Company:company:default_currency"
  },
  {
   "fieldname": "total_costing_amount",
   "fieldtype": "Currency",
   "label": "Total Costing Amount (via Timesheet)",
   "read_only": 1
  },
  {
   "fieldname": "total_purchase_cost",
   "fieldtype": "Currency",
   "label": "Total Purchase Cost (via Purchase Invoice)",
   "read_only": 1
  },
  {
   "fieldname": "company",
   "fieldtype": "Link",
   "label": "Company",
   "options": "Company",
   "remember_last_selected_value": 1,
   "reqd": 1
  },
  {
   "fieldname": "column_break_28",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "total_sales_amount",
   "fieldtype": "Currency",
   "label": "Total Sales Amount (via Sales Order)",
   "read_only": 1
  },
  {
   "fieldname": "total_billable_amount",
   "fieldtype": "Currency",
   "label": "Total Billable Amount (via Timesheet)",
   "read_only": 1
  },
  {
   "fieldname": "total_billed_amount",
   "fieldtype": "Currency",
   "label": "Total Billed Amount (via Sales Invoice)",
   "read_only": 1
  },
  {
   "fieldname": "total_consumed_material_cost",
   "fieldtype": "Currency",
   "label": "Total Consumed Material Cost (via Stock Entry)",
   "read_only": 1
  },
  {
   "fieldname": "cost_center",
   "fieldtype": "Link",
   "label": "Default Cost Center",
   "options": "Cost Center"
  },
  {
   "fieldname": "margin",
   "fieldtype": "Section Break",
   "label": "Margin",
   "oldfieldtype": "Column Break",
   "width": "50%"
  },
  {
   "fieldname": "gross_margin",
   "fieldtype": "Currency",
   "label": "Gross Margin",
   "oldfieldname": "gross_margin_value",
   "oldfieldtype": "Currency",
   "options": "Company:company:default_currency",
   "read_only": 1
  },
  {
   "fieldname": "column_break_37",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "per_gross_margin",
   "fieldtype": "Percent",
   "label": "Gross Margin %",
   "oldfieldname": "per_gross_margin",
   "oldfieldtype": "Currency",
   "read_only": 1
  },
  {
   "default": "0",
   "fieldname": "collect_progress",
   "fieldtype": "Check",
   "label": "Collect Progress",
   "search_index": 1
  },
  {
   "depends_on": "collect_progress",
   "fieldname": "holiday_list",
   "fieldtype": "Link",
   "label": "Holiday List",
   "options": "Holiday List"
  },
  {
   "depends_on": "eval:doc.collect_progress == true",
   "fieldname": "frequency",
   "fieldtype": "Select",
   "label": "Frequency To Collect Progress",
   "options": "Hourly\nTwice Daily\nDaily\nWeekly"
  },
  {
   "depends_on": "eval:(doc.frequency == \"Hourly\" && doc.collect_progress)",
   "fieldname": "from_time",
   "fieldtype": "Time",
   "label": "From Time"
  },
  {
   "depends_on": "eval:(doc.frequency == \"Hourly\" && doc.collect_progress)",
   "fieldname": "to_time",
   "fieldtype": "Time",
   "label": "To Time"
  },
  {
   "depends_on": "eval:(doc.frequency == \"Twice Daily\" && doc.collect_progress == true)\n\n",
   "fieldname": "first_email",
   "fieldtype": "Time",
   "label": "First Email"
  },
  {
   "depends_on": "eval:(doc.frequency == \"Twice Daily\" && doc.collect_progress == true)",
   "fieldname": "second_email",
   "fieldtype": "Time",
   "label": "Second Email"
  },
  {
   "depends_on": "eval:(doc.frequency == \"Daily\" && doc.collect_progress == true)",
   "fieldname": "daily_time_to_send",
   "fieldtype": "Time",
   "label": "Daily Time to send"
  },
  {
   "depends_on": "eval:(doc.frequency == \"Weekly\" && doc.collect_progress == true)",
   "fieldname": "day_to_send",
   "fieldtype": "Select",
   "label": "Day to Send",
   "options": "Monday\nTuesday\nWednesday\nThursday\nFriday\nSaturday\nSunday"
  },
  {
   "depends_on": "eval:(doc.frequency == \"Weekly\" && doc.collect_progress == true)",
   "fieldname": "weekly_time_to_send",
   "fieldtype": "Time",
   "label": "Weekly Time to send"
  },
  {
   "fieldname": "column_break_45",
   "fieldtype": "Column Break"
  },
  {
   "depends_on": "collect_progress",
   "description": "Message will be sent to the users to get their status on the Project",
   "fieldname": "message",
   "fieldtype": "Text",
   "label": "Message",
   "mandatory_depends_on": "collect_progress"
  },
  {
   "fieldname": "naming_series",
   "fieldtype": "Select",
   "label": "Series",
   "no_copy": 1,
   "options": "PROJ-.####",
   "print_hide": 1,
   "reqd": 1,
   "set_only_once": 1
  },
  {
   "depends_on": "collect_progress",
   "fieldname": "subject",
   "fieldtype": "Data",
   "label": "Subject",
   "mandatory_depends_on": "collect_progress"
  },
  {
   "fieldname": "costing_tab",
   "fieldtype": "Tab Break",
   "label": "Costing"
  },
  {
   "fieldname": "monitor_progress_tab",
   "fieldtype": "Tab Break",
   "label": "Progress"
  },
  {
   "fieldname": "more_info_tab",
   "fieldtype": "Tab Break",
   "label": "More Info"
  },
  {
   "fieldname": "connections_tab",
   "fieldtype": "Tab Break",
   "label": "Connections",
   "show_dashboard": 1
  }
 ],
 "icon": "folder-kanban",
 "idx": 29,
 "index_web_pages_for_search": 1,
 "links": [],
 "max_attachments": 4,
 "modified": "2026-09-30 23:24:44.044604",
 "modified_by": "Administrator",
 "module": "Projects",
 "name": "Project",
 "naming_rule": "By \"Naming Series\" field",
 "owner": "Administrator",
 "permissions": [
  {
   "delete": 1,
   "email": 1,
   "export": 1,
   "permlevel": 1,
   "print": 1,
   "read": 1,
   "report": 1,
   "role": "Projects Manager",
   "share": 1,
   "write": 1
  },
  {
   "create": 1,
   "delete": 1,
   "email": 1,
   "print": 1,
   "read": 1,
   "report": 1,
   "role": "Projects User",
   "share": 1,
   "write": 1
  },
  {
   "permlevel": 1,
   "read": 1,
   "report": 1,
   "role": "Desk User"
  },
  {
   "create": 1,
   "delete": 1,
   "email": 1,
   "export": 1,
   "print": 1,
   "read": 1,
   "report": 1,
   "role": "Projects Manager",
   "share": 1,
   "write": 1
  },
  {
   "email": 1,
   "export": 1,
   "print": 1,
   "report": 1,
   "role": "Employee",
   "select": 1,
   "share": 1
  },
  {
   "role": "HR User",
   "select": 1
  },
  {
   "role": "HR Manager",
   "select": 1
  },
  {
   "role": "Accounts Manager",
   "select": 1
  },
  {
   "role": "Accounts User",
   "select": 1
  },
  {
   "role": "Delivery Manager",
   "select": 1
  },
  {
   "role": "Delivery User",
   "select": 1
  },
  {
   "role": "Maintenance Manager",
   "select": 1
  },
  {
   "role": "Maintenance User",
   "select": 1
  },
  {
   "role": "Manufacturing Manager",
   "select": 1
  },
  {
   "role": "Manufacturing User",
   "select": 1
  },
  {
   "role": "Purchase Manager",
   "select": 1
  },
  {
   "role": "Purchase Master Manager",
   "select": 1
  },
  {
   "role": "Purchase User",
   "select": 1
  },
  {
   "role": "Quality Manager",
   "select": 1
  },
  {
   "role": "Sales Manager",
   "select": 1
  },
  {
   "role": "Sales Master Manager",
   "select": 1
  },
  {
   "role": "Sales User",
   "select": 1
  },
  {
   "role": "Stock Manager",
   "select": 1
  },
  {
   "role": "Stock User",
   "select": 1
  },
  {
   "role": "Support Team",
   "select": 1
  }
 ],
 "quick_entry": 1,
 "row_format": "Dynamic",
 "search_fields": "project_name,customer, status, priority, is_active",
 "show_name_in_global_search": 1,
 "show_title_field_in_link": 1,
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": [],
 "timeline_field": "customer",
 "title_field": "project_name",
 "track_seen": 1
}
```

## frappe/hooks.py

Commit `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` · full blob SHA-256 `31eaac57b360a2f33d97bdaa2d30134d74d50fd532cab932d5b565d45b35d4fe`

Lines 114–164

```python
# permissions

permission_query_conditions = {
	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
	"ToDo": "frappe.desk.doctype.todo.todo.get_permission_query_conditions",
	"User": "frappe.core.doctype.user.user.get_permission_query_conditions",
	"Dashboard Settings": "frappe.desk.doctype.dashboard_settings.dashboard_settings.get_permission_query_conditions",
	"Notification Log": "frappe.desk.doctype.notification_log.notification_log.get_permission_query_conditions",
	"Dashboard": "frappe.desk.doctype.dashboard.dashboard.get_permission_query_conditions",
	"Dashboard Chart": "frappe.desk.doctype.dashboard_chart.dashboard_chart.get_permission_query_conditions",
	"Number Card": "frappe.desk.doctype.number_card.number_card.get_permission_query_conditions",
	"Notification Settings": "frappe.desk.doctype.notification_settings.notification_settings.get_permission_query_conditions",
	"Note": "frappe.desk.doctype.note.note.get_permission_query_conditions",
	"Kanban Board": "frappe.desk.doctype.kanban_board.kanban_board.get_permission_query_conditions",
	"Contact": "frappe.contacts.address_and_contact.get_permission_query_conditions_for_contact",
	"Address": "frappe.contacts.address_and_contact.get_permission_query_conditions_for_address",
	"Communication": "frappe.core.doctype.communication.communication.get_permission_query_conditions_for_communication",
	"Workflow Action": "frappe.workflow.doctype.workflow_action.workflow_action.get_permission_query_conditions",
	"Prepared Report": "frappe.core.doctype.prepared_report.prepared_report.get_permission_query_condition",
	"File": "frappe.core.doctype.file.file.get_permission_query_conditions",
	"User Invitation": "frappe.core.doctype.user_invitation.user_invitation.get_permission_query_conditions",
	"Tag Link": "frappe.desk.doctype.tag_link.tag_link.get_permission_query_conditions",
	"Document Follow": "frappe.email.doctype.document_follow.document_follow.get_permission_query_conditions",
	"Custom Sidebar": "frappe.desk.doctype.custom_sidebar.custom_sidebar.get_permission_query_conditions",
	"Dock": "frappe.desk.doctype.dock.dock.get_permission_query_conditions",
}

has_permission = {
	"Event": "frappe.desk.doctype.event.event.has_permission",
	"ToDo": "frappe.desk.doctype.todo.todo.has_permission",
	"Note": "frappe.desk.doctype.note.note.has_permission",
	"User": "frappe.core.doctype.user.user.has_permission",
	"Dashboard Chart": "frappe.desk.doctype.dashboard_chart.dashboard_chart.has_permission",
	"Number Card": "frappe.desk.doctype.number_card.number_card.has_permission",
	"Kanban Board": "frappe.desk.doctype.kanban_board.kanban_board.has_permission",
	"Contact": "frappe.contacts.address_and_contact.has_permission",
	"Address": "frappe.contacts.address_and_contact.has_permission",
	"Communication": "frappe.core.doctype.communication.communication.has_permission",
	"Workflow Action": "frappe.workflow.doctype.workflow_action.workflow_action.has_permission",
	"File": "frappe.core.doctype.file.file.has_permission",
	"Prepared Report": "frappe.core.doctype.prepared_report.prepared_report.has_permission",
	"Notification Settings": "frappe.desk.doctype.notification_settings.notification_settings.has_permission",
	"Dashboard Settings": "frappe.desk.doctype.dashboard_settings.dashboard_settings.has_permission",
	"Notification Log": "frappe.desk.doctype.notification_log.notification_log.has_permission",
	"User Invitation": "frappe.core.doctype.user_invitation.user_invitation.has_permission",
	"Document Follow": "frappe.email.doctype.document_follow.document_follow.has_permission",
	"Custom Sidebar": "frappe.desk.doctype.custom_sidebar.custom_sidebar.has_permission",
	"Dock": "frappe.desk.doctype.dock.dock.has_permission",
}

has_website_permission = {"Address": "frappe.contacts.doctype.address.address.has_website_permission"}
```

## frappe/database/__init__.py

Commit `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` · full blob SHA-256 `c78ea57b3fee7ca4299ece3e384dd62fa6e655e8d9c6e42f31307db4c20b7b29`

Lines 63–89

```python
def get_db(socket=None, host=None, user=None, password=None, port=None, cur_db_name=None):
	import frappe

	conf = frappe.local.conf

	if conf.db_type == "postgres":
		import frappe.database.postgres.database

		return frappe.database.postgres.database.PostgresDatabase(
			socket, host, user, password, port, cur_db_name
		)
	elif conf.db_type == "sqlite":
		import frappe.database.sqlite.database

		return frappe.database.sqlite.database.SQLiteDatabase(cur_db_name=cur_db_name)
	elif conf.get("use_mysqlclient", 1):
		import frappe.database.mariadb.mysqlclient

		return frappe.database.mariadb.mysqlclient.MariaDBDatabase(
			socket, host, user, password, port, cur_db_name
		)
	else:
		import frappe.database.mariadb.database

		return frappe.database.mariadb.database.MariaDBDatabase(
			socket, host, user, password, port, cur_db_name
		)
```

## frappe/app.py

Commit `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` · full blob SHA-256 `1e910e76bcbf596dc708dbd4d8f682f6a6e37368971afcca5f4512efeaa845f9`

Lines 214–251

```python
def init_request(request):
	site = _site or request.headers.get("X-Frappe-Site-Name") or get_site_name(request.host)
	try:
		frappe.init(site, sites_path=_sites_path, force=True, is_request=True)
	finally:
		frappe.local.request = request
		request.after_response = CallbackManager()

	assert frappe.local.conf and frappe.local.conf.db_name, "config should be loaded"

	frappe.local.is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

	frappe.connect(set_admin_as_user=False)
	if frappe.local.conf.maintenance_mode:
		if frappe.local.conf.allow_reads_during_maintenance:
			setup_read_only_mode()
		else:
			raise frappe.SessionStopped("Session Stopped")

	if request.path.startswith("/api/method/upload_file"):
		from frappe.core.api.file import get_max_file_size

		request.max_content_length = get_max_file_size()
	else:
		request.max_content_length = cint(frappe.local.conf.get("max_file_size")) or 25 * 1024 * 1024
	make_form_dict(request)

	if request.method != "OPTIONS":
		frappe.local.http_request = HTTPRequest()

	for before_request_task in frappe.get_hooks("before_request"):
		frappe.call(before_request_task)


def setup_read_only_mode():
	"""During maintenance_mode reads to DB can still be performed to reduce downtime. This
	function sets up read only mode

```

Lines 458–472

```python
def sync_database():
	db = getattr(frappe.local, "db", None)
	if not db:
		# db isn't initialized, can't commit or rollback
		return

	# if HTTP method would change server state, commit if necessary
	if frappe.local.request.method in UNSAFE_HTTP_METHODS or frappe.local.flags.commit:
		db.commit(chain=True)
	else:
		db.rollback(chain=True)

	# update session
	if session := getattr(frappe.local, "session_obj", None):
		frappe.request.after_response.add(session.update)
```

## erpnext/hooks.py

Commit `7474d9e786277383de1242ab882f16856d17a9c9` · full blob SHA-256 `28c286e338e7e28cdc8d23cc2168d52251da49c012c21de64d839d484be5c310`

Lines 77–86

```python
	],
}

page_js = {"print": "public/js/print.js"}

extend_doctype_class = {"Address": "erpnext.accounts.custom.address.ERPNextAddress"}

override_whitelisted_methods = {"frappe.www.contact.send_message": "erpnext.templates.utils.send_message"}

welcome_email = "erpnext.setup.utils.welcome_email"
```

Lines 339–352

```python
has_website_permission = {
	"Sales Order": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Quotation": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Sales Invoice": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Supplier Quotation": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Purchase Order": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Purchase Invoice": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Material Request": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Delivery Note": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Issue": "erpnext.support.doctype.issue.issue.has_website_permission",
	"Timesheet": "erpnext.controllers.website_list_for_contact.has_website_permission",
	"Project": "erpnext.controllers.website_list_for_contact.has_website_permission",
}

```

## erpnext/projects/doctype/project_user/project_user.json

Commit `7474d9e786277383de1242ab882f16856d17a9c9` · full blob SHA-256 `01e03f20c52a5c79c85db241061d496b8aed5242787e9c17390665a21aac395e`

Lines 1–97

```json
{
 "actions": [],
 "creation": "2016-03-25 02:52:19.283003",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "user",
  "email",
  "image",
  "column_break_2",
  "full_name",
  "welcome_email_sent",
  "view_attachments",
  "hide_timesheets",
  "section_break_5",
  "project_status"
 ],
 "fields": [
  {
   "fieldname": "user",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "User",
   "options": "User",
   "reqd": 1,
   "search_index": 1
  },
  {
   "fetch_from": "user.email",
   "fieldname": "email",
   "fieldtype": "Read Only",
   "label": "Email"
  },
  {
   "fetch_from": "user.user_image",
   "fieldname": "image",
   "fieldtype": "Read Only",
   "hidden": 1,
   "in_global_search": 1,
   "label": "Image"
  },
  {
   "fieldname": "column_break_2",
   "fieldtype": "Column Break"
  },
  {
   "fetch_from": "user.full_name",
   "fieldname": "full_name",
   "fieldtype": "Read Only",
   "in_list_view": 1,
   "label": "Full Name"
  },
  {
   "default": "0",
   "fieldname": "welcome_email_sent",
   "fieldtype": "Check",
   "label": "Welcome email sent"
  },
  {
   "columns": 2,
   "default": "0",
   "fieldname": "view_attachments",
   "fieldtype": "Check",
   "in_list_view": 1,
   "label": "View attachments"
  },
  {
   "columns": 2,
   "default": "0",
   "fieldname": "hide_timesheets",
   "fieldtype": "Check",
   "label": "Hide timesheets"
  },
  {
   "fieldname": "section_break_5",
   "fieldtype": "Section Break"
  },
  {
   "depends_on": "eval:parent.doctype == 'Project Update'",
   "fieldname": "project_status",
   "fieldtype": "Text",
   "label": "Project Status"
  }
 ],
 "istable": 1,
 "links": [],
 "modified": "2024-03-27 13:10:21.859474",
 "modified_by": "Administrator",
 "module": "Projects",
 "name": "Project User",
 "owner": "Administrator",
 "permissions": [],
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": []
}
```

## construction/hooks.py

Commit `9098c0a33f003af59547925d8cbc3a5eee6fbba5` · full blob SHA-256 `1a4f17cc0cd6525dd213a03fe051b23094ea955a579c96db9b82aa18b76dc64a`

Lines 276–281

```python
doc_events = {
    "*": {"validate": "construction.overrides.scope_enforcement.validate"},
    "Purchase Order": {
        "validate": "construction.services.boq_transaction_validation.validate_document",
        "on_submit": "construction.services.resource_price_service.capture_price_from_purchase_document",
        "on_cancel": "construction.services.resource_price_service.cancel_price_history_for_document",
```

Lines 338–348

```python
        ]
    },
    "Cost Center": {"validate": "construction.services.bilingual_service.enforce_bilingual_arabic_policy"},
    "Warehouse": {"validate": "construction.services.bilingual_service.enforce_bilingual_arabic_policy"},
    "Project": {
        "validate": [
            "construction.services.bilingual_service.enforce_bilingual_arabic_policy",
            "construction.services.narrative_sanitizer.validate_narrative_fields",
        ]
    },
    "Item Group": {"validate": "construction.services.bilingual_service.enforce_bilingual_arabic_policy"},
```

Lines 412–452

```python
permission_query_conditions = {
    "*": "construction.overrides.scope_query.add_scope_conditions",
    **{
        doctype: "construction.overrides.boq_permissions.boq_parent_query_conditions"
        for doctype in (
            "BOQ Item",
            "BOQ Structure",
            "BOQ Item Stage",
            "BOQ Quantity Revision",
            "BOQ Cost Analysis",
            "Variation Order",
        )
    },
}
permission_query_conditions["Form Layout Profile"] = (
    "construction.overrides.layout_permissions.form_layout_profile_query_conditions"
)

has_permission = {
    doctype: "construction.overrides.boq_permissions.has_boq_parent_permission"
    for doctype in (
        "BOQ Item",
        "BOQ Structure",
        "BOQ Item Stage",
        "BOQ Quantity Revision",
        "BOQ Cost Analysis",
        "Variation Order",
    )
}

# F11-D002: BOQ Header direct reads/writes additionally require the selected
# scope to cover the header's project/company (authorization boundary, not a
# list filter). Native role/User Permission checks still apply independently.
has_permission["BOQ Header"] = "construction.overrides.boq_permissions.has_boq_header_permission"

# F11: Files attached to BOQ doctypes inherit the parent's read/write
# boundary; all other files keep vendor behavior.
has_permission["File"] = "construction.overrides.file_permissions.has_file_parent_permission"
has_permission["Form Layout Profile"] = (
    "construction.overrides.layout_permissions.has_form_layout_profile_permission"
)
```

## construction/overrides/scope_enforcement.py

Commit `9098c0a33f003af59547925d8cbc3a5eee6fbba5` · full blob SHA-256 `448f4a5b7e8ecc65928a63f90762be3a7ebd4947389d3ad7f27df8afb69669a1`

Lines 173–253

```python
def validate(doc, method):
    # ─────────────────────────────────────────────────────────
    # ALWAYS: Branch-Company integrity (regardless of scope context)
    # A document must never have a branch from a different company.
    # This runs on both INSERT and UPDATE.
    # ─────────────────────────────────────────────────────────
    if hasattr(doc, "branch") and doc.branch and hasattr(doc, "company") and doc.company:
        branch_company = frappe.db.get_value("Branch", doc.branch, "company")
        if branch_company and branch_company != doc.company:
            frappe.throw(
                frappe._("Branch '{0}' belongs to Company '{1}', not '{2}.'").format(
                    doc.branch, branch_company, doc.company
                )
            )

    # ─────────────────────────────────────────────────────────
    # SCOPE BOOTSTRAP: narrowly exempt writes to User Scope Context.
    # Must run BEFORE the generic active-scope requirement below,
    # otherwise the first scope can never be established.
    # ─────────────────────────────────────────────────────────
    if doc.doctype == "User Scope Context":
        _validate_own_scope_context_write(doc)
        return

    # In migration / setup / install, skip scope enforcement
    if _in_system_install():
        return

    # Explicit service-only bypass token (server-controlled flag).
    if getattr(frappe.flags, "construction_scope_bypass", False):
        return

    # ─────────────────────────────────────────────────────────
    # OPTIONAL: Scope context checks (only when feature is enabled).
    # Configuration-read failures fail CLOSED (see helper).
    # ─────────────────────────────────────────────────────────
    enabled = _scope_enabled_or_fail_closed()

    if not enabled:
        return

    user = frappe.session.user
    if user == "Administrator":
        return

    # Guests can never create or modify scoped business documents.
    if user == "Guest":
        frappe.throw(
            frappe._("Scope enforcement is active: Guest sessions cannot modify scoped documents."),
            frappe.PermissionError,
        )

    # Check if user has System Manager (document-write exemption).
    # NOTE: finance/report role exemptions apply to REPORTS only
    # (see overrides/scope_report.py) and deliberately do NOT bypass
    # document scope enforcement here.
    if "System Manager" in frappe.get_roles():
        return

    scope = get_user_scope_context(user)
    # A Timesheet project reference (the ``parent_project`` alias or a
    # ``time_logs`` row project) makes the document a scoped document, so it
    # can no longer evade the active-context requirement below.
    referenced_projects = _timesheet_project_references(doc)
    has_scope_fields = any(
        hasattr(doc, f) and getattr(doc, f, None) for f in _SCOPE_DIMENSION_FIELDS
    ) or bool(referenced_projects)
    if has_scope_fields and (not scope or not scope.company):
        frappe.throw(
            frappe._(
                "Scope enforcement is active: An active User Scope Context is required to create or modify scoped documents."
            ),
            frappe.PermissionError,
        )

    if not scope:
        return

    # Enforce company boundary for scoped non-admin users
    if hasattr(doc, "company") and doc.company and scope.company and doc.company != scope.company:
        frappe.throw(
```

## construction/api/scope_context_api.py

Commit `9098c0a33f003af59547925d8cbc3a5eee6fbba5` · full blob SHA-256 `f61bb31432ea22f641234704dabec1095416010875aa8548404f6c7e3cdcba1f`

Lines 105–116

```python
def get_user_scope_context(user=None):
    """
    Returns the User Scope Context document for the given user, or None.
    Internal helper — NOT whitelisted. Used by scope_enforcement.py and boot.py.
    """
    user = user or frappe.session.user
    name = frappe.db.get_value("User Scope Context", {"user": user})
    if name:
        return frappe.get_doc("User Scope Context", name)
    return None


```
