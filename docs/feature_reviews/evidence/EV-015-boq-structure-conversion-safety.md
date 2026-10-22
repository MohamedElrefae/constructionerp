# EV-015: BOQ Structure Conversion Safety

Date: 2026-06-09

Tasks: `WP1.7`, `WP1.8`

## Implementation

Updated BOQ Structure conversion behavior.

Source changes:

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_structure_conversion.py`

Rules implemented:

- Group-to-leaf conversion is Draft-only.
- Empty group-to-leaf conversion creates a linked BOQ Item if missing.
- Group-to-leaf conversion remains blocked when the group has children.
- Leaf-to-group conversion is Draft-only.
- Leaf-to-group conversion runs the same linked item safety guard used by delete safety.
- Leaf-to-group conversion is blocked when the linked BOQ Item has stages or transaction references.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_boq_structure_conversion.run_boq_structure_conversion_smoke
```

Result:

```json
{
  "group_to_leaf": {
    "is_group": 0,
    "boq_item_created": true,
    "boq_item": "BOQI-BOQ-2026-0020-0021"
  },
  "leaf_to_group_block": {
    "blocked": true,
    "message": "Cannot delete BOQ Structure 5ffin79fup: linked BOQ Item BOQI-BOQ-2026-0020-0022 has stages.",
    "is_group_after": 0,
    "item_exists_after": true
  }
}
```

Cleanup and post-check:

```json
{
  "healthy": true,
  "structures_checked": 6,
  "items_checked": 2,
  "issue_count": 0
}
```

Conclusion:

Empty group-to-leaf conversion creates a BOQ Item, while leaf-to-group conversion is blocked when stages exist and leaves the linked BOQ Item intact.
