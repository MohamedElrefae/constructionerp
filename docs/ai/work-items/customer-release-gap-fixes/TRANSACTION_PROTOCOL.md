# BOQ aggregate transaction protocol

Implemented locally on 2026-10-04; qualification here is the installed Frappe v16/MariaDB stack, not every advertised runtime.

## Invariant and evidence

After a successful supported operation commits, maintained header/structure totals must agree with authoritative BOQ items under the existing variation/docstatus calculation policy. Arithmetic policy for zero factors and margin layers remains pending the owner; this protocol does not silently change it.

The old plain aggregate SELECT used a transaction's earlier REPEATABLE READ snapshot. Different-item commits could leave 110 stored versus 120 authoritative. Current locking reads correct that sequence to 120/120. Twelve real-connection tests and the unchanged native three-thread WBS insertion test pass; see `VERIFICATION.md`. Test counts do not establish release readiness or capacity.

## Rules for current and future writers

1. Use `construction.services.boq_transactions.lock_boq_header` in the same transaction before changing aggregate inputs. Ordinary BOQ item/structure validation, deletion and the BOQ import commit do so. Lock old/new headers in sorted order when moving an item. Deferred rollups suppress calculation, not the transaction guard; explicitly flush once after the batch.
2. Lifecycle-bypassing cost/revision services use `lock_boq_item_header`, which locks and reads the actual current item's header, then obtains the header guard. Current item documents and relevant cost/baseline records are read with locking reads. VO prelocks distinct existing items sorted by name and validates their header identity before mutations; approved line application order remains unchanged.
3. Recalculate through `read_boq_totals`: a guarded `SELECT ... FOR UPDATE NOWAIT` reads current item values, includes this transaction's writes, and protects the item range against phantoms until transaction end. A header lock followed by a plain snapshot SELECT is insufficient. Header saves and revision-only total updates must use this path too. Structure rollups retain their set-based UPDATE under the same header guard.
4. Frappe may acquire an existing child document lock before controller validation. Header/current-range guards after that acquisition use NOWAIT to avoid waiting cycles. New structure insertion acquires the header in `before_insert`, before its naming, sibling and item locks; that path may wait at most five seconds. MariaDB can still detect conflicts involving framework/global tree locks: fail the operation and roll it back.
5. A guard timeout/deadlock registers a `before_commit` rejection on the failing database connection. It keeps rejecting commits until a full `frappe.db.rollback()` resets the transaction callbacks. Catching the exception or rolling back only to a savepoint must not permit an earlier partial financial write to commit. Propagate failures to the request layer, which rolls back. Never bypass the guard with raw COMMIT, reset its callbacks manually, or add an internal commit.
6. There is no automatic retry loop. A retry must start a fresh transaction and replay the whole authorized operation, respecting permissions, idempotency and commercial history. The regression demonstrates one explicit complete-operation retry after rollback. If automatic retries are later proposed, bound attempts and time, and prove no duplicated approvals/files/jobs; do not retry just the aggregate statement.

The tradeoff is occasional explicit retry under contention, rather than silent stale totals. Batches retain one final rollup; guards do not scan all items on every deferred save. Measure latency, lock conflicts and worker memory for the sold workload before promising capacity.

## Scope and open work

Current routes covered include item CRUD/deletion, header saves/status changes, tree insertion/conversion, deferred import/batch flush, quantity baseline/revision/VO projection and cost approval/prior-analysis restoration. Tests verify selected actual operations and failure paths; they do not prove arbitrary direct SQL or every legacy migration safe.

The writer inventory found `boq_migration_service.py` changing parents outside the NestedSet lifecycle and committing before resequencing, and the historical v7 revision patch using intermediate commits/direct projections. Those upgrade paths need representative legacy fixtures, an atomic/recovery design and separate review under G12. Normal steady-state correctness is not a substitute for that evidence. G02/G03 still require approved-history/cancellation policy; permissions, supported version matrix, hosting, restore, UI and load qualification remain tracked in `STATUS.md`.
