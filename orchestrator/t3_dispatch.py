"""Opt-in engine -> T3 dispatch launcher (ENGINE_T3_BACKEND=t3).

NATIVE BY DEFAULT: with ENGINE_T3_BACKEND unset, cli.make_engine constructs
``Engine(root)`` exactly as before and this module is never imported. With
``ENGINE_T3_BACKEND=t3`` AND ``ENGINE_T3_LAUNCH_AUTH=true``, cli.make_engine
constructs ``Engine(root, launcher=T3DispatchLauncher(...))``.

ENGINE AUTHORITY IS UNCHANGED and fires BEFORE this launcher in every case:

  engine gates (candidate recheck, plan-artifact drift, prepared-job binding,
  builder PLAN grant, engineering-startup evidence, launch policy: allowed
  models/tools/job cap)
      -> T3DispatchLauncher.preflight   (before LAUNCH_INTENT; refusal keeps
         the job row CREATED and consumes no launch attempt)
      -> LAUNCH_INTENT
      -> T3DispatchLauncher.__call__    (durable intent -> send; never raises
         for expected transport outcomes)
      -> job RUNNING
      -> T3DispatchLauncher.poll        (at collect; materializes terminal.json
         from the durable dispatch ledger / correlation store)
      -> engine accept -> T3DispatchLauncher.parse (wire envelope + session)

HONEST BOUNDARIES — this is NOT engine isolation:

  * STAGE-7 VERDICT — FAIL CLOSED. The installed T3 source states verbatim:
    "OpenCode does not provide an OS sandbox, so permission rules are also
    the enforcement boundary for non-interactive policies." There is no
    verifiable OS/filesystem/network boundary for T3 children on this host,
    so REAL dispatch through this launcher is disabled: preflight and the
    default (unfactored) transport refuse before LAUNCH_INTENT and before any
    ledger/network state. Only tests that inject a factory transport exercise
    the wiring; that is simulation, not containment. The smallest enforced
    alternatives are (a) the engine's NATIVE bwrap-confined worker path
    (proven by wp1/test_native_boundary_canary.py) with T3 used read-only for
    observability, or (b) an isolated T3 host — see T3_BACKEND.md.
  * T3 children run inside T3 Code under its own runtime modes.
    ``approval-required`` is a T3-side least-privilege ceiling; it is NOT the
    engine's bwrap sandbox, and launch-policy ``hide_roots`` is NOT applied to
    T3 children. Nothing here claims T3 approval-required == isolation.
  * Containment mechanisms that ARE installed (stage-6 evidence, see
    T3_BACKEND.md): scratch workspace ("fresh folder of its own, outside any
    repository"), the server's caller-mode ceiling (children can never run
    broader than our approved approval-required), runtime-mode -> permission
    defaults (untrusted approvals + readOnly sandbox policy) which T3 derives
    into opencode permission rules (default-deny + bash/edit/webfetch/
    external_directory denied or asked + *.env reads protected), and
    fail-closed consumption (a pending approval/question is never accepted as
    a result). Our own layers add: host-path redaction of every brief
    (artifact-only input), loopback-only HTTP, credential scan of the exact
    sent bytes, and job-bound launch titles for reconciliation.
  * What is NOT proven without a live (gated) child: that opencode's
    external_directory fence actually blocks an out-of-workspace READ at
    runtime, and what environment credentials a child inherits. Those remain
    documented platform limitations, not claims.
  * The engine sandbox (sandbox.command) is never invoked on this path —
    proven by test (sandbox.command patched to raise; T3 path still
    succeeds). That is a DOCUMENTED GAP for any future real run, not a
    safety property.
  * Engine-side gates (candidate/plan/binding/policy/PAUSED/scope) remain in
    force: they run before the launcher and refuse without contacting T3.
  * The real HTTP transport (HttpT3Client + obtain_mcp_token) can no longer
    be constructed from this launcher at all (fail-closed above). It is
    reachable only from the double-gated synthetic-canary probe and the
    env-gated stage-2 live probe, and was NEVER exercised while building
    this stage (no model runs). Tests inject a fake transport through
    ``transport_factory``.
  * Credentials on the real route are SAME-OS-USER authority (WP3 gap);
    access-token revocation is not implemented (see wp1/t3_transport.py).
"""

from __future__ import annotations

import calendar
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

_UNSET = object()

