import json


TRANSLATABLE_FIXTURE_FIELDS = {
	"theme_name",
	"theme_type",
	"description",
	"login_page_title",
}


def extract_construction_theme_fixture(fileobj, *args, **kwargs):
	"""Extract user-facing strings from Construction Theme fixture records."""
	data = json.load(fileobj)
	if not isinstance(data, list):
		return

	for record in data:
		if not isinstance(record, dict):
			continue

		for fieldname in TRANSLATABLE_FIXTURE_FIELDS:
			value = record.get(fieldname)
			if value and isinstance(value, str):
				yield None, "_", value, [f"Value of {fieldname} in Construction Theme fixture"]
