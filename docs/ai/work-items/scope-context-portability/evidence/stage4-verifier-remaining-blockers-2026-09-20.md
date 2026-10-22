# Stage 4 Verifier — Remaining Blockers Diagnosis (2026-09-20)

The verifier returned BLOCKED with two findings. Both are stale-evidence artifacts, not
new defects:

## 1. Panel provenance absent from the bundle

The mounted bundle `d0f66ee9…` was composed **before** the `compose_bundle` provenance
fix; it has no `panel` section (top-level keys: company, rows, schema, workflow). The
current code (`stage4.py:319,819`) does include `panel` with role/session/verdict/
proposal+review digests. A recomposition is required — a fresh panel PASS cycle will
recompose the bundle with the panel section.

## 2. Validation appears unavailable

The verifier ran the validation command from `/tmp/workspace/private_output`, so the
relative path `orchestrator/.venv/bin/python` did not resolve (exit 127). Executed in the
correct execution root under Bubblewrap with network isolation, the command succeeds:

```
orchestrator/.venv/bin/python -m pytest tests_offline -q -p no:cacheprovider
67 passed
```

The engine's `validation_runner` already runs validation with `cwd=spec["root"]`; the
in-job verifier simply does not inherit that. The verifier instruction will state that
validation evidence is runner-captured in the execution root and must not be re-run from
the private output directory.

## Actions

1. Re-run the panel to recompose the bundle with panel provenance.
2. Clarify the verifier instruction about runner-captured validation and the correct root.
3. No ERP mutation, DRY_RUN, IMPORT, commit, push, or merge.
