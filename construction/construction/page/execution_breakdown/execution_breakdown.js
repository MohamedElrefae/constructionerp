frappe.pages["execution-breakdown"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Execution Breakdown"),
		single_column: true,
	});

	const state = {
		project: "",
		actions: {},
		nodes: [],
		collapsed: new Set(),
		focused: null,
		in_flight: 0,
		generation: 0,
	};

	const $root = $(page.main);
	$root.append(`
		<div class="execution-breakdown pt-3">
			<div class="alert alert-info d-none" data-role="status"></div>
			<button class="btn btn-default btn-sm d-none" data-action="retry-scope">${__(
				"Retry scope save"
			)}</button>
			<div class="alert alert-warning d-none" data-role="conflict">
				<div data-role="conflict-message" class="mb-2"></div>
				<div class="d-flex flex-wrap gap-1">
					<button class="btn btn-primary btn-sm" data-action="apply-selection">${__(
						"Apply my selection"
					)}</button>
					<button class="btn btn-default btn-sm" data-action="use-saved">${__("Use saved scope")}</button>
				</div>
			</div>
			<div class="tree" data-role="tree" role="tree" aria-label="${__("Execution locations")}"></div>
		</div>
	`);

	if (frappe.dom && typeof frappe.dom.set_style === "function") {
		frappe.dom.set_style(
			".execution-breakdown .tree-root { list-style: none; margin: 0; padding: 0; }" +
				' [dir="rtl"] .execution-breakdown .tree-children {' +
				" border-left: 0 !important;" +
				" border-right: 1px solid var(--border, var(--outline-gray-2)) !important;" +
				" margin-left: 0 !important;" +
				" margin-right: 12px !important;" +
				" padding-left: 0 !important;" +
				" padding-right: 20px !important;" +
				" }",
			"execution-breakdown-tree-style"
		);
	}

	const $status = $root.find('[data-role="status"]');
	const $tree = $root.find('[data-role="tree"]');
	const $retry_scope = $root.find('[data-action="retry-scope"]');
	const $conflict = $root.find('[data-role="conflict"]');

	function esc(value) {
		return frappe.utils.escape_html(String(value == null ? "" : value));
	}

	function set_status(message, kind) {
		$status
			.removeClass("d-none alert-info alert-warning alert-danger")
			.addClass(kind || "alert-info")
			.text(message || "")
			.toggleClass("d-none", !message);
	}

	function clear_tree() {
		state.nodes = [];
		state.actions = {};
		state.collapsed.clear();
		state.focused = null;
		$tree.empty();
	}

	function conflict_message() {
		const scope = window.scopeContext;
		const conflict = scope && scope._conflict;
		if (!conflict) return "";
		const saved = conflict.authoritative.project || __("none");
		return (
			__("The saved scope is now Project:") +
			" " +
			esc(saved) +
			" — " +
			__("Apply your selection or use the saved scope.")
		);
	}

	function is_current(project, generation) {
		return generation === state.generation && project === state.project;
	}

	function call(method, args) {
		state.in_flight += 1;
		let request;
		try {
			request = frappe.call({
				method: "construction.api.execution_tree_api." + method,
				type: method === "get_tree" ? "GET" : "POST",
				args: args,
			});
		} catch (error) {
			state.in_flight = Math.max(0, state.in_flight - 1);
			return Promise.reject(error);
		}
		return Promise.resolve(request)
			.then((response) => response.message)
			.finally(() => {
				state.in_flight = Math.max(0, state.in_flight - 1);
			});
	}

	function load_tree(project) {
		const target = String(project || "").trim();
		const generation = ++state.generation;
		const focusSnapshot = target && target === state.project ? capture_tree_focus() : null;
		if (focusSnapshot) {
			$tree.attr("tabindex", "-1").trigger("focus");
		}
		clear_tree();
		state.project = target;
		if (!target) {
			set_status(
				__("Select a Project in the top bar to view its execution tree."),
				"alert-info"
			);
			return Promise.resolve();
		}
		set_status(__("Loading…"), "alert-info");
		return call("get_tree", { project: target })
			.then((data) => {
				if (!is_current(target, generation)) {
					return;
				}
				if (!data || data.project !== target) {
					clear_tree();
					set_status(__("Not permitted."), "alert-danger");
					return;
				}
				state.actions = data.actions || {};
				state.nodes = data.nodes || [];
				const restoreFocus = focusSnapshot && document.activeElement === $tree[0];
				set_status("", "alert-info");
				render_tree();
				if (restoreFocus) restore_tree_focus(focusSnapshot);
			})
			.catch(() => {
				if (!is_current(target, generation)) {
					return;
				}
				clear_tree();
				set_status(__("Not permitted."), "alert-danger");
			});
	}

	function action_button(label, action, node, primary) {
		return (
			'<button class="btn btn-xs ' +
			(primary ? "btn-primary" : "btn-default") +
			' ml-1" data-action="' +
			esc(action) +
			'" data-name="' +
			esc(node.name) +
			'">' +
			esc(label) +
			"</button>"
		);
	}

	function node_actions(node) {
		const actions = state.actions || {};
		let html = action_button(__("View Coverage"), "view-coverage", node);
		if (actions.create && node.is_group) {
			html += action_button(__("Add child"), "create-child", node);
		}
		if (actions.update) {
			html += action_button(__("Edit"), "edit", node);
		}
		if (actions.move) {
			html += action_button(__("Move"), "move", node);
		}
		if (actions.set_disabled) {
			html += action_button(node.disabled ? __("Enable") : __("Disable"), "toggle", node);
		}
		if (actions.delete) {
			html += action_button(__("Delete"), "delete", node);
		}
		return html;
	}

	function node_has_children(node) {
		return (state.nodes || []).some(
			(item) => (item.parent_node || null) === (node.name || null)
		);
	}

	function toggle_expansion(node) {
		if (state.collapsed.has(node.name)) {
			state.collapsed.delete(node.name);
		} else {
			state.collapsed.add(node.name);
		}
		render_tree();
	}

	function focus_tree_node(name) {
		state.focused = name;
		const $items = $tree.find('[role="treeitem"]');
		$items.attr("tabindex", "-1");
		$items
			.filter(function () {
				return $(this).attr("data-name") === name;
			})
			.attr("tabindex", "0")
			.trigger("focus");
	}

	function capture_tree_focus() {
		const active = document.activeElement;
		if (!active || !active.getAttribute || !$tree[0] || !$tree[0].contains(active))
			return null;
		const isItem = active.getAttribute("role") === "treeitem";
		const action = active.tagName === "BUTTON" ? active.getAttribute("data-action") : null;
		if (!isItem && !action) return null;
		const name = active.getAttribute("data-name") || null;
		// Only actions rendered inside a tree item (or the root-create button) are restored.
		if (action && !name && action !== "create-root") return null;
		const candidates = [];
		let node = find_node(name);
		while (node) {
			candidates.push(node.name);
			node = find_node(node.parent_node);
		}
		return { action, name, candidates };
	}

	function restore_tree_focus(snapshot) {
		const visible = visible_nodes();
		const visibleNames = new Set(visible.map((node) => node.name));
		const fallback =
			snapshot.candidates.find((name) => visibleNames.has(name)) ||
			(visible.length ? visible[0].name : null);
		if (fallback) {
			state.focused = fallback;
			const $items = $tree.find('[role="treeitem"]');
			$items.attr("tabindex", "-1");
			$items
				.filter(function () {
					return $(this).attr("data-name") === fallback;
				})
				.attr("tabindex", "0");
		}
		if (snapshot.action && (!snapshot.name || visibleNames.has(snapshot.name))) {
			const $action = $tree.find("[data-action]").filter(function () {
				return (
					$(this).attr("data-action") === snapshot.action &&
					($(this).attr("data-name") || null) === snapshot.name
				);
			});
			if ($action.length) {
				$action.trigger("focus");
				return;
			}
		}
		if (fallback) focus_tree_node(fallback);
		else $tree.attr("tabindex", "-1").trigger("focus");
	}

	function visible_nodes() {
		const children = new Map();
		state.nodes.forEach((node) => {
			const parent = node.parent_node || null;
			if (!children.has(parent)) children.set(parent, []);
			children.get(parent).push(node);
		});
		const result = [];
		function walk(parent) {
			(children.get(parent) || []).forEach((node) => {
				result.push(node);
				if (!state.collapsed.has(node.name)) walk(node.name);
			});
		}
		walk(null);
		return result;
	}

	function render_nodes(children, parent, level, prefix) {
		const nodes = children.get(parent) || [];
		if (!nodes.length) {
			return "";
		}
		let html =
			level === 1
				? '<ul class="tree-root list-unstyled m-0 p-0" role="none">'
				: '<ul class="tree-children" role="group">';
		nodes.forEach((node, index) => {
			const number = prefix ? prefix + "." + (index + 1) : String(index + 1);
			const has_children = (children.get(node.name) || []).length > 0;
			const expanded = has_children && !state.collapsed.has(node.name);
			const marker = node.disabled ? " · " + __("Disabled") : "";
			const icon = has_children
				? frappe.utils.icon(
						expanded
							? "chevron-down"
							: frappe.utils.is_rtl()
							? "chevron-left"
							: "chevron-right",
						"sm"
				  )
				: frappe.utils.icon("circle-small", "xs");
			html +=
				'<li class="tree-node" role="treeitem" tabindex="' +
				(state.focused === node.name ? "0" : "-1") +
				'"' +
				' aria-level="' +
				level +
				'"' +
				(has_children ? ' aria-expanded="' + expanded + '"' : "") +
				' data-name="' +
				esc(node.name) +
				'">' +
				'<span class="tree-link" data-name="' +
				esc(node.name) +
				'">' +
				'<span class="' +
				(has_children ? "node-parent" : "node-leaf") +
				'">' +
				icon +
				"</span> " +
				'<a class="tree-label" data-name="' +
				esc(node.name) +
				'">' +
				esc(number + (node.title ? " " + node.title : "")) +
				"</a>" +
				'<span class="text-muted small">' +
				esc(marker) +
				"</span>" +
				node_actions(node) +
				"</span>" +
				(expanded ? render_nodes(children, node.name, level + 1, number) : "") +
				"</li>";
		});
		return html + "</ul>";
	}

	function render_tree() {
		const focusSnapshot = capture_tree_focus();
		if (!state.nodes.length) {
			$tree.html('<p class="text-muted">' + __("No execution locations yet.") + "</p>");
			if (state.actions.create) {
				$tree.append(
					'<button class="btn btn-primary btn-sm" data-action="create-root">' +
						__("Add root location") +
						"</button>"
				);
			}
			if (focusSnapshot) restore_tree_focus(focusSnapshot);
			return;
		}
		if (focusSnapshot && focusSnapshot.name) state.focused = focusSnapshot.name;
		const visible = visible_nodes();
		while (state.focused && !visible.some((node) => node.name === state.focused)) {
			const node = find_node(state.focused);
			state.focused = (node && node.parent_node) || null;
		}
		if (!state.focused && visible.length) state.focused = visible[0].name;
		const children = new Map();
		state.nodes.forEach((node) => {
			const parent = node.parent_node || null;
			if (!children.has(parent)) children.set(parent, []);
			children.get(parent).push(node);
		});
		let html = render_nodes(children, null, 1, "");
		if (state.actions.create) {
			html +=
				'<button class="btn btn-primary btn-sm mt-2" data-action="create-root">' +
				__("Add root location") +
				"</button>";
		}
		$tree.html(html);
		if (focusSnapshot) restore_tree_focus(focusSnapshot);
	}

	function find_node(name) {
		return state.nodes.find((node) => node.name === name);
	}

	function stale_selection() {
		set_status(__("The selected Project changed. Try again."), "alert-warning");
	}

	function create_node(parent) {
		const project = state.project;
		const generation = state.generation;
		const parent_name = parent ? parent.name : null;
		const parent_modified = parent ? parent.modified : null;
		frappe.prompt(
			[
				{
					fieldname: "title",
					fieldtype: "Data",
					label: __("Title"),
					reqd: 1,
				},
				{
					fieldname: "is_group",
					fieldtype: "Check",
					label: __("Is Group"),
					default: 0,
				},
			],
			(values) => {
				if (!is_current(project, generation)) {
					stale_selection();
					return;
				}
				call("create_node", {
					project: project,
					title: values.title,
					is_group: Boolean(values.is_group),
					parent_node: parent_name,
					expected_parent_modified: parent_modified,
				})
					.then(() => {
						if (is_current(project, generation)) {
							load_tree(project);
						}
					})
					.catch(() => {
						if (is_current(project, generation)) {
							clear_tree();
							set_status(__("Not permitted."), "alert-danger");
						}
					});
			},
			__("Add execution location")
		);
	}

	function edit_node(node) {
		const project = state.project;
		const generation = state.generation;
		const name = node.name;
		const modified = node.modified;
		frappe.prompt(
			[
				{
					fieldname: "title",
					fieldtype: "Data",
					label: __("Title"),
					default: node.title,
					reqd: 1,
				},
				{
					fieldname: "is_group",
					fieldtype: "Check",
					label: __("Is Group"),
					default: node.is_group ? 1 : 0,
				},
			],
			(values) => {
				if (!is_current(project, generation)) {
					stale_selection();
					return;
				}
				call("update_node", {
					project: project,
					name: name,
					expected_modified: modified,
					title: values.title,
					is_group: Boolean(values.is_group),
				})
					.then(() => {
						if (is_current(project, generation)) {
							load_tree(project);
						}
					})
					.catch(() => {
						if (is_current(project, generation)) {
							clear_tree();
							set_status(__("Not permitted."), "alert-danger");
						}
					});
			},
			__("Edit execution location")
		);
	}

	function move_node(node) {
		const project = state.project;
		const generation = state.generation;
		const name = node.name;
		const modified = node.modified;
		const candidates = state.nodes.filter((item) => item.is_group && item.name !== node.name);
		const options = [{ label: __("Root (no parent)"), value: "__root__" }].concat(
			candidates.map((item) => ({
				label: item.ebs_code + " · " + item.title,
				value: item.name,
			}))
		);
		frappe.prompt(
			[
				{
					fieldname: "parent_node",
					fieldtype: "Select",
					options: options,
					label: __("Destination parent"),
					reqd: 1,
				},
			],
			(values) => {
				if (!is_current(project, generation)) {
					stale_selection();
					return;
				}
				let destination = null;
				if (values.parent_node !== "__root__") {
					destination = candidates.find((item) => item.name === values.parent_node);
					if (!destination) {
						set_status(__("Select a group in this Project."), "alert-danger");
						return;
					}
				}
				call("move_node", {
					project: project,
					name: name,
					expected_modified: modified,
					parent_node: destination ? destination.name : null,
					expected_parent_modified: destination ? destination.modified : null,
				})
					.then(() => {
						if (is_current(project, generation)) {
							load_tree(project);
						}
					})
					.catch(() => {
						if (is_current(project, generation)) {
							clear_tree();
							set_status(__("Not permitted."), "alert-danger");
						}
					});
			},
			__("Move execution location")
		);
	}

	function toggle_node(node) {
		const project = state.project;
		const generation = state.generation;
		call("set_disabled", {
			project: project,
			name: node.name,
			expected_modified: node.modified,
			disabled: !node.disabled,
		})
			.then(() => {
				if (is_current(project, generation)) {
					load_tree(project);
				}
			})
			.catch(() => {
				if (is_current(project, generation)) {
					clear_tree();
					set_status(__("Not permitted."), "alert-danger");
				}
			});
	}

	function delete_node(node) {
		const project = state.project;
		const generation = state.generation;
		const name = node.name;
		const modified = node.modified;
		frappe.confirm(__("Delete this execution location?"), () => {
			if (!is_current(project, generation)) {
				stale_selection();
				return;
			}
			call("delete_node", {
				project: project,
				name: name,
				expected_modified: modified,
			})
				.then(() => {
					if (is_current(project, generation)) {
						load_tree(project);
					}
				})
				.catch(() => {
					if (is_current(project, generation)) {
						clear_tree();
						set_status(__("Not permitted."), "alert-danger");
					}
				});
		});
	}

	$root.on("click", "[data-action]", function (e) {
		if (e && typeof e.stopPropagation === "function") e.stopPropagation();
		if (state.in_flight > 0) {
			return;
		}
		const action = $(this).attr("data-action");
		const node = find_node($(this).attr("data-name"));
		if (action === "retry-scope") {
			if (
				window.scopeContext &&
				window.scopeContext._saveFailed &&
				!window.scopeContext._savePending
			) {
				set_status(__("Retrying scope save…"), "alert-info");
				window.scopeContext.retrySave();
			}
			return;
		}
		if (action === "apply-selection") {
			window.scopeContext && window.scopeContext.applySelection();
			return;
		}
		if (action === "use-saved") {
			window.scopeContext && window.scopeContext.applySavedScope();
			return;
		}
		if (action === "create-root") {
			create_node(null);
			return;
		}
		if (!node) {
			clear_tree();
			return;
		}
		if (action === "expand") {
			toggle_expansion(node);
		} else if (action === "create-child") {
			create_node(node);
		} else if (action === "edit") {
			edit_node(node);
		} else if (action === "move") {
			move_node(node);
		} else if (action === "view-coverage") {
			frappe.route_options = {
				project: state.project,
				execution_node: node.name,
			};
			if (typeof frappe.set_route === "function") {
				frappe.set_route("execution-coverage");
			}
		} else if (action === "toggle") {
			toggle_node(node);
		} else if (action === "delete") {
			delete_node(node);
		}
	});

	$root.on("click", "[role='treeitem']", function (e) {
		if (e && typeof e.stopPropagation === "function") e.stopPropagation();
		if (e && e.target && typeof $ === "function") {
			const $target = $(e.target);
			if ($target && typeof $target.closest === "function") {
				if ($target.closest("[data-action]").length) return;
				const $closestItem = $target.closest("[role='treeitem']");
				if (
					$closestItem.length &&
					$closestItem[0] !== this &&
					$closestItem.attr("data-name") !== $(this).attr("data-name")
				) {
					return;
				}
				const $self = $(this);
				if ($self && typeof $self.closest === "function") {
					const $targetGroup = $target.closest(".tree-children");
					const $ownGroup = $self.closest(".tree-children");
					if ($targetGroup.length && $targetGroup[0] !== $ownGroup[0]) {
						return;
					}
				}
			}
		}
		const node = find_node($(this).attr("data-name"));
		if (node && node_has_children(node)) toggle_expansion(node);
	});

	$root.on("focusin", "[role='treeitem']", function (e) {
		if (e.target !== this) return;
		const name = $(this).attr("data-name");
		if (!find_node(name)) return;
		state.focused = name;
		const $items = $tree.find('[role="treeitem"]');
		$items.attr("tabindex", "-1");
		$items
			.filter(function () {
				return $(this).attr("data-name") === name;
			})
			.attr("tabindex", "0");
	});

	$root.on("keydown", "[role='treeitem']", function (e) {
		if (
			!e ||
			![
				"Enter",
				" ",
				"ArrowDown",
				"ArrowUp",
				"ArrowLeft",
				"ArrowRight",
				"Home",
				"End",
			].includes(e.key)
		)
			return;
		if (e.target && typeof $ === "function") {
			const $target = $(e.target);
			if ($target && typeof $target.closest === "function") {
				if ($target.closest("[data-action]").length) return;
				const $closestItem = $target.closest("[role='treeitem']");
				if (
					$closestItem.length &&
					$closestItem[0] !== this &&
					$closestItem.attr("data-name") !== $(this).attr("data-name")
				) {
					return;
				}
			}
		}
		const node = find_node($(this).attr("data-name"));
		if (!node) return;
		if (typeof e.stopPropagation === "function") e.stopPropagation();
		if (typeof e.preventDefault === "function") e.preventDefault();
		const visible = visible_nodes();
		const index = visible.findIndex((item) => item.name === node.name);
		const expandKey = frappe.utils.is_rtl() ? "ArrowLeft" : "ArrowRight";
		const collapseKey = frappe.utils.is_rtl() ? "ArrowRight" : "ArrowLeft";
		let target = null;
		if (e.key === "ArrowDown") target = visible[index + 1];
		else if (e.key === "ArrowUp") target = visible[index - 1];
		else if (e.key === "Home") target = visible[0];
		else if (e.key === "End") target = visible[visible.length - 1];
		else if (e.key === expandKey && node_has_children(node)) {
			if (state.collapsed.has(node.name)) {
				toggle_expansion(node);
				target = node;
			} else target = visible[index + 1];
		} else if (e.key === collapseKey) {
			if (node_has_children(node) && !state.collapsed.has(node.name)) {
				toggle_expansion(node);
				target = node;
			} else target = find_node(node.parent_node);
		} else if ((e.key === "Enter" || e.key === " ") && node_has_children(node)) {
			toggle_expansion(node);
			target = node;
		}
		if (target) focus_tree_node(target.name);
	});

	function sync_scope() {
		const scope = window.scopeContext;
		const conflict = scope && scope._conflict;
		if (conflict) {
			$root.find('[data-role="conflict-message"]').text(conflict_message());
			$conflict.toggleClass("d-none", false);
		} else {
			$conflict.toggleClass("d-none", true);
			$root.find('[data-role="conflict-message"]').text("");
		}
		$retry_scope.toggleClass(
			"d-none",
			!(scope && scope._saveFailed && !scope._savePending && !conflict)
		);
		if (
			scope &&
			(!scope.supportsSaveConfirmation ||
				scope._savePending ||
				scope._saveQueued ||
				scope._saveFailed)
		) {
			++state.generation;
			state.project = "";
			clear_tree();
			set_status(
				conflict
					? __("Another session changed the scope. Choose how to resolve it.")
					: scope._saveFailed
					? __("Could not confirm the scope. Retry or refresh the page.")
					: __("Saving scope…"),
				"alert-info"
			);
			return;
		}
		const current = scope && scope.enabled && scope.getValidatedCurrentScope();
		load_tree(current && current.project);
	}

	const events =
		"scope:changed.executionBreakdown scope:save_confirmed.executionBreakdown scope:save_failed.executionBreakdown scope:save_conflict.executionBreakdown";
	function show_page() {
		$(document).off(events).on(events, sync_scope);
		sync_scope();
	}
	function hide_page() {
		$(document).off(events);
		++state.generation;
		state.project = "";
		clear_tree();
	}
	$(wrapper).on("show", show_page).on("hide", hide_page);
	show_page();
};
