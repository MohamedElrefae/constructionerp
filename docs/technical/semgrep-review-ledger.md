# Semgrep finding review ledger

The Semgrep review ledger keeps scan findings and bounded manual-review decisions distinct. The raw Semgrep JSON remains the source for `raw_findings_total`. Exact reviewed exceptions are counted separately as `reviewed_findings`; findings without a valid, exact `REVIEWED` record remain `unresolved_findings`. A clean checker exit requires successful scanner execution, no Semgrep JSON errors, and zero unresolved findings. The current ledger contains five independently pinned `relaxed-permissions` candidates, all `PENDING`; those entries do not approve or suppress findings.

Run Semgrep in JSON scan mode without `--error`, then validate its JSON and exit code:

```sh
semgrep scan --json --config <qualified-rules> --config r/python.lang.correctness
python3 scripts/check_semgrep_review_ledger.py \
  --raw-semgrep-json <raw-semgrep.json> \
  --scanner-exit <semgrep-scan-exit-code> \
  --review-ledger .github/security/semgrep_review_ledger.json \
  --candidate-root .
```

The checker treats nonzero scanner exit as execution failure, not as a signal that findings exist. It fails closed for malformed JSON, Semgrep errors, malformed or noncanonical paths/spans, any new or missing finding, stale/extra ledger entries, altered source permission records, and source/guard/test digest mismatches. It pins the exact five finding identities and permission-array records in code, so editing both the ledger inventory and entries cannot replace the expected targets. The ledger stores only a SHA-256 digest of each canonical permission-fields object; the checker independently pins the expected fields and compares them with the actual indexed DocType record. This avoids duplicating permission-shaped JSON in the ledger. No rule-wide or path-wide finding exception is introduced.

Each future reviewed entry must bind its source, guard, and test files by SHA-256 and supply a `reviewed_source_manifest_sha256`. That manifest is computed from the canonical compact UTF-8 JSON array of unique `{path, sha256}` records sorted by relative path, with object keys sorted. The checker verifies the individual file hashes against the candidate before comparing the manifest. This 64-character manifest hash is not the candidate Git SHA. Record the exact candidate Git commit and CI/native test run IDs in the operational run evidence; do not present source hashes or ledger fields as proof that tests ran or that a human reviewed a finding.

Any `REVIEWED` status requires an explicit accepted decision, parent review reference, a local combined qualification ID and SHA-256, native REST run and log reference, and a matching source manifest. The local qualification artifact records the exact phased local results and source bindings; its reference is not a GitHub CI run or proof by itself. Separately, the remote workflow must execute all named native REST and owner-guard tests on the exact final candidate commit. Record that commit and remote CI run in external qualification evidence; do not add a future CI run ID to the candidate ledger, which would change the commit the run tested. Keep entries `PENDING` until the actual local qualification and parent review exist. The checker does not identify who supplied a review reference or independently prove that the named local or remote run executed.

The focused offline fixture suite is:

```sh
python3 -m pytest -q tests_offline/test_semgrep_review_ledger.py
```

Workflow wiring is maintained separately; this document and checker do not change Semgrep rules, exclusions, or CI behavior.
