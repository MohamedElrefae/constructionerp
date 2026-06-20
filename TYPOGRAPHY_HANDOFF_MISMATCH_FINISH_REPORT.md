# Typography Handoff Mismatch Finish Report

Date: 2026-06-15
Repo: `/home/mohamed/frappe-bench/apps/construction`
Branch: `feat/scope-context-standardization`

## Objective

Finish P1 item 1: resolve the mismatch between `AGENTS_HANDOFF.md` and the
actual typography source code, then leave the repository in a truthful,
verifiable state.

## Verdict

The mismatch is real. `AGENTS_HANDOFF.md` claims a v16 Microsoft Edge
font-rendering fix is implemented, but the live source tree still matches the
older v9 behavior.

Committing the restored tree as-is would ship a false completion signal.

## Three-Marker Audit

| Marker | Actual Code | Handoff Claim |
| --- | --- | --- |
| `construction/hooks.py` | `typography_settings.js?v=9` | `?v=16` |
| `ensureStyleTag()` | CSS variables such as `var(--ct-desk-font-family, inherit)` | Literal font stacks such as `"Times New Roman", Times, serif` |
| Google Fonts loader | Not present | `loadNeededGoogleFonts()` and `<link id="ct-google-fonts">` |
| DOM typography observer | Present in v9 flow | Removed in v16 flow |

## Risk

If committed unchanged, QA will believe the Edge typography bug is already
fixed. In reality, the browser still loads the v9 raw asset and the generated
CSS still depends on custom properties for `font-family`, which is the behavior
the handoff says was replaced.

## Decision Required

Choose one path before committing the restored work.

### Option A: Ship the Edge Typography Fix

Use this if the Microsoft Edge font-family repaint bug is in scope for this
branch.

Completion means:

- `typography_settings.js` generates literal font stacks for primary typography
  CSS.
- `hooks.py` uses the final cache-buster version.
- Google Fonts are loaded when selected.
- Legacy inline observer code is removed or no longer part of the main flow.
- Automated checks pass.
- Edge manual QA is completed or clearly delegated with an honest status.
- `AGENTS_HANDOFF.md` is updated into a truthful implementation/verification
  report.

### Option B: Do Not Ship the Edge Typography Fix in This Branch

Use this if the handoff was restored accidentally or belongs to another branch.

Completion means:

- Remove `AGENTS_HANDOFF.md`, or rewrite it to say the typography fix is not
  included in this branch.
- Leave `typography_settings.js` and `hooks.py` unchanged.
- Track the Edge fix separately.

## Recommendation

Option A is recommended if this branch is intended to finish the restored work
fully. The v16 design is directionally correct: literal CSS font stacks are a
reasonable fix for Chromium/Edge repaint problems involving `font-family` custom
properties.

If Microsoft Edge manual verification is unavailable, either mark that
verification as pending or choose Option B. Do not keep the current handoff claim
without matching code.

## Option A: Required Gaps to Close

### Gap 1: `fontStacks` and server `allowed_fonts` can diverge

The client font list in `typography_settings.js` and server allowlists in
`construction/api/theme_api.py` and
`construction/construction/doctype/user_desk_theme/user_desk_theme.py` are
maintained independently.

Required finish:

- Add comments at each location linking the lists.
- Prefer a later follow-up to expose the server font allowlist through boot or
  add a lint check.
- Before shipping, verify every JS `fontStacks` key is accepted by server
  normalization.

### Gap 2: Google Font names must not drift from `fontStacks`

The Google Fonts subset must stay aligned with `fontStacks`.

Required finish:

- Add a `googleFontNames` set only for fonts that also exist in `fontStacks`.
- Keep the set near `fontStacks` with a maintenance comment.
- Consider a JS test/lint that fails if `googleFontNames` contains unknown
  fonts.

### Gap 3: `ensureStyleTag(settings)` needs a precise output contract

The current `ensureStyleTag()` has no arguments and emits a static CSS block
with `var()`.

Required finish:

- Change it to `ensureStyleTag(settings)`.
- Keep the existing selector coverage from v9 unless deliberately reduced.
- Resolve `Inherit` component fonts to the desk font immediately.
- Generate rules for all six components: desk, sidebar, navbar, form, list,
  menu.