_HERE = Path(__file__).resolve().parent  # orchestrator/
from core import WorkflowError, atomic_write, utc
from engine_t3_dispatch import (
    L_CANCELLED,
    L_COLLECTED,
    L_DISPATCHED,
    L_DISPATCHING,
    L_FAILED,
    L_PENDING,
    L_RECONCILIATION,
    DispatchLedger,
    EngineT3Dispatcher,
)
from t3_transport import (
    CorrelationStore,
    TransportReconciliationRequired,
    TransportRefusal,
    TransportUncertain,
)

# Result marker the transport requires on the child's FINAL line; parse()
# locates the wire envelope independently of it.
MARKER_PREFIX = "ENGINE-T3-RESULT"
WIRE_KEYS = {"result_json", "explanation", "plan_text"}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_POLICY_NAME = "launch_policy.json"


def _is_wire(obj, *, allow_builder_bundle=False) -> bool:
    accepted = {frozenset(WIRE_KEYS)}
    if allow_builder_bundle:
        accepted.add(frozenset(WIRE_KEYS | {"builder_bundle_json"}))
    return (
        isinstance(obj, dict)
        and frozenset(obj) in accepted
        and all(isinstance(obj[k], str) for k in WIRE_KEYS)
        and ("builder_bundle_json" not in obj or isinstance(obj["builder_bundle_json"], str))
    )


def _extract_wire(raw, *, allow_builder_bundle=False) -> dict:
    """Extract the {result_json, explanation, plan_text} wire from child output.

    Mirrors adapters.parse_output's contract (exactly those three string
    fields) but works on the T3 final message: a JSON line possibly followed
    by the marker line, or the envelope embedded in surrounding prose.
    """
    text = raw if isinstance(raw, str) else raw.decode("utf-8", "replace")
    for line in reversed(text.splitlines()):  # final message first
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if _is_wire(obj, allow_builder_bundle=allow_builder_bundle):
            return obj
    decoder = json.JSONDecoder()
    idx = 0
    while True:  # balanced scan fallback
        idx = text.find("{", idx)
        if idx < 0:
            break
        try:
            obj, _end = decoder.raw_decode(text, idx)
        except ValueError:
            idx += 1
            continue
        if _is_wire(obj, allow_builder_bundle=allow_builder_bundle):
            return obj
        idx += 1
    raise WorkflowError("MALFORMED_RESULT: invalid wire envelope")


