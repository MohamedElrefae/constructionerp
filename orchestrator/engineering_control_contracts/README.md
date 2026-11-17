# Engineering Control contract — OFFLINE ONLY

Version `1.0.0-offline`; machine artifacts in `v1/openapi.json` (OpenAPI 3.1) and `v1/schemas.json` (JSON Schema 2020-12). All 19 operations are live-disabled. No server, executable endpoint, engine transport, authentication mechanism or dependency installation is included.

`contract.py` is the source for artifacts. `offline.py` contains explicitly synthetic test doubles; TestIssuer is a test trust root, never login. FakeBoundary writes only its caller-supplied temporary journal; callers must not give it a real workflow directory. Three operations also fail in the fake: create_work_item, plan, assignments. Other operations illustrate contract obligations only. See the source mapping, decision register and threat model under `docs/ai/work-items/t3-engineering-control-wp1/`.

From repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 orchestrator/engineering_control_contracts/contract.py --write
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider orchestrator/tests/test_engineering_control_contracts.py orchestrator/tests/test_engineering_control_contracts_creation.py orchestrator/tests/test_routing.py orchestrator/tests/test_contracts.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider orchestrator/tests/test_engineering_control_contracts_o01_o04.py -q
```

`provenance.py` and `operation_store.py` are additional TEST-ONLY O01/O02 design prototypes. `provenance.py` verifies signed assertion semantics with a shared test HMAC key and binds replay to the full canonical signed claim digest; `operation_store.py` models an intent journal with a test-only revision precondition, writer epochs, restart uncertainty and reconciliation in a caller-supplied SQLite file. Neither is authentication, durable production storage or a multi-writer control, and neither may be imported by an ingress, service listener or production route. Their 75 offline tests and the O01–O04 design/evidence matrix are under `docs/ai/work-items/t3-engineering-control-wp1/` (see `O01_O04_DESIGN_AND_EVIDENCE.md`).

The generator writes only the two contract artifacts. Tests include fakes plus one isolated real PLAN primitive test in a disposable synthetic engine/Git fixture. No test authenticates a real T3 human, executes a real model or proves native/phone isolation. Avoid importing this package into application hooks or production control routes.

A separate test-only C02 harness in `test_engineering_control_contracts_creation.py` maps the bounded Create schema to real Engine.initialize in disposable fixtures; it does not enable FakeBoundary creation. Receipt `initialization_only` means checkpoint/candidate initialization, with no grant or job. See `C02_CREATION_PROOF.md` for classified Git/SQLite/export writes and uncertain initialization recovery.
