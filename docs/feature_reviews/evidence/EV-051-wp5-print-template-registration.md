# EV-051 - WP5 Print Templates and Registration

Date: 2026-06-09

Tasks: `WP5.5`, `WP5.6`

## Implementation

- Updated BOQ PDF templates for Arabic-aware `dir="rtl"` rendering.
- Added Arabic-capable font fallbacks: `Noto Naskh Arabic`, `Noto Kufi Arabic`, `Amiri`, `Arial`, `sans-serif`.
- Added idempotent `setup_boq_print_formats()` to `construction.install.setup_boq_integration`.
- Synced `BOQ Print Format` into `v16.localhost`.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.install.setup_boq_print_formats
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_print_format_registration_smoke
```

Result:

```json
{
  "success": true,
  "print_format": {
    "name": "BOQ Print Format",
    "print_format_type": "Jinja",
    "custom_format": 1
  },
  "templates": ["boq_print_format.html", "boq_header_print.html"],
  "rtl_rendered": true
}
```

SQL verification:

```sql
select name, doc_type, disabled, print_format_type, custom_format
from `tabPrint Format`
where name = 'BOQ Print Format';
```

Result: `BOQ Print Format`, `BOQ Header`, `disabled=0`, `Jinja`, `custom_format=1`.

## Status

`WP5.5` and `WP5.6` can move to `VER`.
