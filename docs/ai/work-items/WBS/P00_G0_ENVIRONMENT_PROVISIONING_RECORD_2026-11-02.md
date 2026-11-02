# P00/G0 — Disposable environment provisioning record, 2026-11-02

**Status: PROVISIONED, VALIDATED, AND TORN DOWN (ephemeral; no residue).** No target access, no D2, no custody, no qualification, no Q7 execution, no closure. Gate remains BLOCKED.

## 1. Environment

| Field | Value |
|---|---|
| Name | `p00-g0-disposable-01` |
| Server | locally installed `/usr/sbin/mariadbd` — **`10.11.14-MariaDB-0ubuntu0.24.04.1`** (exactly the recorded accepted full reference) |
| Method | private datadir `mariadb-install-db --no-defaults`, private Unix socket, `--skip-networking`, `--skip-log-bin` |
| Isolation | socket-only; the process bound **no TCP listener**; the pre-existing system service on 3306 was not used or modified |
| Fixtures | synthetic only: `p00g0_fixture.t` with 3 synthetic rows; no user data, identities, credentials, or document identifiers |
| Lifetime | single-use; provisioned, validated, then torn down within the same session (well under the ≤24 h bound) |
| Teardown | `mariadb-admin shutdown`, process wait, datadir removed, verified: no process remains, no datadir residue |
| Evidence boundary | ephemeral only; no ERF records were created; no D2 access |

## 2. Validation evidence (synthetic only)

- `SELECT VERSION()` → `10.11.14-MariaDB-0ubuntu0.24.04.1`
- `@@skip_networking` → `1`
- synthetic fixture: 3 rows inserted, counted
- read-only transaction read on synthetic data succeeded (`START TRANSACTION READ ONLY; SELECT COUNT(*); COMMIT`)
- process-level check: our PID had **no** TCP listener
- pre-existing system service (PID 1241, `127.0.0.1:3306`) confirmed distinct and untouched; the disposable instance never used system credentials or the system datadir

## 3. Scope compliance

- The S4 component was **not** executed against the instance (Q7 execution not authorized); validation used plain SQL only.
- No package installation or system configuration change occurred (the required 10.11.14 build was already present).
- No target, production, staging, or lab access; no D2 creation/access/placement; no custody; no acceptance; no qualification; no closure.
- Teardown verified: datadir removed, process gone; the environment can be re-provisioned reproducibly for a future authorized Q7 run.

## 4. Consumption and next state

The authorization is consumed by completion of this provisioning cycle. Q7 remains `INCOMPLETE`; the witness remains unqualified; D5 freshness remains unvalidated at runtime. Gate BLOCKED; P00/G0, H01, H02 open; P1 deferred; P2 paused.
