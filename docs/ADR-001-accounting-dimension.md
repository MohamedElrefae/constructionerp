# ADR-001: BOQ Item as Accounting Dimension

## Status

Accepted for Phase 1.

## Context

The approved BOQ integration plan uses `BOQ Item` as the Accounting Dimension so ERPNext GL and operational transactions can be attributed to BOQ cost objects in Phase 1. This gives direct reporting value but creates a high-cardinality dimension as projects grow.

## Decision

Proceed with `BOQ Item` as the Phase 1 Accounting Dimension and provision it idempotently during install and migrate. Keep `BOQ Item Stage` operational only; it is not a GL dimension.

## Consequences

- Small and medium projects can report directly by BOQ Item.
- Large projects may experience slower GL reports when BOQ Item counts grow into the thousands.
- Phase 1 must keep setup idempotent and preserve ERPNext-native Accounting Dimension behavior.

## Migration Path

If GL performance degrades at large scale, introduce a lower-cardinality `Cost Code` dimension in Phase 2, map BOQ Structure/BOQ Item to Cost Code, and keep BOQ Item as an analytical link rather than the primary GL dimension.
