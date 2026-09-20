# Stage 3 — Independent AI-R Round 10 Verification

**Verdict: BLOCKED. Stage 4 must not begin.**

Fresh review of the current uncommitted candidate, not approval of prior reports. Evidence-only: no implementation, catalog, payload, business DB, runtime Translation, Git index/history, or existing evidence file was changed; the only write is this report.

## Blocking finding

**P1 — the claimed shared strict-integer contract is not implemented on both public paths.** `construction/services/bilingual_service.py` defines the strict `_coerce_int` and uses it in `search_bilingual`, raising `frappe.ValidationError` for fractional floats, garbage, and `None`. However, `construction/searchable_dropdown/api/search.py` still defines a separate local `_coerce_int` (lines 226ff) executing `int(float(value))` and falling back to the default on `TypeError`/`ValueError`. The dropdown therefore accepts `"3.5"`/`3.7` as truncated integers and silently defaults garbage/`None`, rather than using the shared helper and producing the same error class/message.

The permanent `test_non_integer_pagination_inputs_are_cross_path_consistent` test uses only `assertRaises(Exception)` for the dropdown and does not require an exception or exact `frappe.ValidationError` class/message. This directly contradicts the Round-10 closure claim. Required tests must assert exact failure parity for `"3.5"`, `"abc"`, `3.7`, and `None`, plus accepted integer/integer-string cases on both paths, including blank/text and start/page interactions.

## P95 artifact review

Current artifact SHA-256: `4b956657039b7e137bca8d8429d23eb615ae4a14f3e818ced59b9c45966a39ba`. It preserves five raw rounds of 50 samples per side and five `round_p95_ms` values. Independent nearest-rank recomputation gives baseline `[1.983, 2.288, 1.974, 2.729, 2.603]` and bilingual `[2.518, 3.371, 2.953, 2.591, 2.034]`; selected minima are 1.974 ms and 2.034 ms (+3.04%), within the bare 10% rule. The permanent test checks every round and the minimum selection. Code hashes match current service `a8c049443d7755714e2a173c75cd5747fce527a374be6b43cf7c76b49ebd0698`, registry `691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538`, and dropdown `c6ee63717a4fe8408657a7b46fd1799d7aa13c9db081669dec2390b4e22ed99b`.

The canonical plan permits min-of-rounds; with all raw rounds, workload identities, balanced ordering, warmup/GC, environment, and SQL counts preserved/authenticated, this gate is independently verifiable. It remains a best-case-round gate, not a typical-latency estimate.

## Other evidence

Supplied current evidence reports 53 pilot, 38 pure, 89 standalone, and 215 aggregate tests green; catalog 805; extraction `663 + 21`, missing 0; inventory 18,446 with Merkle `2e284695…`; sync 0/0; evidence gate `errors=0`; clean lints/diff-check; and prior UI, HTTP, permission, ranking/window, overflow, confinement/rename/audit, registry, normalization, and governed Stage-2 controls. These do not override the source-level P1, and aggregate green status was not accepted as proof after the contradictory implementation was found.

## Next gate

Remove the dropdown-local permissive coercer and route both public paths through one strict helper with identical `frappe.ValidationError` semantics. Strengthen permanent tests to require exact class/message parity for all rejected values while retaining accepted/clamped, blank/text, bounded-transfer, one-query, permission, and 5,000/5,001 regressions. Then request a fresh independent AI-R review. No commit, push, merge, deploy, or live Account-name migration is authorized by this report.
