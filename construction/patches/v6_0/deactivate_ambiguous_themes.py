import frappe


def execute():
	"""
	Deactivate non-default basic themes to prevent resolution ambiguity.

	After this patch:
	- Only Construction Light (is_default_light=1) and Construction Dark (is_default_dark=1)
	  are active system themes.
	- Basic 'Light' and 'Dark' themes are deactivated but kept in DB for rollback safety.
	"""

	# Verify the expected default themes exist before deactivating others
	defaults_ok = True

	for check in [
		{"is_system_theme": 1, "is_default_light": 1, "name": "Construction Light"},
		{"is_system_theme": 1, "is_default_dark": 1, "name": "Construction Dark"},
	]:
		exists = frappe.db.get_value("Construction Theme", check, "name")
		if not exists:
			frappe.log_error(
				f"Default theme missing: {check}",
				"Theme Deactivation Check Failed",
			)
			defaults_ok = False

	if not defaults_ok:
		print("SKIPPING: Default Construction themes not found. Please verify database state.")
		return

	# Soft-deactivate ambiguous themes (safer than deletion)
	ambiguous = ["Light", "Dark"]

	for theme_name in ambiguous:
		if frappe.db.exists("Construction Theme", theme_name):
			frappe.db.set_value(
				"Construction Theme",
				theme_name,
				{"is_active": 0, "is_default_light": 0, "is_default_dark": 0},
			)
			print(f"Deactivated ambiguous theme: {theme_name}")

	frappe.db.commit()

	# Log the final state
	final_state = frappe.get_all(
		"Construction Theme",
		filters={"is_active": 1},
		fields=["name", "is_system_theme", "is_default_light", "is_default_dark"],
	)
	print("Active themes after patch:")
	for t in final_state:
		print(
			f"  - {t.name}: system={t.is_system_theme}, default_light={t.is_default_light}, default_dark={t.is_default_dark}"
		)
