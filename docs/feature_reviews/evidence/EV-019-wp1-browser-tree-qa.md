# EV-019: WP1 Browser Tree/Form QA

Date: 2026-06-09

Task: `WP1.10`

## Scope

Completed browser-level QA for the existing BOQ dataset on `v16.localhost` after resetting the local test-site Administrator password.

Temporary Administrator password set for the local site:

```text
Admin@2026-temp
```

## Browser QA Method

Because the in-app browser session could open pages but could not type into the themed login form reliably, QA was completed with Playwright using the bundled Codex runtime and the local bench server.

Script used:

```text
/tmp/wp1_browser_qa.js
```

Screenshots were saved to:

```text
/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/wp1_browser_qa/
```

## Screenshots

- `boq-header-list.png`: BOQ Header list rendered with Arabic navigation and records.
- `boq-header-form.png`: BOQ Header `BOQ-2026-0006` rendered with status `Frozen`.
- `boq-structure-form.png`: BOQ Structure `rvetpphgb9` rendered with WBS code `01.01.01`.
- `boq-item-form.png`: BOQ Item `اسقف خرسانية` rendered and linked to BOQ Header/Structure.
- `boq-stage-form.png`: BOQ Item Stage `BOQ-STG-00008` rendered and linked to Project, BOQ Header, BOQ Structure, and BOQ Item.

## Captured UI Signals

The browser body text confirmed:

- Construction module navigation is visible.
- BOQ Header list is accessible.
- BOQ Header form is accessible.
- BOQ Structure form is accessible and displays WBS code.
- BOQ Item form is accessible and displays stage/action context.
- BOQ Item Stage form is accessible and shows scope links back to Project, BOQ Header, BOQ Structure, and BOQ Item.
- Arabic labels and Arabic data render in the Desk UI.

## Final Checks

WBS health:

```bash
bench --site v16.localhost execute construction.services.boq_wbs_health.run_wbs_health_check
```

Result:

```json
{
  "healthy": true,
  "summary": {
    "structures_checked": 6,
    "items_checked": 2,
    "issue_count": 0,
    "by_type": {},
    "by_severity": {}
  },
  "issues": []
}
```

Feature flags:

```bash
bench --site v16.localhost execute construction.services.feature_flags.get_flags
```

Result: all seven Improve Now rollout flags returned `false`.

## Review Conclusion

`WP1.10` is verified. WP1 has server smoke evidence, clean WBS health, and browser/form QA evidence. `G1` can be promoted because WBS health, delete safety, conversion safety, Draft-only resequence, and browser/manual tree QA are now verified.
