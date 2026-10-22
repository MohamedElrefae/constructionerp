# EV-014: BOQ Structure Delete Safety

Date: 2026-06-09

Tasks: `WP1.5`, `WP1.6`

## Implementation

Added a leaf delete safety guard before linked BOQ Item deletion.

Source changes:

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_lifecycle.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_structure_delete_safety.py`

Important Frappe v16 note:

Frappe v16 `delete_doc` calls `on_trash` before built-in link validation. There is no earlier controller `before_delete` call in this path. Therefore, the safety guard is placed as the first operation inside `BOQStructure.on_trash`, before `delete_boq_item()`.

## Safety Rules

Deleting a leaf BOQ Structure is blocked when its linked BOQ Item has:

- Any BOQ Item Stage.
- Any transaction child row reference through `boq_item`.
- Any transaction child row reference through `boq_structure`.

The linked BOQ Item deletion no longer uses `force=True`.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_boq_structure_delete_safety.run_boq_structure_delete_safety_smoke
```

Result:

```json
{
  "material_request": "MAT-MR-2026-00003",
  "boq_structure": "rvetpphgb9",
  "boq_item": "اسقف خرسانية",
  "blocked": true,
  "message": "Cannot delete BOQ Structure rvetpphgb9: linked BOQ Item اسقف خرسانية has stages.",
  "structure_exists_before": true,
  "item_exists_before": true,
  "structure_exists_after": true,
  "item_exists_after": true
}
```

Source check:

```text
frappe.delete_doc("BOQ Item", item_name, ignore_permissions=True)
```

No `force=True` remains in the linked BOQ Item delete path.

Post-check health:

```json
{
  "healthy": true,
  "summary": {
    "structures_checked": 6,
    "items_checked": 2,
    "issue_count": 0
  }
}
```

Conclusion:

Referenced leaf deletion is blocked before linked BOQ Item deletion, the linked item remains intact, and unsafe forced deletion has been removed from this path.
