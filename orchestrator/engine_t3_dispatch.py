"""Engine -> T3 dispatch & collection (ISOLATED: no live engine wiring).

Bridges the ENGINE's job lifecycle to the T3 task transport
(`wp1.t3_transport.T3Transport`) without touching the live engine, the live
config, or any pilot root, and without running any model — every test uses an
in-memory fake T3.

Two durable stores, deliberately separate:

  DispatchLedger   ENGINE side: job state machine, bound to (work_item, root).
                   Survives crashes; holds the original job payload so a fresh
                   process can finish or unwind any interrupted dispatch.
  CorrelationStore (t3_transport) TASK side: job_id <-> task_id + T3 states.

State machines:

  ledger:  pending -> dispatching -> dispatched -> collected
                     \\-> failed (terminal)      \\-> cancelled (terminal)
  task:    intent -> sending -> sent -> completed | failed | uncertain |
                                          cancelled   (t3_transport states)

Crash windows and how they recover (all proven by isolated tests):

  W1 ledger=pending/dispatching, no task record   -> recover(): fresh send
     (the send provably never happened — nothing reached T3)
  W2 ledger=dispatching, task=sending/uncertain   -> recover(): never
     re-sends and never adopts by lookup. The task record carries the
     only trustworthy identity: a known task_id re-polls; otherwise the
     reattach lookup is diagnostic — possible threads are attached to
     the reconciliation error — and the job parks RECONCILIATION_REQUIRED
     (owner reconciles; never guesses)
  W3 ledger=dispatching, task=sent                -> recover(): adopt task_id
     (known-identity; zero client calls)
  W4 ledger=dispatched, task terminal             -> collect() reads the
     durable task record (zero client calls on re-collect)
  W5 ledger=dispatched, task=sending/uncertain    -> recover(): diagnostic
     reattach park (or known-identity re-poll), then collect()

Scope (the engine-side gate; refused BEFORE any ledger write or T3 contact):
  - job_id must match job-[0-9a-f]+; idempotency_key [A-Za-z0-9_-]{16,128}
  - job.work_item must equal this dispatcher's work_item
  - job.root must equal this dispatcher's root (no cross-root dispatch)
  - job.model must be in this dispatcher's allowed pins
  - allow_dispatch defaults False (LAUNCH_AUTH-analog; refused first)

Result validation: T3Transport.validate_result proves terminal + model-pinned
+ marker-present + no pending human stop; the dispatcher adds ENGINE-side
checks — the result must carry the SAME task_id the ledger recorded (corruption
guard), and it is persisted as an engine-linked receipt (job_id, task_id,
work_item, root).

Authority note (carried forward from t3_transport): credentials on the real
route are SAME-OS-USER authority; nothing here proves per-human authentication
(WP3). This module is now wired into the engine through the OPT-IN
orchestrator/t3_dispatch.py launcher (ENGINE_T3_BACKEND=t3); the engine's
launcher slot (preflight/poll/parse) is the insertion point, and native
behavior remains the default when the backend is not selected.
"""

from __future__ import annotations

import time
from pathlib import Path

from t3_transport import (
    IDEM_RE,
    JOB_ID_RE,
    S_CANCELLED,
    S_COMPLETED,
    S_FAILED,
    S_INTENT,
    S_SENDING,
    S_SENT,
    S_UNCERTAIN,
    CorrelationStore,
    TransportReconciliationRequired,
    TransportRefusal,
    TransportUncertain,
)

# ledger states (engine side)
L_PENDING = "pending"               # accepted durably; zero T3 contact
L_DISPATCHING = "dispatching"       # T3 contact possible (crash window)
L_DISPATCHED = "dispatched"         # task_id adopted/correlated; awaiting collection
L_COLLECTED = "collected"           # terminal: validated receipt persisted
L_FAILED = "failed"                 # terminal: validation/transport failure
L_CANCELLED = "cancelled"           # terminal: scoped cancel succeeded
L_RECONCILIATION = "reconciliation_required"  # terminal: owner must reconcile

TERMINAL = {L_COLLECTED, L_FAILED, L_CANCELLED, L_RECONCILIATION}


class ScopeRefusal(TransportRefusal):
    """Job outside this dispatcher's (work_item, root, model-pin) scope."""


