# EV-053 - WP5 Visual QA Artifacts

Date: 2026-06-09

Tasks: `WP5.8`, `WP5.9`

## Scope

Generate persistent Arabic BOQ print/export artifacts from existing Frozen Arabic BOQ `BOQ-2026-0006`.

## Verification

Command:

```bash
bench --site v16.localhost execute construction.tests.test_boq_excel_parser.run_wp5_visual_artifacts_smoke
```

Artifacts:

- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/wp5_visual_artifacts/WP5-arabic_header_pdf.pdf`
- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/wp5_visual_artifacts/WP5-arabic_header_pdf.png`
- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/wp5_visual_artifacts/WP5-arabic_full_pdf.pdf`
- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/wp5_visual_artifacts/WP5-arabic_full_pdf.png`
- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/wp5_visual_artifacts/WP5-arabic_full_excel.xlsx`

Checks:

- `file` confirmed PDFs, PNG page renders, and XLSX workbook.
- `pdffonts` confirmed embedded Arabic-capable fonts in the full PDF.
- Visual inspection confirmed readable Arabic header/full BOQ pages after template spacing fixes.
- Excel RTL behavior was already verified in `EV-038`; this evidence adds a persistent Arabic XLSX artifact.

## Status

`WP5.8` and `WP5.9` can move to `VER`.
