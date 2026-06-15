# Handoff: Typography Settings — Microsoft Edge Font Rendering Fix

**Date:** 2026-06-14  
**Status:** Implementation complete per plan; awaiting manual verification in Edge  
**Handoff to:** Next AI Agent (for verification / follow-up)

---

## Summary

The Typography Settings feature (`typography_settings.js`) was refactored to resolve the Microsoft Edge bug where font-family changes showed the correct computed style but did not render visually.

**Root cause addressed:** CSS custom properties with `font-family` values containing quotes fail to trigger a repaint in Chromium-based Edge. The fix replaces CSS-variable-based `font-family` declarations with a dynamically generated `<style>` tag containing literal font stacks.

---

## Files Changed

| File | Change |
|------|--------|
| `construction/public/js/typography_settings.js` | v9 → v16; dynamic static stylesheet + Google Fonts loader |
| `construction/hooks.py` | Bumped `typography_settings.js` query param to `?v=16` |

---

## What Was Implemented

### 1. Proper font stack quotes (`fontStacks`, js:26-48)

Multi-word font names are now quoted so they render as valid CSS:

```js
"Times New Roman": '"Times New Roman", Times, serif',
"Noto Sans Arabic": '"Noto Sans Arabic", Tahoma, Arial, sans-serif',
```

### 2. Dynamic Google Fonts loader (`loadNeededGoogleFonts`, js:113-143)

- Scans the six component font families.
- For every selected Google Font, injects/updates a single `<link id="ct-google-fonts">` to `fonts.googleapis.com/css2`.
- Removes the link when no Google Fonts are selected.
- Handles `Inherit` by resolving to the desk font first.

Covered Google Fonts: Inter, Cairo, Tajawal, Noto Sans Arabic, Almarai, Roboto, Open Sans, Lato, Montserrat, Poppins, Noto Sans.

### 3. Dynamic static stylesheet (`ensureStyleTag(settings)`, js:145-312)

- Accepts current settings.
- Resolves each component font (desk, sidebar, navbar, form, list, menu), falling back from `Inherit` to desk.
- Rewrites `#ct-typography-style` with literal values such as:

```css
html.ct-enterprise body {
  font-family: "Times New Roman", Times, serif !important;
  font-size: 14px !important;
  font-weight: 400 !important;
}
```

- Re-appends the `<style>` tag to the end of `<head>` so it wins the cascade.

### 4. `applyTypography(settings)` updated (js:332-367)

Calls in order:
1. `normalize(settings)`
2. `loadNeededGoogleFonts(settings)`
3. `ensureStyleTag(settings)`
4. Sets legacy CSS variables (`--ct-*-font-family`, `--ct-*-font-size`, `--ct-*-font-weight`) for backward compatibility.
5. `applyRootTypographyStyles(settings)` — keeps inline `!important` styles on `<html>` / `<body>` as a safety net.
6. Chromium repaint invalidation via `ct-typography-changing` class.

### 5. Removed legacy inline-typography DOM observer

The previous `applyInlineTypography`, DOM `MutationObserver`, and `setInlineFont` machinery were removed because the static stylesheet now handles all elements via CSS rules.

### 6. Version bump

`hooks.py`: `typography_settings.js?v=9` → `?v=16`.

---

## Verification Checklist (to be run by next agent / user)

### Automated
- [ ] `node --check construction/public/js/typography_settings.js` passes ✅ (already verified)
- [ ] `python3 -m py_compile construction/hooks.py` passes
- [ ] `bench build --app construction` completes without errors

### Manual — Microsoft Edge
- [ ] Hard-refresh page (`Ctrl + Shift + R`).
- [ ] Open Typography Settings (sidebar Aa button or user menu).
- [ ] Change **Font Family** to `Times New Roman` → UI should repaint visibly.
- [ ] Change **Font Family** to `Tahoma` → UI should repaint visibly.
- [ ] Change **Font Family** to `Cairo` → a Google Fonts `<link>` should appear in `<head>`, and UI should use Cairo after the font loads.
- [ ] Change **Desk Font Size** → UI size should update (regression check).
- [ ] Click **Cancel** or close dialog without saving → UI should revert to last saved settings on next reload.
- [ ] Click **Save** → settings persist across reloads.
- [ ] Check that opening the dialog does **not** collapse the sidebar.

### Diagnostic commands (if it still fails)

```js
// Should show the literal font stack, no var()
console.log(document.getElementById('ct-typography-style').textContent.match(/font-family:[^;]+;/g));

// Should show the selected font stack
console.log(getComputedStyle(document.body).fontFamily);

// Should exist when a Google Font is selected
console.log(document.getElementById('ct-google-fonts')?.href);
```

---

## Known Risks / Watch Items

1. **Google Fonts blocked by ad blocker / CSP** — If `fonts.googleapis.com` is blocked, Google Fonts will silently fall back to the next font in the stack (e.g., Tahoma, Arial). This is acceptable but may surprise users expecting Cairo/Inter on Linux.
2. **Dynamic `<style>` rewrite cost** — `ensureStyleTag` regenerates ~40 CSS rules on every `change input` event. The cost is low for modern browsers, but on very large DOMs the re-append to `<head>` could trigger style recalculation. If performance issues appear, throttle the `change input` handler.
3. **Frappe late-injected styles** — The `startStyleOrderObserver` keeps `#ct-typography-style` as the last child of `<head>`. Verify this still works after the refactor.

---

## If It Still Fails in Edge

If font-family still does not visually update in Edge after this refactor, the issue is not CSS variables. Next things to investigate:

1. **Force-reflow diagnostic** in `applyTypography`:
   ```js
   document.body.style.display = 'none';
   void document.body.offsetHeight;
   document.body.style.display = '';
   ```
   If this fixes the rendering, it confirms a Chromium repaint bug and we should keep a less intrusive forced-reflow mechanism.

2. **External script interference** — `inject_main.js` / `assets.js` clear localStorage and may manipulate styles. Search for any script that overrides `font-family` on `html` or `body`.

3. **Frappe dialog modal styles** — Check whether the modal wrapper receives an inline `font-family` from Frappe that overrides our stylesheet.

---

## Key Code Locations

| Function | File:Line | Purpose |
|----------|-----------|---------|
| `fontStacks` | `typography_settings.js:26` | Font name → CSS stack mapping |
| `googleFontNames` | `typography_settings.js:56` | Set of fonts loaded from Google |
| `loadNeededGoogleFonts` | `typography_settings.js:113` | Injects Google Fonts `<link>` |
| `ensureStyleTag` | `typography_settings.js:145` | Generates static CSS stylesheet |
| `applyTypography` | `typography_settings.js:332` | Main application entry point |
| `applyRootTypographyStyles` | `typography_settings.js:371` | Inline fallback on `<html>`/`<body>` |
| `closeOpenMenus` | `typography_settings.js:413` | Closes dropdowns before dialog |