class DispatchRefusal(TransportRefusal):
    """Gate closed, state machine violation, or ledger/transport divergence."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class DispatchLedger:
    """Durable engine-side job ledger (receipt_store conventions:
    flock + atomic replace, fail-closed on foreign documents, mkdir at init)."""

    def __init__(self, path: str | Path):
        import json
        import os

        self._json = json
        self._os = os
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = self.path.with_name(self.path.name + ".lock")
        if self.path.exists():
            doc = json.loads(self.path.read_text())
            if not isinstance(doc, dict) or "jobs" not in doc:
                raise ValueError("foreign dispatch ledger (fail-closed)")
            if not isinstance(doc["jobs"], dict):
                raise ValueError("ledger jobs must be an object")

    def _locked(self):
        import fcntl

        fh = open(self._lock, "a+")
        fcntl.flock(fh, fcntl.LOCK_EX)
        return fh

    def _read(self) -> dict:
        if not self.path.exists():
            return {"jobs": {}}
        return self._json.loads(self.path.read_text())

    def _write(self, doc: dict) -> None:
        tmp = self.path.with_name(
            self.path.name + f".tmp.{self._os.getpid()}")
        tmp.write_text(self._json.dumps(doc, sort_keys=True, indent=1))
        self._os.replace(tmp, self.path)

    def get(self, job_id: str) -> dict | None:
        with self._locked():
            return self._read()["jobs"].get(job_id)

    def put(self, job: dict) -> None:
        with self._locked():
            doc = self._read()
            doc["jobs"][job["job_id"]] = job
            self._write(doc)


class EngineT3Dispatcher:
    """Dispatch engine jobs to T3 and collect validated results back.

    Idempotency contract:
      - dispatch(job) twice -> ONE T3 delegate ever (second call returns the
        ledger record; if a prior attempt crashed mid-send, dispatch routes
        through reattach() rather than a fresh plan)
      - collect(job_id) twice -> ONE status call ever (terminal ledger states
        short-circuit with zero client calls)
      - a NEW dispatcher over the same two store files resumes both
        properties (process-restart recovery)
    """

    def __init__(self, *, work_item: str, root: str, allowed_models: list[str],
                 transport,  # wp1.t3_transport.T3Transport
                 ledger: DispatchLedger,
                 allow_dispatch: bool = False):
        self.work_item = str(work_item)
        self.root = str(root)
        self.allowed_models = list(allowed_models)
        self.transport = transport
        self.ledger = ledger
        self.allow_dispatch = bool(allow_dispatch)  # least privilege default

    # -- scope gate (before ANY ledger write or T3 contact) ---------------- #
    def _check_scope(self, job: dict) -> dict:
        if not isinstance(job, dict):
            raise ScopeRefusal("job must be an object")
        job_id = job.get("job_id", "")
        if not isinstance(job_id, str) or not JOB_ID_RE.match(job_id):
            raise ScopeRefusal(f"malformed engine job_id: {job_id!r}")
        if not isinstance(job.get("idempotency_key"), str) or not IDEM_RE.match(
                job["idempotency_key"]):
            raise ScopeRefusal(
                "idempotency_key must match [A-Za-z0-9_-]{16,128}")
        if job.get("work_item") != self.work_item:
            raise ScopeRefusal(
                f"job work_item {job.get('work_item')!r} outside dispatcher "
                f"scope {self.work_item!r}")
        if job.get("root") != self.root:
            raise ScopeRefusal(
                f"job root {job.get('root')!r} outside dispatcher root "
                f"{self.root!r} (cross-root dispatch refused)")
        if job.get("model") not in self.allowed_models:
            raise ScopeRefusal(
                f"model {job.get('model')!r} not in pinned allowed models "
                f"{self.allowed_models}")
        return job

    def _own(self, job_id: str) -> dict:
        rec = self.ledger.get(job_id)
        if rec is None:
            raise DispatchRefusal(
                f"unknown job_id {job_id!r} (not in this dispatcher's ledger)")
        return rec

    @staticmethod
    def _advance(rec: dict, state: str, **extra) -> None:
        rec["state"] = state
        # extras are part of the record itself (error, task_id, reason, ...)
        # AND traced in history — collectors read rec["error"] directly.
        rec.update(extra)
        rec["history"].append({"state": state, "utc": _now(), **extra})

    # -- phase 1: durable dispatch ---------------------------------------- #
    def dispatch(self, job: dict) -> dict:
        self._check_scope(job)                    # scope FIRST (zero effects)
        if not self.allow_dispatch:
            raise DispatchRefusal(
                "dispatch gate closed (allow_dispatch=False) — engine launch "
                "authorization required before any delegation")
        job_id = job["job_id"]
        rec = self.ledger.get(job_id)
        if rec is not None:
            if rec.get("idempotency_key") != job["idempotency_key"]:
                raise DispatchRefusal(
                    "job_id reused with a divergent idempotency_key")
            if rec["state"] == L_RECONCILIATION:
                # durable owner gate: re-dispatch never guesses either
                raise DispatchRefusal(
                    "job parked reconciliation-required; owner must reconcile")
            if rec["state"] in TERMINAL:
                return rec                        # idempotent: terminal
            if rec["state"] == L_DISPATCHED:
                return rec                        # idempotent: already sent
            # pending/dispatching -> fall through to (re)send path
        else:
            rec = {
                "job_id": job_id,
                "idempotency_key": job["idempotency_key"],
                "work_item": self.work_item,
                "root": self.root,
                "state": L_PENDING,
                "task_id": None,
                "job": dict(job),                 # full payload for recovery
                "history": [{"state": L_PENDING, "utc": _now()}],
            }
            self.ledger.put(rec)                  # durable BEFORE T3 contact
        # dispatching marker BEFORE any transport call (crash window W1/W2)
        self._advance(rec, L_DISPATCHING)
        self.ledger.put(rec)
        try:
            task_rec = self._ensure_sent(job)
        except TransportUncertain:
            raise                                  # ledger stays dispatching
        except TransportReconciliationRequired as exc:
            self._advance(rec, L_RECONCILIATION, error=str(exc)[:300],
                          via="recover")
            self.ledger.put(rec)
            raise
        except TransportRefusal:
            raise
        if task_rec["state"] == S_FAILED:
            self._advance(rec, L_FAILED,
                          error=str(task_rec.get("error", ""))[:300])
            self.ledger.put(rec)
            return rec
        # sent (or transport already terminal-successful — adopt the outcome then collect)
        self._advance(rec, L_DISPATCHED,
                      task_id=task_rec.get("task_id"))
        rec["task_id"] = task_rec.get("task_id")
        self.ledger.put(rec)
        return rec

    def _ensure_sent(self, job: dict) -> dict:
        """Send through the transport, routing crash windows via reattach.

        reattach() NEVER re-sends on an uncertain outcome and NEVER adopts
        by lookup: the lookup is diagnostic only — possible threads are
        attached to the reconciliation error for the owner to resolve.
        Dispatch()-path refusals never create a thread.
        """
        existing = self.transport.store.get(job["job_id"])
        if existing is not None and existing.get("state") in (
                S_SENDING, S_UNCERTAIN):
            # W2/W5: interrupted send, outcome unknown — diagnostic reattach or require
            # reconciliation; never an automatic re-send.
            return self.transport.reattach(job["job_id"])
        self.transport.begin_intent(job)           # durable intent (no network)
        return self.transport.send(job)            # marker THEN network

    # -- phase 2: collect + validate --------------------------------------- #
    def collect(self, job_id: str) -> dict:
        rec = self._own(job_id)
        if rec["state"] in TERMINAL:
            return rec                             # idempotent: zero client calls
        if rec["state"] in (L_PENDING, L_DISPATCHING):
            raise DispatchRefusal(
                "job not dispatched; run dispatch()/recover() first")
        try:
            task_rec = self.transport.collect(job_id)
        except TransportUncertain:
            raise                                  # caller must recover() first
        except TransportRefusal as exc:
            # transport marks its own record failed on validation refusal;
            # divergence (no record / never sent) surfaces unchanged.
            stored = self.transport.store.get(job_id)
            if stored is not None and stored.get("state") == S_FAILED:
                self._advance(rec, L_FAILED,
                              error=str(exc)[:300])
                self.ledger.put(rec)
            raise
        # ENGINE-side result guard: the task result must be for THE task the
        # ledger correlated (corruption / store-mixup detection).
        if (task_rec.get("task_id") and rec.get("task_id")
                and task_rec["task_id"] != rec["task_id"]):
            raise DispatchRefusal(
                "ledger/transport task_id mismatch (corruption): "
                f"{rec['task_id']} != {task_rec['task_id']}")
        if task_rec["state"] == S_COMPLETED:
            receipt = task_rec.get("receipt") or {}
            if receipt.get("job_id") != job_id:
                raise DispatchRefusal(
                    "receipt job linkage mismatch (corruption)")
            self._advance(rec, L_COLLECTED,
                          task_id=task_rec.get("task_id"))
            rec["receipt"] = {
                **receipt,
                "work_item": rec["work_item"],     # engine-linked
                "root": rec["root"],
            }
            self.ledger.put(rec)
            return rec
        if task_rec["state"] == S_FAILED:
            self._advance(rec, L_FAILED,
                          error=str(task_rec.get("error", ""))[:300])
            self.ledger.put(rec)
            return rec
        if task_rec["state"] == S_CANCELLED:
            self._advance(rec, L_CANCELLED)
            self.ledger.put(rec)
            return rec
        # in-flight: task exists but not terminal — stay dispatched, poll again
        return rec

    # -- phase 3: crash recovery ------------------------------------------- #
    def recover(self, job_id: str) -> dict:
        """Repair every documented crash window; never double-delegates."""
        rec = self._own(job_id)
        if rec["state"] in TERMINAL:
            return rec
        if rec["state"] == L_PENDING:
            return rec                # zero T3 contact yet; dispatch() later
        # dispatching or dispatched: reconcile against the task record
        stored = self.transport.store.get(job_id)
        if stored is None:
            # W1: crash before the transport ever saw the job -> safe fresh
            # send (the send provably never reached T3).
            stored = self._ensure_sent(rec["job"])
        elif stored.get("state") == S_INTENT:
            stored = self._ensure_sent(rec["job"])
        elif stored.get("state") in (S_SENDING, S_UNCERTAIN):
            # W2/W5: interrupted/unknown send outcome -> identity lookup
            # diagnostic-reconciliation-required (never an automatic re-send).
            try:
                stored = self.transport.reattach(job_id)
            except TransportReconciliationRequired as exc:
                self._advance(rec, L_RECONCILIATION, error=str(exc)[:300],
                              via="recover")
                self.ledger.put(rec)
                raise
        # stored is now sent/completed/failed/cancelled
        if stored.get("state") in (S_SENT, S_COMPLETED) and stored.get(
                "task_id"):
            if rec.get("task_id") and rec["task_id"] != stored["task_id"]:
                raise DispatchRefusal(
                    "ledger/transport task_id divergence: "
                    f"{rec['task_id']} != {stored['task_id']}")
            if rec["state"] == L_DISPATCHING:
                self._advance(rec, L_DISPATCHED,
                              task_id=stored["task_id"], via="recover")
                rec["task_id"] = stored["task_id"]
                self.ledger.put(rec)
            # W3/W4 (already dispatched): nothing to change; collect() reads
            # the durable task record with zero client calls when terminal.
            return rec
        if stored.get("state") == S_FAILED:
            self._advance(rec, L_FAILED,
                          error=str(stored.get("error", ""))[:300],
                          via="recover")
            self.ledger.put(rec)
            return rec
        if stored.get("state") == S_CANCELLED:
            self._advance(rec, L_CANCELLED, via="recover")
            self.ledger.put(rec)
            return rec
        # TransportReconciliationRequired / TransportUncertain propagate to the
        # caller (the engine launcher), which maps them to a durable
        # reconciliation-required outcome — never a re-send. Anything else
        # lands here as an honest divergence.
        raise DispatchRefusal(
            f"unrecoverable task state {stored.get('state')!r} for {job_id}")

    # -- scoped cancellation (own ledger only) ------------------------------ #
    def cancel(self, job_id: str, reason: str) -> dict:
        rec = self._own(job_id)          # own-ledger scope: foreign refused
        if rec["state"] in TERMINAL:
            raise DispatchRefusal(f"job already terminal ({rec['state']})")
        # transport enforces its own gates: allow_cancel, correlated task_id
        self.transport.cancel(job_id, reason)
        self._advance(rec, L_CANCELLED, reason=str(reason)[:200])
        self.ledger.put(rec)
        return rec
