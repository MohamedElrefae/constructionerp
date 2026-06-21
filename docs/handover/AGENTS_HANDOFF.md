# Implementation Report: Typography Settings Current State

**Date:** 2026-06-16
**Branch:** `feat/edge-typography-fix-v16`
**Status:** Finished for now; ready to move to next phase.

## Summary

The Typography Settings implementation has been moved from the stale v9/v16
handoff state to the current v21 implementation.

The code now applies typography settings correctly at the CSS/computed-style
level, uses literal font stacks instead of CSS-variable font-family rules, and
separates font choices into two sections in the UI:

- **Web Fonts (recommended)** — expected to render reliably when Google Fonts is
  reachable.
- **Local System Fonts (depends on device)** — retained, but explicitly labeled
  because rendering depends on the client OS/browser font availability.

## Files Changed

| File | Change |
| --- | --- |
| `construction/public/js/typography_settings.js` | Current implementation, asset marker `21`, literal CSS generation, inline fallback, sectioned font picker |
| `construction/hooks.py` | Cache buster changed from `?v=9` to `?v=21` |
| `TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md` | Detailed current-state report and future completion plan |

## What Is Finished

### 1. Stale Handoff Mismatch Resolved

The old handoff claimed a v16 Edge fix while the repo still loaded v9. That is
no longer true.

Current hook:

```python
"/assets/construction/js/typography_settings.js?v=21",
```

Current runtime marker:

```javascript
window.ctTypography.assetVersion === "21"
```

### 2. Literal Typography Stylesheet

`typography_settings.js` now generates `#ct-typography-style` with literal font
stacks, for example:

```css
font-family: "Cairo", Tahoma, Arial, sans-serif !important;
```

The primary font-family rules no longer depend on CSS custom properties such as
`var(--ct-desk-font-family)`.

### 3. Inline Fallback for Old v9 Residue

The old v9 implementation wrote inline `font-family: ... !important` styles to
many descendants. The current implementation updates descendant inline fallback
styles too, so stale v9 inline values no longer block the selected font.

### 4. Web Font Loading Restored

Google Fonts loading is active for the supported web font set:

- Inter
- Cairo
- Tajawal
- Noto Sans Arabic
- Almarai
- Roboto
- Open Sans
- Lato
- Montserrat
- Poppins
- Noto Sans

The failed v19 alias experiment (`Tinos`, `Arimo`, `Cousine`) was reverted
because it caused font-file load failures in this environment.

### 5. Font Picker Split Into Two Sections

The picker now separates fonts into disabled section headers:

- `Web Fonts (recommended)`
- `Local System Fonts (depends on device)`

The headings are disabled options and cannot be saved as font values.

## Known Current Limitation

Local system fonts are not visually reliable across client machines.

Examples:

- Times New Roman
- Arial
- Tahoma
- Verdana
- Georgia
- Courier New

DevTools can show the requested computed style, such as:

```text
"Times New Roman", Times, serif
```

while the actual UI rendering still looks different because the browser/OS is
substituting or rendering a local font differently.

Cairo and the other web-loaded fonts are the reliable path when Google Fonts is
reachable.

## Verification Performed

Automated checks passed:

```bash
node --check construction/public/js/typography_settings.js
python3 -m py_compile construction/hooks.py
bench build --app construction
bench clear-cache
```

The served asset was verified to contain:

- `assetVersion = "21"`
- section labels
- current Google Fonts loader
- v20/v21 local-font behavior without the failed alias fallback

## Runtime Diagnostics

Use this in the browser:

```javascript
console.log(window.ctTypography?.assetVersion);
console.log(window.ctTypographySettings);
console.log(document.getElementById("ct-google-fonts")?.href);
console.log(getComputedStyle(document.querySelector(".sidebar-item-label")).fontFamily);
```

Expected:

- Asset version is `21`.
- Web fonts such as Cairo appear in `#ct-google-fonts`.
- Computed style reflects the selected font stack.

## Final Product Statement

Typography Settings currently applies selected font settings correctly at the CSS
level. Web-loaded fonts such as Cairo, Tajawal, Almarai, Noto Sans Arabic,
Inter, and Roboto render reliably when Google Fonts is reachable. Local system
fonts such as Times New Roman, Arial, Tahoma, Verdana, Georgia, and Courier New
depend on the user's operating system and browser font availability, so their
visual rendering may differ even when DevTools shows the selected font-family.

## Future Work

Do not continue chasing Chromium repaint for local fonts. The remaining issue is
font availability/rendering reliability, not CSS application.

Recommended future options:

1. Keep current v21 behavior with clear labels.
2. Replace local-only fonts with clearly named web equivalents.
3. Bundle approved `.woff2` fonts locally and remove reliance on Google Fonts.

See `TYPOGRAPHY_CURRENT_FONT_IMPLEMENTATION_REPORT.md` for the detailed
follow-up plan.