class T3DispatchLauncher:
    """Engine launcher slot -> T3 dispatch (opt-in backend; never native).

    Construction is CHEAP and touches no state: the engine store, policy and
    dispatch ledger are read lazily at first use so ``doctor``/``status`` can
    construct it safely. All durable stores live under the engine root
    (orchestrator/var/), never outside it.
    """

    allow_builder_for_tests = False

    def __init__(
        self,
        root,
        *,
        transport_factory=None,
        allow_dispatch=True,
        hard_timeout_s=None,
        min_poll_interval_s=5.0,
    ):
        self.root = str(Path(root).resolve())
        self.transport_factory = transport_factory
        self.allow_dispatch = bool(allow_dispatch)
        self.hard_timeout_s = hard_timeout_s
        # Durable poll floor (stored in the ledger, honored across processes):
        # the CLI collect loop runs every 0.5 s and must not become a
        # status/reattach request storm against the T3 endpoint.
        self.min_poll_interval_s = float(min_poll_interval_s)
        # Observation for tests/audit: dispatch attempts and collect polls.
        self.calls: list[str] = []
        self.polls: list[str] = []
        self._config: dict | None = None
        self._policy = _UNSET
        self._dispatcher = None

    # ------------------------------------------------------------------ #
    # lazy, root-local state
    # ------------------------------------------------------------------ #
    def engine_config(self) -> dict:
        if self._config is None:
            db = Path(self.root) / "orchestrator" / "var" / "checkpoints.db"
            if not db.is_file():
                raise WorkflowError("T3 backend: engine store absent")
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
            finally:
                conn.close()
            if not row:
                raise WorkflowError("T3 backend: engine config absent")
            self._config = json.loads(row[0])
        return self._config

    def policy(self) -> dict:
        """launch_policy.json — REQUIRED for the T3 backend (fail closed)."""
        if self._policy is _UNSET:
            path = Path(self.root) / "orchestrator" / _POLICY_NAME
            doc = None
            if path.is_file():
                try:
                    doc = json.loads(path.read_text())
                except (OSError, ValueError) as exc:
                    raise WorkflowError(f"T3 backend: launch policy unreadable: {exc}") from exc
            if not isinstance(doc, dict):
                raise WorkflowError("T3 backend requires a valid orchestrator/launch_policy.json")
            models = doc.get("allowed_models")
            if (
                not isinstance(models, list)
                or not models
                or not all(isinstance(m, str) and m for m in models)
            ):
                raise WorkflowError(
                    "T3 backend: launch policy allowed_models must be a " "non-empty list of strings"
                )
            self._policy = doc
        return self._policy

    def dispatcher(self) -> EngineT3Dispatcher:
        if self._dispatcher is None:
            config = self.engine_config()
            work_item = config.get("work_item")
            if not work_item:
                raise WorkflowError("T3 backend: config carries no work_item")
            allowed = list(self.policy()["allowed_models"])
            if self.transport_factory is not None:
                transport = self.transport_factory(
                    root=self.root, allowed_models=allowed, allow_send=self.allow_dispatch
                )
            else:
                transport = self._real_transport(allowed_models=allowed)
            var = Path(self.root) / "orchestrator" / "var"
            self._dispatcher = EngineT3Dispatcher(
                work_item=work_item,
                root=self.root,
                allowed_models=allowed,
                transport=transport,
                ledger=DispatchLedger(var / "t3-dispatch-ledger.json"),
                allow_dispatch=self.allow_dispatch,
            )
        return self._dispatcher

    def _real_transport(self, *, allowed_models: list):
        # STAGE-7 FAIL-CLOSED belt: the real HTTP transport is never built
        # from the engine launcher. Only the env-gated synthetic-canary probe
        # (wp1/t3_canary_probe.py, reviewed before use) constructs a client,
        # and never for project content.
        raise WorkflowError(
            "T3 backend fail-closed: real transport construction is disabled "
            "until a verifiable containment boundary exists (T3_BACKEND.md)."
        )

    # ------------------------------------------------------------------ #
    # engine hook 1: preflight BEFORE LAUNCH_INTENT (refusal => job stays
    # CREATED, no launch attempt consumed, zero T3 contact)
    # ------------------------------------------------------------------ #
    def preflight(self, job: dict) -> None:
        # STAGE-7 FAIL-CLOSED: with no factory transport injected (the REAL
        # path), refuse before LAUNCH_INTENT — no enforceable OS boundary
        # exists for T3 children (installed T3 source: OpenCode has no OS
        # sandbox). Zero state, zero network, no override knob.
        if self.transport_factory is None:
            raise WorkflowError(
                "T3 production backend refused unconditionally: this build has "
                "no production T3 transport or provider access. No environment "
                "flag, sealed marker or namespace grants it."
            )
        if not self.allow_dispatch:
            raise WorkflowError("T3 launch authorization not granted " "(ENGINE_T3_LAUNCH_AUTH is not true)")
        spec = job.get("spec") or {}
        role = job.get("role") or spec.get("role")
        if role == "builder":
            raise WorkflowError("T3 backend refuses builder dispatch (read-only transport)")
        envelope = spec.get("envelope") or {}
        if envelope.get("candidate_kind") == "stage4-proposal":
            raise WorkflowError("T3 backend refuses stage4-proposal dispatch (private stage)")
        job_root = spec.get("root")
        if job_root and str(Path(job_root).resolve()) != self.root:
            raise WorkflowError("T3 backend refuses cross-root dispatch " f"({job_root} != {self.root})")
        policy = self.policy()
        if spec.get("model") not in policy["allowed_models"]:
            raise WorkflowError(
                f"T3 backend refuses model {spec.get('model')!r} " "not in launch policy allowed_models"
            )
        config = self.engine_config()
        expected_wi = config.get("work_item")
        if expected_wi and envelope.get("work_item") != expected_wi:
            raise WorkflowError(
                "T3 backend refuses job work_item " f"{envelope.get('work_item')!r} != engine {expected_wi!r}"
            )

    # ------------------------------------------------------------------ #
    # engine hook 2: dispatch (called post-gates, post-LAUNCH_INTENT)
    # ------------------------------------------------------------------ #
    def __call__(self, job: dict) -> None:
        job_id = job["job_id"]
        self.calls.append(job_id)
        try:
            self.dispatcher().dispatch(self._dispatch_job(job))
        except TransportUncertain:
            # Send outcome unknown: ledger + correlation records are parked;
            # poll() reattach() adopts the ORIGINAL thread iff it can be
            # uniquely identified (read-only lookup) or parks the job
            # RECONCILIATION_REQUIRED — no automatic re-send, ever.
            return
        except TransportRefusal as exc:
            # Refusal raised BEFORE any network I/O (dispatcher gate/scope, or
            # the brief credential scan): durable denial terminal -> engine
            # classifies -> DENIED_ACTION -> owner pause. Failures INSIDE the
            # network call (token/HTTP) park as uncertain instead and surface
            # as TIMEOUT if never recovered (documented in T3_BACKEND.md).
            self._write_denial(job, exc)
            return
        # Durable send (or idempotent already-sent): RUNNING; poll() will
        # materialize terminal.json at collect time.

    def _dispatch_job(self, job: dict) -> dict:
        spec = job["spec"]
        envelope = spec.get("envelope") or {}
        return {
            "job_id": job["job_id"],
            "role": job.get("role") or spec.get("role"),
            # job-<hex24> satisfies IDEM_RE; deterministic per engine job.
            "idempotency_key": job["job_id"],
            "work_item": envelope.get("work_item") or self.engine_config().get("work_item"),
            "root": self.root,
            "model": spec["model"],
            "brief": spec["prompt"],
            "expect_marker": f"{MARKER_PREFIX} {job['job_id']}",
            "access": "read-only",
        }

    # ------------------------------------------------------------------ #
    # engine hook 3: poll at collect (only while terminal.json is absent)
    # ------------------------------------------------------------------ #
    def poll(self, job: dict) -> None:
        job_id = job["job_id"]
        self.polls.append(job_id)
        dispatcher = self.dispatcher()
        rec = dispatcher.ledger.get(job_id)
        if rec is None:
            # No durable dispatch record at all — either a crash before this
            # launcher ever ran (LAUNCH_INTENT) or the ledger was destroyed
            # externally. Re-dispatching would send with zero knowledge of
            # outcome: never. Leave the row alone; the engine pauses honestly
            # (LAUNCH_INTENT path) or the durable timeout terminates it.
            return
        if rec is not None and rec["state"] == L_RECONCILIATION:
            # Durable owner gate: no transport contact ever; the engine maps
            # the WorkflowError code to a RECONCILIATION_REQUIRED pause.
            raise WorkflowError(f"RECONCILIATION_REQUIRED: {rec.get('error') or job_id}")
        if (
            rec is not None
            and rec["state"] in (L_PENDING, L_DISPATCHING, L_DISPATCHED)
            and self._throttled(rec)
        ):
            # Durable poll floor: bound the job, but issue no transport call.
            self._maybe_timeout(job, rec)
            return
        try:
            if rec is None or rec["state"] == L_PENDING:
                # (Re)send path: gate/scope refusals are denials.
                rec = dispatcher.dispatch(self._dispatch_job(job))
            elif rec["state"] == L_DISPATCHING:
                rec = dispatcher.recover(job_id)
        except TransportUncertain:
            # Outcome still unknown on this pass; bound it, else stay RUNNING.
            self._stamp_poll(dispatcher, job_id)
            self._maybe_timeout(job, rec)
            return
        except TransportReconciliationRequired as exc:
            # Never re-sent, never guessed: the engine parks the job as
            # RECONCILIATION_REQUIRED for explicit owner reconciliation.
            raise WorkflowError(f"RECONCILIATION_REQUIRED: {exc}") from exc
        except TransportRefusal as exc:
            self._write_denial(job, exc)
            return
        try:
            if rec["state"] == L_DISPATCHED:
                rec = dispatcher.collect(job_id)
        except TransportUncertain:
            self._stamp_poll(dispatcher, job_id)
            self._maybe_timeout(job, rec)
            return
        except TransportReconciliationRequired as exc:
            # Terminal-completed but projection missing/empty: never a false
            # accept, never a hidden malformed result — owner reconciles.
            raise WorkflowError(f"RECONCILIATION_REQUIRED: {exc}") from exc
        except TransportRefusal as exc:
            # collect() refusal: transport validation or integrity divergence —
            # raw text feeds the engine's own classifier (MALFORMED_RESULT).
            self._write_failure(job, rec, str(exc))
            return
        state = rec["state"]
        if state == L_COLLECTED:
            receipt = rec.get("receipt") or {}
            self._write_stdout(job, str(receipt.get("summary", "")))
            self._write_terminal(job, rec, exit_code=0)
        elif state == L_FAILED:
            self._write_failure(job, rec, str(rec.get("error", "")))
        elif state == L_CANCELLED:
            self._write_failure(job, rec, "T3 dispatch cancelled")
        elif state == L_RECONCILIATION:
            raise WorkflowError(f"RECONCILIATION_REQUIRED: {rec.get('error') or job_id}")
        elif state == L_DISPATCHED:
            # In flight: record the contact for the durable poll floor, then
            # only a wall-clock bound may end it.
            self._stamp_poll(dispatcher, job_id)
            self._maybe_timeout(job, rec)
        # pending/dispatching after a refused recovery are already written
        # above; anything else stays RUNNING for the next collect pass.

    def _throttled(self, rec: dict) -> bool:
        """True when a transport contact happened less than the floor ago."""
        if self.min_poll_interval_s <= 0:
            return False
        last = rec.get("last_poll_utc")
        if not isinstance(last, str):
            return False
        try:
            began = calendar.timegm(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            return False
        return (time.time() - began) < self.min_poll_interval_s

    def _stamp_poll(self, dispatcher, job_id: str) -> None:
        """Durably record that a transport contact just happened (re-get to
        avoid clobbering records the dispatcher advanced during the call)."""
        rec = dispatcher.ledger.get(job_id)
        if rec is None:
            return
        rec["last_poll_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        dispatcher.ledger.put(rec)

    def _maybe_timeout(self, job: dict, rec) -> None:
        if not self._expired(job, rec):
            return
        started = self._started(rec)
        self._write_stdout(
            job,
            "T3 dispatch exceeded its hard timeout; no terminal result was "
            "ever observed from the T3 task.\n",
        )
        self._write_terminal(job, rec, exit_code=124, timeout=True, started=started)

    def _expired(self, job: dict, rec) -> bool:
        limit = self.hard_timeout_s
        if limit is None:
            limit = float((job.get("spec") or {}).get("hard_timeout") or 3600)
        history = (rec or {}).get("history") or []
        started = history[0].get("utc") if history else None
        if not started:
            return False
        try:
            # timegm: the ledger timestamps are UTC, not local time.
            began = calendar.timegm(time.strptime(started, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            return False
        return (time.time() - began) > limit

    # ------------------------------------------------------------------ #
    # engine hook 4: parse at acceptance (exit 0 path only)
    # ------------------------------------------------------------------ #
    def parse(self, job: dict, raw: str):
        wire = _extract_wire(raw, allow_builder_bundle=job.get("role") == "builder")
        try:
            body = json.loads(wire["result_json"])
        except ValueError as exc:
            raise WorkflowError("MALFORMED_RESULT: invalid wire envelope") from exc
        if not isinstance(body, dict):
            raise WorkflowError("MALFORMED_RESULT: invalid wire envelope")
        rec = self.dispatcher().ledger.get(job["job_id"])
        session = (rec or {}).get("task_id")
        # COMPLETE results must carry a schema-valid session identity; the
        # T3 task id is that identity (fail closed, never guess one).
        if not isinstance(session, str) or not _ID_RE.match(session):
            raise WorkflowError("MALFORMED_RESULT: missing T3 task identity")
        return session, body, wire, []

    # ------------------------------------------------------------------ #
    # durable observation writers (stdout FIRST, terminal LAST: terminal.json
    # is the engine's collect trigger and accept() reads stdout.jsonl)
    # ------------------------------------------------------------------ #
    def _write_denial(self, job: dict, exc: Exception) -> None:
        # "denied action" is the engine classifier's DENIED_ACTION keyword.
        self._write_stdout(job, f"T3 dispatch denied action: {type(exc).__name__}: {exc}\n")
        self._write_terminal(job, None, exit_code=1)

    def _write_failure(self, job: dict, rec, text: str) -> None:
        self._write_stdout(job, (text or "T3 task failed") + "\n")
        self._write_terminal(job, rec, exit_code=1)

    def _started(self, rec) -> str:
        history = (rec or {}).get("history") or []
        started = history[0].get("utc") if history else None
        return started if isinstance(started, str) and started.endswith("Z") else utc()

    def _write_stdout(self, job: dict, text: str) -> None:
        atomic_write(Path(job["runtime"]) / "stdout.jsonl", text.encode("utf-8"))

    def _write_terminal(
        self, job: dict, rec, *, exit_code: int, timeout: bool = False, started: str | None = None
    ) -> None:
        observation = {
            "job_id": job["job_id"],
            "phase": "TERMINAL",
            "exit_code": int(exit_code),
            "started_utc": started or self._started(rec),
            "finished_utc": utc(),
        }
        if timeout:
            observation["timeout"] = True
        atomic_write(
            Path(job["runtime"]) / "terminal.json",
            json.dumps(observation).encode("utf-8"),
        )
