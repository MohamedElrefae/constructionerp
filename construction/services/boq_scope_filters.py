"""SQL-aware BOQ scope filter builders."""

from __future__ import annotations

import frappe

from construction.services.scope_resolution import (
	get_cost_center_descendants,
	get_scope_token,
	resolve_user_scope,
	should_enforce_scope,
)

# Statuses approved for cost attribution on transactions.
# Draft/Pricing: not yet finalized — attribution not permitted.
# Closed: no further transactions allowed per business rule.
ALLOWED_TRANSACTION_BOQ_STATUSES = ["Locked", "Frozen"]
EXCLUDED_TRANSACTION_BOQ_STATUSES = ["Draft", "Pricing", "Closed"]


def get_scope_payload(user=None):
	scope = resolve_user_scope(user)
	return {
		"scope": {
			"company": scope.company,
			"cost_center": scope.cost_center,
			"project": scope.project,
			"scope_type": scope.scope_type,
		},
		"scope_token": get_scope_token(user),
	}


def apply_header_scope(conditions, values, scope=None, header_alias="h"):
	"""Append BOQ Header scope constraints using Project as the source of truth."""
	scope = scope or resolve_user_scope()
	project_alias = "p"
	join_project = False

	if scope.project:
		conditions.append(f"{header_alias}.project = %(scope_project)s")
		values["scope_project"] = scope.project
		return join_project

	if scope.company:
		join_project = True
		conditions.append(f"{project_alias}.company = %(scope_company)s")
		values["scope_company"] = scope.company

	if scope.cost_center and frappe.db.has_column("Project", "cost_center"):
		join_project = True
		cost_centers = get_cost_center_descendants(scope.cost_center)
		if cost_centers:
			conditions.append(f"{project_alias}.cost_center IN %(scope_cost_centers)s")
			values["scope_cost_centers"] = tuple(cost_centers)

	return join_project


def apply_header_filters(conditions, values, filters, header_alias="h"):
	if not filters:
		return False
	join_project = False
	if filters.get("project"):
		conditions.append(f"{header_alias}.project = %(project)s")
		values["project"] = filters.get("project")
	if filters.get("company"):
		join_project = True
		conditions.append("p.company = %(company)s")
		values["company"] = filters.get("company")
	if filters.get("cost_center") and frappe.db.has_column("Project", "cost_center"):
		join_project = True
		conditions.append("p.cost_center IN %(cost_centers)s")
		values["cost_centers"] = tuple(get_cost_center_descendants(filters.get("cost_center")))
	return join_project


def append_allowed_status_filter(conditions, values, header_alias="h"):
	conditions.append(f"{header_alias}.status IN %(allowed_statuses)s")
	values["allowed_statuses"] = tuple(ALLOWED_TRANSACTION_BOQ_STATUSES)


def resolve_query_scope(enforce_scope=None):
	if not should_enforce_scope(enforce_scope):
		return None
	return resolve_user_scope()