- Generate literal values for family, size, and weight.

### Gap 4: Avoid style-order observer append loops

`ensureStyleTag(settings)` will rewrite the style tag repeatedly during dialog
changes. The order observer also re-appends the style node.

Required finish:

- Ensure regeneration does not create a micro-loop.
- Either skip appending when the style is already the last child of `<head>`, or
  temporarily pause observer-driven re-appends during regeneration.

### Gap 5: Define the repaint invalidation mechanism

The handoff mentions a `ct-typography-changing` class but does not design it.

Required finish:

- Add/remove `ct-typography-changing` on `document.documentElement`.
- Force reflow with `void document.documentElement.offsetHeight`.
- Add a harmless CSS rule if needed so the class triggers style recalculation.

### Gap 6: Implement `closeOpenMenus()`

The handoff references `closeOpenMenus()`, but v9 does not define it.

Required finish:

- Add a helper that closes open dropdown menus before the dialog opens.
- Use a minimal DOM approach, for example removing `.show` from open
  `.dropdown-menu.show` elements.

### Gap 7: Treat legacy CSS variables as compatibility only

The repo currently has no clear consumers for `--ct-*-font-*` CSS variables.

Required finish:

- Do not rely on CSS variables for primary `font-family` rules.
- Either keep setting them only as compatibility output or remove them if no
  consumers are confirmed.
- Document the choice.

### Gap 8: Check co-loaded scripts for font overrides

Typography loads between `theme_loader_v24.js` and `components/index.js`.

Required finish:

- Search `theme_loader_v24.js` and the component bundle source for
  `font-family` writes or injected typography styles.
- Confirm the typography style-order strategy wins without fighting other
  scripts.

### Gap 9: Remove legacy inline typography observer scope

The v9 observer infrastructure should be removed if the static literal
stylesheet becomes the primary mechanism.

Remove or retire:

- `inlineApplyTimer`
- `typographyObservedRoots`
- `typographyObservedRootList`
- `typographyRootObservers`
- `domObserverStarted`
- `applyInlineTypography`
- `startDomTypographyObserver`
- `observeTypographyRoot`
- `discoverTypographyShadowRoots`
- `registerTypographyShadowRoots`
- `shouldSkipInlineTypography`
- `setInlineFont`

### Gap 10: Specify Google Fonts URL construction

Google Fonts CSS2 URLs must include family names and weights.

Required finish:

- Use URL-encoded family names, replacing spaces with `+`.
- Include allowed weights: `wght@300;400;500;600;700`.
- Use multiple `family=` params.
- Add `display=swap`.
- Example:

```text
https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap
```

### Gap 11: Resolve `Inherit` before loading Google Fonts

If a component font is `Inherit`, the loader must inspect the desk font.

Required finish:

- If desk is `Cairo` and sidebar is `Inherit`, load Cairo.
- If desk is `System Default`, do not load a Google Font for inherited
  components.

### Gap 12: Document Google Fonts loading flash

Google Fonts load asynchronously, so a fallback font may render briefly before
the selected web font appears.

Required finish:

- Use `display=swap`.
- Document the flash/fallback behavior as an accepted limitation.

### Gap 13: Document `node --check` limits

`node --check` only validates syntax. It does not validate Frappe globals such
as `frappe`, `__`, or `$`.

Required finish:

- Keep `node --check`, but document it as a syntax-only gate.
- Do browser/manual testing for runtime behavior.

### Gap 14: Build and clear cache are both required

`typography_settings.js` is loaded as a raw asset. Frappe must copy it into
`sites/assets`.

Required finish:

- Run `bench build --app construction`.
- Run `bench clear-cache`.
- Hard-refresh the browser.

### Gap 15: Handle double apply on save

The dialog applies settings immediately, then applies server-normalized settings
again after save succeeds.

Required finish:

- Ensure `applyTypography(settings)` is idempotent.
- Rewriting the same style twice should not flicker or duplicate DOM nodes.

### Gap 16: Add at least minimal tests or checks

Required finish:

- Add or run a JS check that verifies generated `font-family` CSS contains no
  `var()`.
- Add or run a Python check that server typography normalization accepts every
  client font name.
- Prefer adding these to the project test suite if time allows.

