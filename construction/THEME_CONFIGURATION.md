# Construction ERP — Theme Configuration Guide

## Overview

The Construction ERP app provides 4 themes built on top of Frappe's native dark/light mode system. Two are standard Frappe themes (Light, Dark) and two are custom construction-branded themes (Construction Light, Construction Dark) with green accent colors matching the construction industry identity.

## Theme Matrix

| Theme | Mode | Accent | Navbar | Sidebar | Body | Emoji |
|---|---|---|---|---|---|---|
| **Light** | light | Blue `#2076FF` | `#FFFFFF` | `#F8FAFC` | `#F5F6FA` | ☀️ |
| **Dark** | dark | Blue `#2076FF` | `#23272F` | `#22262A` | `#181A20` | 🌙 |
| **Construction Light** | light | Green `#2E7D32` | `#F0FDF4` | `#F0FDF4` | `#F0FDF4` | 🏗️ |
| **Construction Dark** | dark | Green `#4CAF50` | `#1A3A1E` | `#0D1F12` | `#111A13` | 🏗️ |

## Architecture

```
User selects theme via ThemeSwitcher dialog
        ↓
switch_theme() in modern_theme_loader_v2.js
        ↓
├── Sets data-theme="light|dark" on <html>
├── Sets data-modern-theme="construction_light|construction_dark" on <html> (or removes it)
├── Saves to localStorage('construction_theme') for page reload persistence
├── Calls save_user_mode API (persists light/dark to User.desk_theme)
├── Calls set_user_theme API (persists construction variant to User Desk Theme)
└── Updates navbar indicator label and dot color
```

## Files

| File | Purpose |
|---|---|
| `public/js/modern_theme_loader_v2.js` | Theme loader, switcher override, inline CSS injection |
| `api/theme_api.py` | Server-side theme resolution + persistence APIs |
| `overrides/switch_theme.py` | Frappe switch_theme override for construction themes |
| `public/css/modern_theme_tokens.css` | Design tokens (colors, spacing, typography) |
| `public/css/modern_theme_base.css` | Frappe native element overrides |
| `public/css/modern_theme_*.css` | Component-specific styles |

## How It Works

### Theme Switching
The ThemeSwitcher class is overridden to add Construction Light and Construction Dark options. When a user selects a theme:

1. `data-theme` is set to `light` or `dark` (Frappe's native attribute)
2. `data-modern-theme` is set to `construction_light` or `construction_dark` (our custom attribute, removed for standard themes)
3. The inline CSS in the JS file uses `html[data-modern-theme="construction_dark"]` selectors to apply green-accented styles
4. The choice is saved to `localStorage` so it persists across page reloads

### Why Inline CSS?
Frappe's asset pipeline doesn't reliably serve the `modern_theme_light.css` and `modern_theme_dark.css` files (they're listed in `hooks.py` `app_include_css` but don't appear as `<link>` tags in the browser). The construction theme CSS is therefore injected inline via JavaScript to guarantee it loads.

### TimestampMismatchError Prevention
The `save_user_mode` API uses `frappe.db.set_value(..., update_modified=False)` to avoid the `TimestampMismatchError` that occurs when Frappe's User document is modified concurrently. The `switch_theme` override also uses `update_modified=False`.

## Adding a New Theme

To add a new theme variant (e.g., "Ocean Dark"):

1. Add CSS rules in the inline CSS section of `modern_theme_loader_v2.js` using `html[data-modern-theme="ocean_dark"]` selectors
2. Add the theme to the `fetch_themes()` array in the ThemeSwitcher override
3. Add handling in `switch_theme()` for the new theme name
4. Update the `updateNavbarIndicator()` and `injectNavbarIndicator()` functions for the new label/dot color

## Known Limitations

- Construction theme CSS is inline in JS (not in separate CSS files) due to Frappe asset pipeline issues
- Theme persistence uses localStorage (client-side) because the server-side `get_effective_desk_theme` API doesn't return the construction variant on page reload
- The `prefers-color-scheme: auto` option maps to light/dark but doesn't auto-select construction variants
