# BOQ Structure Review

## Scope

This report reviews `BOQ Structure` as the WBS tree layer that organizes BOQ scope and automatically creates/deletes BOQ Item rows for leaf nodes.

## Main Files

- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.py](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.json](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.json)
- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure_tree.js](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure_tree.js)
- [/home/mohamed/frappe-bench/apps/construction/construction/api/boq_api.py](/home/mohamed/frappe-bench/apps/construction/construction/api/boq_api.py)

## Implementation Overview

`BOQ Structure` extends Frappe `NestedSet` and uses `parent_structure` as the nested-set parent field. It is configured as a tree DocType with `lft`, `rgt`, `old_parent`, and sorted by `lft`.

On insert, the controller generates a hierarchical `wbs_code` based on sibling count:

- Root nodes use two digits, such as `01`.
- Group child nodes use two digits after the parent, such as `01.02`.
- Leaf child nodes use three digits after the parent, such as `01.001`.

When a non-group node is inserted, the controller automatically creates a linked `BOQ Item`. When a non-group node is deleted, it force-deletes the linked BOQ Item.

The controller blocks structure changes when the parent BOQ Header is `Frozen` or `Locked`.

The tree view adds project and BOQ Header filters, syncs project from scope context, clears incompatible BOQ selections when scope changes, and adds navigation/export buttons.

## Strengths

- NestedSet is the right Frappe primitive for WBS hierarchy.
- Automatic BOQ Item creation gives a clean one-leaf-one-item relationship.
- Status enforcement prevents structural changes after commercial freeze.
- The tree view includes project filtering and scope synchronization, which helps prevent users from editing the wrong BOQ.
- The DocType has role-based permissions with read-only roles separated from manager/owner roles.

## Risks and Gaps

- `generate_wbs_code()` is count-based. Concurrent inserts under the same parent can produce duplicate or unstable WBS codes unless the database schema enforces uniqueness per BOQ and parent.
- WBS codes are generated only before insert. Moving nodes, converting group/ledger status, or deleting siblings can leave gaps or codes that no longer reflect hierarchy.
- `convert_ledger_to_group()` sets `is_group = 1` but does not delete or validate the existing linked BOQ Item. That can leave a BOQ Item attached to a now-group node.
- `convert_group_to_ledger()` creates no BOQ Item after converting a group to a leaf. It saves `is_group = 0`, but item creation only happens in `after_insert`.
- `delete_boq_item()` force-deletes with ignored permissions. That is operationally convenient, but risky if transaction rows already reference the BOQ Item.
- The tree view calls export endpoints directly but does not expose export errors as thoroughly as the form export menu.

## Review Opinion

The WBS foundation is strong, but the group/leaf conversion methods need attention before relying on them in production. Insert/delete lifecycle works for simple creation, but conversion and concurrent insertion are the weak points.

## Recommended Next Steps

1. Add unique validation for `wbs_code` within each `boq_header`.
2. Rework group/leaf conversion so converting to leaf creates a BOQ Item and converting to group only succeeds if no item transactions exist.
3. Add transaction-reference checks before force-deleting linked BOQ Items.
4. Decide whether WBS codes are immutable identifiers or structural display codes. If structural, add a controlled recode/resequence operation.
5. Add tests for concurrent-ish sibling creation, group-to-leaf conversion, leaf-to-group conversion, and deletion with linked transactions.