## Phased Implementation Plan for Option A

### Phase 0: Safeguard

```bash
cd /home/mohamed/frappe-bench/apps/construction
git checkout -b feat/edge-typography-fix-v16
cp construction/public/js/typography_settings.js construction/public/js/typography_settings.js.v9-backup
```

If staying on the current branch, skip branch creation but keep the backup until
verification is complete.

### Phase 1: Rewrite `typography_settings.js`

Code tasks:

1. Add `googleFontNames` near `fontStacks`.
2. Add `closeOpenMenus()`.
3. Add `resolveFontFamily(settings, component)`.
4. Add `loadNeededGoogleFonts(settings)`.
5. Rewrite `ensureStyleTag(settings)` to emit literal CSS.
6. Preserve existing v9 selector coverage unless deliberately reduced.
7. Rewrite `applyTypography(settings)` flow:
   - normalize settings
   - load needed Google Fonts
   - regenerate literal stylesheet
   - optionally set legacy variables as compatibility output
   - apply root inline fallback
   - trigger repaint invalidation
8. Remove or retire the legacy inline observer functions and variables listed
   in Gap 9.

Keep unchanged unless needed:

- `fontStacks`, except maintenance comments
- `fontOptions`
- `componentFontOptions`
- `deskFontOptions`
- `normalize()`
- `clamp()`
- `normalizeWeight()`
- `startStyleOrderObserver()`, except loop prevention
- `applyRootTypographyStyles()`
- dialog construction and preview functions
- settings load/save flow
- `window.ctTypography`
- `window.ctShowTypographySettings`

### Phase 2: Bump Cache Buster

Change `construction/hooks.py`:

```python
"/assets/construction/js/typography_settings.js?v=9",
```

to:

```python
"/assets/construction/js/typography_settings.js?v=16",
```

or a later version if more iterations are made.

### Phase 3: Automated Verification

Run:

```bash
node --check construction/public/js/typography_settings.js
python3 -m py_compile construction/hooks.py
bench build --app construction
bench clear-cache
```

Also run targeted checks:

- Verify generated typography CSS has literal `font-family` values.
- Verify `font-family:` declarations in the generated style do not contain
  `var(`.
- Verify all client font names pass server normalization.

### Phase 4: Co-loaded Script Audit

Search for competing font writes:

```bash
rg "font-family|fontFamily|--ct-.*font" construction/public/js/theme_loader_v24.js construction/public/js/components construction/public/js
```

Confirm any competing rules are either unrelated or weaker than
`#ct-typography-style`.

### Phase 5: Update Documentation

Rewrite `AGENTS_HANDOFF.md` so it becomes a truthful implementation report.

Required contents:

- actual files changed
- final cache-buster version
- automated commands run
- Edge manual QA status
- known limitations, especially Google Fonts fallback/flash

### Phase 6: Microsoft Edge Manual QA

Manual checks:

- Hard-refresh the desk page.
- Open Typography Settings from sidebar/user menu.
- Change Desk Font Family to `Times New Roman`; UI visibly changes.
- Change Desk Font Family to `Tahoma`; UI visibly changes.
- Change Desk Font Family to `Cairo`; `#ct-google-fonts` appears and UI uses
  Cairo after load.
- Change Desk Font Size; UI size changes.
- Cancel without saving; reload returns to previously saved settings.
- Save settings; reload preserves saved typography.
- Opening the dialog does not collapse or break the sidebar.

Browser diagnostics:

```javascript
console.log(document.getElementById("ct-typography-style")?.textContent.match(/font-family:[^;]+;/g));
console.log(getComputedStyle(document.body).fontFamily);
console.log(document.getElementById("ct-google-fonts")?.href);
```

Expected:

- `#ct-typography-style` contains literal font stacks.
- `getComputedStyle(document.body).fontFamily` reflects the selected font.
- `#ct-google-fonts` exists when a Google Font is selected.

## Completion Definition

This P1 item is complete when one of the following is true:

1. Option A is implemented, cache-busted, built, verified, and documented.
2. Option B is chosen and the stale handoff claim is removed or corrected.

Do not commit a state where `AGENTS_HANDOFF.md` claims v16 is implemented while
the source tree still loads v9.
