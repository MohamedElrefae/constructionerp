# Vite UI, List Views, and Form Config Review

## Scope

This report reviews the feature referred to as "Vite UI" for list/form controls and form configuration.

Important finding: there is no standalone Vite application source tree, `vite.config`, Vue/React component tree, or Vite package setup in the construction app. The implementation is Frappe Desk JavaScript and CSS assets named `vite_*` and `vfc_*`.

## Main Files

- [/home/mohamed/frappe-bench/apps/construction/construction/hooks.py](/home/mohamed/frappe-bench/apps/construction/construction/hooks.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/public/js/vite_layout_controls.js](/home/mohamed/frappe-bench/apps/construction/construction/public/js/vite_layout_controls.js)
- [/home/mohamed/frappe-bench/apps/construction/construction/public/js/vfc_layout_engine.js](/home/mohamed/frappe-bench/apps/construction/construction/public/js/vfc_layout_engine.js)
- [/home/mohamed/frappe-bench/apps/construction/construction/construction/api/layout_api.py](/home/mohamed/frappe-bench/apps/construction/construction/construction/api/layout_api.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/form_layout_profile/form_layout_profile.py](/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/form_layout_profile/form_layout_profile.py)
- [/home/mohamed/frappe-bench/apps/construction/construction/public/css/vite_form_override.css](/home/mohamed/frappe-bench/apps/construction/construction/public/css/vite_form_override.css)
- [/home/mohamed/frappe-bench/apps/construction/construction/public/css/vite_list_override.css](/home/mohamed/frappe-bench/apps/construction/construction/public/css/vite_list_override.css)
- [/home/mohamed/frappe-bench/apps/construction/construction/public/css/vfc_sections.css](/home/mohamed/frappe-bench/apps/construction/construction/public/css/vfc_sections.css)

## Implementation Overview

The hook layer loads Vite/VFC CSS after the main theme CSS so it wins the cascade. It then loads `vite_layout_controls.js` and `vfc_layout_engine.js` late in `app_include_js`.

`vite_layout_controls.js` globally attaches to every Frappe form through `frappe.ui.form.on("*")`. It injects a `Form Config` button, builds a draggable/resizable panel, and supports:

- Column density persisted in localStorage.
- Field visibility persisted in `frappe.model.user_settings`.
- Presets for BOQ Header, BOQ Item, and BOQ Item Stage.
- A sections editor, with System Manager-only save behavior.

`vfc_layout_engine.js` reads active layout profiles from the server, re-parents native Frappe field wrappers into custom section containers, and falls back to native rendering when no profile exists. It blocks known system DocTypes and has additional handling for tabbed forms.

`layout_api.py` resolves profiles in priority order:

1. User-specific profile.
2. Role-specific profile.
3. Default profile.
4. No profile.

The `Form Layout Profile` DocType validates section JSON, blocks duplicate field assignments, warns on unknown fields, prevents hiding required fields in shared profiles, and enforces a single default enabled profile per DocType.

Live database review showed seeded default profiles for `BOQ Header`, `BOQ Structure`, `BOQ Item`, `BOQ Item Stage`, `Project`, and `User Scope Context`.

## Strengths

- The form config feature is generic and not hard-coded only to BOQ forms.
- The profile resolver supports personal, role, and default layouts.
- No-profile fallback is an important safety feature.
- The profile DocType has meaningful server-side validation.
- System Manager restrictions exist for profile mutation.
- The layout engine attempts to preserve native Frappe controls, events, permissions, dependencies, and child tables by moving wrappers rather than rebuilding fields.
- CSS is loaded after the main theme by design, which makes the custom controls visually consistent.

## Risks and Gaps

- The name "Vite UI" is misleading. This is not Vite-built UI; it is injected Frappe Desk UI. That matters for future maintenance and onboarding.
- The global `frappe.ui.form.on("*")` attach means every form pays some runtime cost and carries regression risk.
- The layout engine mutates DOM placement of native field wrappers. That is powerful but fragile against Frappe version changes.
- There is heavy console logging in both VFC scripts. This will be noisy in production and can mask real browser errors.
- `vite_layout_controls.js` loads SortableJS from a CDN for section editing. In restricted or offline environments, this can fail.
- The panel uses inline HTML and inline event handlers. This is workable in Frappe scripts but increases XSS/escaping discipline requirements.
- Field visibility is user-setting based, while layout profiles are server-profile based, and density is browser-local. The persistence model is mixed and needs clear user documentation.
- The comments say the engine skips tabbed forms, but current code includes tab-aware rendering paths. The behavior and documentation are not fully aligned.

## Review Opinion

The feature is ambitious and useful, especially for tailoring dense ERP forms. It should be treated as a platform-level extension, not just a BOQ feature. Because it hooks every form and re-parents DOM, it needs a tighter stability strategy than ordinary client scripts.

## Recommended Next Steps

1. Rename the feature in documentation from "Vite UI" to "VFC Form Config" or "Construction Form Config" unless a true Vite app will be introduced.
2. Gate global attach by app/module or a settings flag, so rollout can be controlled.
3. Bundle SortableJS locally instead of loading from CDN.
4. Reduce console logging to a debug flag.
5. Add browser regression tests for: no profile fallback, profile rendering, tabbed form behavior, hidden required field protection, and field dependency behavior.
6. Document persistence clearly: density is browser-local, visibility/presets are user settings, layout profiles are server records.
