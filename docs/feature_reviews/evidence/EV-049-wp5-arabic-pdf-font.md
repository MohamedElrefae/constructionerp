# EV-049 - WP5 Arabic PDF Font and Renderer

Date: 2026-06-09

Task: `WP5.3`

## Scope

Verify Arabic PDF font availability and PDF renderer support on `v16.localhost`.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_boq_pdf_arabic_font_smoke
```

Result summary:

```json
{
  "success": true,
  "font_match": "NotoNaskhArabic-Regular.ttf: \"Noto Naskh Arabic\" \"Regular\"",
  "wkhtmltopdf": "wkhtmltopdf 0.12.6"
}
```

Both Arabic header and full BOQ PDFs rendered as private files, `pdftotext` detected Arabic text, and `pdffonts` showed embedded Arabic-capable fonts including `NotoNaskhArabic` and `Amiri`.

## Status

`WP5.3` can move to `VER`.
