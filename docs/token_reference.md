# Token Reference Guide

## Construction ERP White-Label Theming System

Complete reference for all 54 CSS design tokens.

---

## Token Architecture

```
Level 1: Root Tokens (--primary, --bg, --text)
    ↓
Level 2: Theme Variants ([data-theme="dark"] overrides)
    ↓
Level 3: Frappe Mapping (--blue-500: var(--primary) !important)
```

---

## Color Tokens (16)

### Primary Palette

| Token | Dark Value | Light Value | Usage |
|-------|------------|-------------|-------|
| `--primary` | #2563eb | #2563eb | Main brand color, buttons, links |
| `--primary-hover` | #1d4ed8 | #1d4ed8 | Button hover, link hover |
| `--primary-light` | rgba(37,99,235,0.15) | rgba(37,99,235,0.12) | Subtle backgrounds, selected states |

### Accent Colors

| Token | Dark Value | Light Value | Usage |
|-------|------------|-------------|-------|
| `--accent` | #f59e0b | #f59e0b | Warnings, highlights, attention |
| `--accent-hover` | #d97706 | #d97706 | Accent hover state |
| `--accent-light` | rgba(245,158,11,0.15) | rgba(245,158,11,0.12) | Subtle accent backgrounds |

### Semantic Colors

| Token | Dark Value | Light Value | Usage |
|-------|------------|-------------|-------|
| `--danger` | #dc2626 | #dc2626 | Errors, delete actions, critical alerts |
| `--danger-hover` | #b91c1c | #b91c1c | Danger hover state |
| `--danger-light` | rgba(220,38,38,0.15) | rgba(220,38,38,0.12) | Error message backgrounds |
| `--success` | #16a34a | #16a34a | Success states, confirmations |
| `--success-light` | rgba(22,163,74,0.15) | rgba(22,163,74,0.12) | Success message backgrounds |

---

## Background Tokens (4)

| Token | Dark Value | Light Value | Usage |
|-------|------------|-------------|-------|
| `--bg` | #0b1020 | #f8fafc | Page background |
| `--bg-2` | #111827 | #f1f5f9 | Secondary background, alternate rows |
| `--surface` | #1e293b | #ffffff | Cards, modals, popovers |
| `--surface-hover` | #334155 | #f1f5f9 | Hover state for surface elements |
| `--surface-active` | #475569 | #e2e8f0 | Active/pressed state |

---

## Text Tokens (4)

| Token | Dark Value | Light Value | Usage |
|-------|------------|-------------|-------|
| `--text` | #f8fafc | #0f172a | Primary text, headings |
| `--text-2` | #94a3b8 | #475569 | Secondary text, descriptions |
| `--text-3` | #64748b | #94a3b8 | Tertiary text, placeholders |
| `--text-disabled` | #475569 | #cbd5e1 | Disabled text states |

---

## Border Tokens (3)

| Token | Dark Value | Light Value | Usage |
|-------|------------|-------------|-------|
| `--border` | rgba(148,163,184,0.18) | rgba(15,23,42,0.10) | Default borders |
| `--border-hover` | rgba(148,163,184,0.28) | rgba(15,23,42,0.18) | Hover state borders |
| `--divider` | rgba(148,163,184,0.10) | rgba(15,23,42,0.08) | Section dividers |

---

## Shadow Tokens (3)

### Dark Theme Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | 0 2px 8px rgba(0,0,0,.40) | Subtle elevation, dropdowns |
| `--shadow` | 0 8px 24px rgba(0,0,0,.48) | Cards, modals |
| `--shadow-lg` | 0 16px 48px rgba(0,0,0,.56) | High elevation, dialogs |

### Light Theme Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | 0 2px 8px rgba(0,0,0,.06) | Subtle elevation |
| `--shadow` | 0 8px 24px rgba(0,0,0,.08) | Cards, modals |
| `--shadow-lg` | 0 16px 48px rgba(0,0,0,.12) | High elevation |

---

