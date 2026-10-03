#!/usr/bin/env bash
# Persisted runner for the canonical bilingual regression matrix.
# Executes all 12 bilingual test modules (151 total tests).

set -euo pipefail

SITE="${1:-v16.localhost}"
BENCH_DIR="/home/mohamed/frappe-bench"

MODULES=(
    "construction.tests.test_bilingual_account_pilot"
    "construction.tests.test_bilingual_boq_print"
    "construction.tests.test_bilingual_data_import"
    "construction.tests.test_bilingual_wave1_pilot"
    "construction.tests.test_bilingual_wave1_phase2_pilot"
    "construction.tests.test_bilingual_wave2a_pilot"
    "construction.tests.test_bilingual_employee_pilot"
    "construction.tests.test_bilingual_department_pilot"
    "construction.tests.test_bilingual_task_pilot"
    "construction.tests.test_bilingual_asset_category_pilot"
    "construction.tests.test_bilingual_payment_terms_template_pilot"
    "construction.tests.test_bilingual_narrative_sanitizer"
)

cd "$BENCH_DIR"

for m in "${MODULES[@]}"; do
    echo "=== MODULE $m ==="
    bench --site "$SITE" run-tests --module "$m" 2>&1
done
