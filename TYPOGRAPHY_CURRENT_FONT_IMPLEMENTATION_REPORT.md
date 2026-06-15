# Typography Current Font Implementation Report

Date: 2026-06-16
Repo: `/home/mohamed/frappe-bench/apps/construction`
Current asset: `typography_settings.js?v=20`

## Purpose

This report records the current state of the Typography Settings implementation
after the Edge/Chromium font-rendering investigation.

The feature now applies typography settings correctly at the CSS/computed-style
level, but some local system fonts still do not visually render as expected in
the UI. The problem is no longer that the selected value is not being applied;
the problem is that local font names can be unavailable or substituted by the
browser/OS while DevTools still reports the requested `font-family` stack.

## Current Implementation Summary

Typography Settings currently:

- Loads as a raw Frappe asset:
  `/assets/construction/js/typography_settings.js?v=20`
- Generates a literal `#ct-typography-style` stylesheet instead of relying on
  CSS variables for primary `font-family` rules.
- Applies typography to root elements and visible descendants using inline
  `!important` fallback to override stale v9 inline styles.
- Loads Google Fonts for the fonts listed in `googleFontNames`.
- Uses a repaint trigger for Chromium/Edge.
- Stores the applied settings in `window.ctTypographySettings`.
- Exposes the loaded script version through:
  `window.ctTypography.assetVersion`.

## Font Availability Sections

### 1. Default / Local Fonts — Not Working Reliably

These fonts are local/system fonts. The browser may report them in
`getComputedStyle()`, but the actual rendered UI may still look different if the
font is missing, substituted, or rendered differently by the OS.

Current local/default options:

| Font Option | Current Stack | Current Status |
| --- | --- | --- |
| `System Default` | browser/system default | Works as fallback, not a distinct selected font |
| `Arial` | `Arial, Helvetica, sans-serif` | Computed style applies, visual rendering may not match expected Arial |
| `Helvetica` | `"Helvetica Neue", Helvetica, Arial, sans-serif` | Depends on local availability |
| `Tahoma` | `Tahoma, Arial, sans-serif` | Computed style applies, visual rendering may not match expected Tahoma |
| `Verdana` | `Verdana, Geneva, sans-serif` | Computed style applies, visual rendering may not match expected Verdana |
| `Trebuchet MS` | `"Trebuchet MS", Arial, sans-serif` | Depends on local availability |
| `Georgia` | `Georgia, "Times New Roman", serif` | Depends on local availability |
| `Times New Roman` | `"Times New Roman", Times, serif` | Computed style applies, but visual UI may not match expected Times New Roman |
| `Courier New` | `"Courier New", Courier, monospace` | Depends on local availability |

Observed example:

```javascript
console.log(getComputedStyle(document.querySelector(".sidebar-item-label")).fontFamily);
```

Can return:

```text
"Times New Roman", Times, serif
```

while the visible UI still does not look like the expected Times New Roman
rendering. This indicates browser/OS substitution or local font availability
behavior, not a failure of the CSS application path.

### 2. Google / Web Fonts — Rendering Well

These fonts are loaded by injecting:

```html
<link id="ct-google-fonts" rel="stylesheet" href="https://fonts.googleapis.com/css2?...">
```

When the network can reach Google Fonts, these render much more reliably because
the browser receives the actual web font files.

Current Google/web-loaded options:

| Font Option | Current Stack | Current Status |
| --- | --- | --- |
| `Inter` | `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | Expected to render well if Google Fonts loads |
| `Roboto` | `"Roboto", Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Open Sans` | `"Open Sans", Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Lato` | `"Lato", Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Montserrat` | `"Montserrat", Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Poppins` | `"Poppins", Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Noto Sans` | `"Noto Sans", Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Noto Sans Arabic` | `"Noto Sans Arabic", Tahoma, Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Cairo` | `"Cairo", Tahoma, Arial, sans-serif` | Verified visually reliable before the failed alias experiment |
| `Tajawal` | `"Tajawal", Tahoma, Arial, sans-serif` | Expected to render well if Google Fonts loads |
| `Almarai` | `"Almarai", Tahoma, Arial, sans-serif` | Expected to render well if Google Fonts loads |

Observed Cairo check:

```javascript
console.log(window.ctTypography?.assetVersion);
console.log(window.ctTypographySettings);
console.log(document.getElementById("ct-google-fonts")?.href);
console.log(getComputedStyle(document.querySelector(".sidebar-item-label")).fontFamily);
```

Expected:

```text
20
...Cairo...
https://fonts.googleapis.com/css2?family=Cairo...
"Cairo", Tahoma, Arial, sans-serif
```

## Important Notes from Debugging

### Computed Style Is Not Enough

DevTools can report the requested `font-family` stack even when the first font
is not actually installed or not actually used for glyph rendering. This is why
`Times New Roman` can appear in computed style while the UI still looks wrong.

### Cairo Works Because It Is Web Loaded

Cairo looked correct because the implementation loaded it from Google Fonts.
The browser had the actual font file available.

### The v19 Alias Experiment Was Reverted

An experiment attempted to make local fonts deterministic by mapping them to
Google-compatible substitutes:

- `Times New Roman` -> `Tinos`
- `Arial` -> `Arimo`
- `Courier New` -> `Cousine`

This made the problem worse in the current environment because the browser
failed to load the generated `.woff2` resources with `ERR_CONNECTION_CLOSED`.
That experiment was reverted in v20.

## Current Risk

The Typography Settings UI currently offers local fonts and Google fonts in the
same list, but they do not have the same reliability:

- Google/web fonts render predictably when network access works.
- Local/default fonts depend on the client operating system and browser font
  substitution behavior.

This can make the feature look broken even when the CSS application code is
working.

## Recommended Product Statement

Suggested statement for the current implementation:

> Typography Settings currently applies selected font settings correctly at the
> CSS level. Web-loaded fonts such as Cairo, Tajawal, Almarai, Noto Sans Arabic,
> Inter, and Roboto render reliably when Google Fonts is reachable. Local system
> fonts such as Times New Roman, Arial, Tahoma, Verdana, Georgia, and Courier New
> depend on the user's operating system and browser font availability, so their
> visual rendering may differ even when DevTools shows the selected font-family.

## Recommended UI Improvement

In a later pass, separate the font picker into two clear sections:

### Section A: Reliable Web Fonts

Recommended default choices:

- Cairo
- Tajawal
- Almarai
- Noto Sans Arabic
- Noto Sans
- Inter
- Roboto
- Open Sans
- Lato
- Montserrat
- Poppins

Suggested label:

```text
Web Fonts (recommended)
```

### Section B: Local System Fonts

Keep these available, but label them honestly:

- System Default
- Arial
- Helvetica
- Tahoma
- Verdana
- Trebuchet MS
- Georgia
- Times New Roman
- Courier New

Suggested label:

```text
Local System Fonts (depends on device)
```

## Future Completion Plan

### Option 1: Keep Current Behavior with Better Labels

Lowest-risk path:

1. Keep v20 behavior.
2. Change the UI labels/options so users understand which fonts are reliable web
   fonts and which are local system fonts.
3. Add help text below the field explaining that local fonts depend on the
   device.

### Option 2: Make All Fonts Web-Loaded

More complete but needs careful testing:

1. Replace local-only fonts with web-available equivalents.
2. Avoid pretending substitutes are exact matches.
3. For example:
   - Use `Tinos` as a Times-like font, but label it `Tinos`, not
     `Times New Roman`.
   - Use `Arimo` as an Arial-like font, but label it `Arimo`, not `Arial`.
4. Add the new font names to:
   - JS `fontStacks`
   - JS `googleFontNames`
   - server `allowed_fonts` in `theme_api.py`
   - server validation in `user_desk_theme.py`
5. Verify Google Fonts loading in the target deployment network.

### Option 3: Bundle Fonts Locally

Most reliable production path:

1. Choose approved fonts.
2. Store `.woff2` font files inside the app assets.
3. Define local `@font-face` rules.
4. Avoid external Google Fonts dependency.
5. Use only bundled fonts in the UI picker.

This is the best long-term option if the deployment environment blocks or
intermittently fails Google Fonts.

## Suggested Next Step

Do not spend more time trying to force Chromium repaint for local fonts. The
current evidence shows that CSS is applied correctly. The remaining problem is
font availability/rendering reliability.

Recommended next work package:

1. Update the font picker UI to separate web fonts from local fonts.
2. Add explanatory help text.
3. Prefer Cairo/Tajawal/Almarai/Noto Sans Arabic for Arabic-heavy UI.
4. Decide later whether to bundle fonts locally for production reliability.