## Radius Tokens (5)

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Small elements, tags, badges |
| `--radius` | 10px | Buttons, inputs, cards |
| `--radius-lg` | 16px | Modals, large cards |
| `--radius-xl` | 24px | Feature cards, hero elements |
| `--radius-full` | 9999px | Pills, avatars, fully rounded |

---

## Transition Tokens (3)

| Token | Value | Usage |
|-------|-------|-------|
| `--t-fast` | 0.15s ease | Quick feedback (hovers, toggles) |
| `--t` | 0.2s cubic-bezier(0.4,0,0.2,1) | Standard transitions |
| `--t-slow` | 0.3s cubic-bezier(0.4,0,0.2,1) | Complex animations |

---

## Special Tokens (5)

| Token | Dark Value | Light Value | Usage |
|-------|------------|-------------|-------|
| `--row-hover-bg` | rgba(37,99,235,0.06) | rgba(37,99,235,0.06) | Table row hover |
| `--row-hover-border` | rgba(37,99,235,0.25) | rgba(37,99,235,0.25) | Table row hover border |
| `--row-focus-ring` | #2563eb | #2563eb | Table row focus indicator |
| `--col-header-bg` | linear-gradient(135deg, #2563eb, #1d4ed8) | Same | DataTable column header |
| `--card-hover-border` | #16a34a | #16a34a | Card hover accent border |

---

## Token Usage Examples

### Button Styling

```css
.btn-primary {
  background-color: var(--primary) !important;
  color: white !important;
  border-radius: var(--radius) !important;
  transition: all var(--t-fast) !important;
  box-shadow: var(--shadow-sm) !important;
}

.btn-primary:hover {
  background-color: var(--primary-hover) !important;
  box-shadow: var(--shadow) !important;
}
```

### Card Styling

```css
.card {
  background-color: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow) !important;
}

.card:hover {
  border-color: var(--card-hover-border) !important;
  box-shadow: var(--shadow-lg) !important;
}
```

### Form Input Styling

```css
.form-control {
  background-color: var(--bg-2) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}

.form-control:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--primary-light) !important;
}
```

---

## Frappe Variable Mapping

Tokens are mapped to Frappe's native CSS variables for complete override:

| Frappe Variable | Maps To |
|----------------|---------|
| `--blue-500` | `--primary` |
| `--red-500` | `--danger` |
| `--orange-500` | `--accent` |
| `--green-500` | `--success` |
| `--bg-color` | `--bg` |
| `--fg-color` | `--surface` |
| `--text-color` | `--text` |
| `--border-color` | `--border` |

---

## Token Inheritance

```css
/* Level 1: Define root tokens */
:root {
  --primary: #2563eb;
  --bg: #0b1020;
  --text: #f8fafc;
  /* ... */
}

/* Level 2: Theme-specific overrides */
[data-theme="light"] {
  --bg: #f8fafc;
  --surface: #ffffff;
  --text: #0f172a;
  /* ... */
}

/* Level 3: Map to Frappe variables */
--blue-500: var(--primary) !important;
--bg-color: var(--bg) !important;
--text-color: var(--text) !important;
```

---

## Creating Custom Themes

Override tokens in your custom theme:

```css
html[data-modern-theme="my_brand"] {
  --primary: #your-brand-color;
  --accent: #your-accent-color;
  --bg: #your-bg-color;
  --surface: #your-surface-color;
  --text: #your-text-color;
  /* ... all 54 tokens */
}
```

All components will automatically adapt to your color scheme.

---

## Token Validation Checklist

When creating a new theme, verify:

- [ ] All 16 color tokens defined
- [ ] All 4 background tokens defined
- [ ] All 4 text tokens defined
- [ ] All 3 border tokens defined
- [ ] All 3 shadow tokens defined
- [ ] All 5 radius tokens defined
- [ ] All 3 transition tokens defined
- [ ] All 5 special tokens defined
- [ ] Light and dark variants tested
- [ ] Contrast ratios meet WCAG 2.1 AA

---

*Token Reference Version: 1.0*
*Total Tokens: 54*
*Last Updated: 2026-05-05*
