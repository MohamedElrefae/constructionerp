"""Real T3 transport adapter for engine jobs (ISOLATED — no engine dispatch).

Maps one engine job to one T3 delegated task over the T3 Code server's MCP
endpoint (streamable HTTP + Bearer), with the durability guarantees the engine
requires around an external, non-transactional side effect:

  DURABLE CORRELATION   engine job_id <-> T3 task_id persisted before the
                        engine can observe the job as sent (flock + atomic
                        replace, receipt_store conventions).
  INTENT-BEFORE-SEND   a durable `intent` record exists before any network
                        call; a durable `sending` marker is written BEFORE
                        the launch call (t3_thread_launch) is invoked, so a
                        crash between marker and reply is detectable and
                        recoverable.
    UNCERTAIN/REATTACH    state=sending without task_id, or a raised send
                          error => state=uncertain. reattach() NEVER re-sends
                          and NEVER re-creates a thread (installed T3 does not
                          dedupe clientRequestId — proven). reattach NEVER
                          adopts by lookup either: a single content-verified
                          candidate after our own cut-reply is indistinguishable
                          from an impostor that copied our task text (marker +
                          per-attempt token are visible to the provider).
                          The lookup is a read-only DIAGNOSTIC: it enumerates
                          the bound recovery project (or all projects for
                          legacy records) and names possible threads in the
                          reconciliation error — owner resolves manually.
                          Uncertain sends always park RECONCILIATION_REQUIRED.
  IDEMPOTENCY           one idempotency_key => one send, forever; replays
                        return the stored record without contacting T3.
  RESULT VALIDATION     a task result is accepted only if terminal, non-empty,
                        model-pinned, marker-matching and free of pending
                        human questions/approvals.
  SCOPED CANCELLATION   cancel() only ever names a task_id that lives in OUR
                        correlation store, and only with allow_cancel=True
                        (separate gate from allow_send).
  SANDBOX/APPROVAL      send is refused unless allow_send=True (least
                        privilege, mirrors LAUNCH_AUTH); specs must declare
                        access="read-only" (writes are not transportable yet);
                        the Bearer token NEVER enters task text, payloads,
                        exceptions or logs.

The engine's own dispatch (engine.run) is deliberately NOT wired to this
transport here: pilot dispatch gates are owner-gated and currently failing
(memory gate, see PILOT_AR_PRECONDITIONS.md). This module is the transport
half, tested against a fake T3 and, when T3_REAL_TRANSPORT=1, against the
live local T3 server with a short-TTL scoped PAIRING credential (revoked at
exchange) and a resource-bound access token that expires by its server-set
TTL — ACCESS-TOKEN REVOCATION IS NOT IMPLEMENTED (documented honestly; the
`t3 auth` CLI cannot list or revoke MCP OAuth tokens).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from pathlib import Path

PROTOCOL = "engineering/v1"
JOB_ID_RE = re.compile(r"^job-[0-9a-f]+$")
IDEM_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
# deterministic correlation key: same Engine job => same clientRequestId.
# Installed T3 does not deduplicate this field; it is never a retry guarantee.
CLIENT_REQ_PREFIX = "wp1-engine-job-"
ENGINE_T3_ROLES = frozenset(
    {
        "architect",
        "reviewer",
        "builder",
        "verifier",
        "proposer",
        "ai-a1",
        "ai-a2",
        "ai-a3",
    }
)

# ---- artifact-only input boundary (stage 6) ---------------------------- #
# Absolute host paths never enter a T3 brief: the engine packet carries its
# data inline, so no child needs to know (or follow) host locations. This is
# prompt-data-exposure containment at OUR boundary; the OS-side read fence is
# the provider permission layer (T3 -> opencode external_directory), and a
# live demonstration of that fence is a separately gated step (T3_BACKEND.md).
HOST_PATH_RE = re.compile(
    r"/(?:home|root|var|etc|opt|usr|srv|private|proc|sys|boot|mnt|media|tmp)" r"(?:/[A-Za-z0-9._@+~+-]+)+"
)
PATH_TOKEN = "<path-redacted>"


def redact_host_paths(text: str) -> str:
    """Replace absolute host paths with a neutral token (artifact-only brief)."""
    return HOST_PATH_RE.sub(PATH_TOKEN, text)


def require_loopback(base_url: str) -> str:
    """Only loopback T3 endpoints are dialable.

    Network containment at OUR boundary: the backend's HTTP client never
    speaks to a remote host, so an endpoint-poisoned configuration cannot
    exfiltrate the brief (or the bearer token) off-box.
    """
    import urllib.parse

    try:
        parts = urllib.parse.urlsplit(str(base_url))
        port = parts.port
    except ValueError:
        raise TransportRefusal("refusing malformed T3 loopback origin") from None
    if (
        parts.scheme not in ("http", "https")
        or parts.hostname not in ("127.0.0.1", "::1")
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise TransportRefusal("refusing non-loopback or credentialed T3 endpoint")
    return base_url


def _loopback_opener():
    """Never forward local bearer credentials via a proxy or redirect."""
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


# record states (linear where possible; uncertain is the only parked state)
S_INTENT = "intent"  # durable, not yet contacting T3
S_SENDING = "sending"  # durable marker written before the network call
S_SENT = "sent"  # task_id correlated
S_COMPLETED = "completed"  # terminal, validated
S_FAILED = "failed"  # terminal, T3 reported failure/invalid result
S_UNCERTAIN = "uncertain"  # parked: outcome unknown, requires reconcile
S_CANCELLED = "cancelled"  # terminal, cancelled through OUR correlation only
MAX_ASSISTANT_ITEM_CHARS = 50_000
MAX_ASSISTANT_SUMMARY_CHARS = 50_000


def scrub_secret(text: str, token: str | None = None) -> str:
    """Remove bearer material from any text that may be raised or persisted."""
    import re as _re

    out = str(text)
    if token:
        out = out.replace(token, "<redacted>")
    out = _re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", out)
    return out


class TransportRefusal(RuntimeError):
    """Gate or validation refusal; never contacted T3 (or T3 rejected us)."""


class TransportUncertain(RuntimeError):
    """Send outcome unknown; record parked in S_UNCERTAIN for reconcile."""


def _normalize_ts(ts: str | None) -> str:
    """Normalize ISO-8601 timestamps for comparison.

    Marker stamps use second precision ("...Z"), T3's createdAt carries
    milliseconds ("...ss.mmmZ"); pad both sides so every comparison is on
    equal footing ('.', 46 < 'Z', 90).
    """
    if not ts:
        return ""
    ts = str(ts).strip()
    if ts.endswith(".000Z") or ("." not in ts and ts.endswith("Z")):
        return ts if ts.endswith(".000Z") else ts.replace("Z", ".000Z")
    return ts


def _assistant_text(out: dict) -> str:
    """Joined assistant_message texts from a t3_thread_read result.

    The child's full answer is the evidence; non-assistant items (tool
    calls, user messages, system) can never satisfy marker/token checks.
    """
    parts = []
    if not isinstance(out, dict):
        return ""  # hostile wire: no content provable
    for item in out.get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "assistant_message":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
    return "\n".join(parts)


class TransportReconciliationRequired(RuntimeError):
    """No safe recovery exists for an uncertain outcome; explicit reconciliation.

    Raised instead of guessing: never re-sends, never re-creates a thread.
    The engine maps this class to a durable RECONCILIATION_REQUIRED pause
    (owner reconciles; the transport never guesses)."""


# --------------------------------------------------------------------------- #
# durable correlation store (receipt_store conventions, own schema)
# --------------------------------------------------------------------------- #
class CorrelationStore:
    """flock + atomic replace; fail-fast on foreign documents; mkdir at init."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = self.path.with_name(self.path.name + ".lock")
        if self.path.exists():
            doc = json.loads(self.path.read_text())
            if not isinstance(doc, dict) or "records" not in doc:
                raise ValueError("foreign correlation document (fail-closed)")
            if not isinstance(doc["records"], dict):
                raise ValueError("correlation records must be an object")

    def _locked(self):
        import fcntl

        fh = open(self._lock, "a+")
        fcntl.flock(fh, fcntl.LOCK_EX)
        return fh

    def _read(self) -> dict:
        if not self.path.exists():
            return {"records": {}}
        return json.loads(self.path.read_text())

    def _write(self, doc: dict) -> None:
        tmp = self.path.with_name(self.path.name + f".tmp.{os.getpid()}")
        tmp.write_text(json.dumps(doc, sort_keys=True, indent=1))
        os.replace(tmp, self.path)

    def get(self, job_id: str) -> dict | None:
        with self._locked():
            return self._read()["records"].get(job_id)

    def put(self, record: dict) -> None:
        with self._locked():
            doc = self._read()
            doc["records"][record["job_id"]] = record
            self._write(doc)

    def by_idempotency_key(self, key: str) -> dict | None:
        with self._locked():
            for rec in self._read()["records"].values():
                if rec.get("idempotency_key") == key:
                    return rec
        return None

    def all(self) -> list[dict]:
        with self._locked():
            return list(self._read()["records"].values())


# --------------------------------------------------------------------------- #
# task spec: what the engine asks T3 to do (read-only transport at this stage)
# --------------------------------------------------------------------------- #
def build_task_spec(job: dict, *, allowed_models: list[str]) -> dict:
    """Validate the engine job and render the bounded, read-only task spec.

    Refuses anything that is not a well-formed, model-pinned, read-only job —
    the transport cannot express writes yet, so it must not pretend it can.
    """
    job_id = job.get("job_id", "")
    if not JOB_ID_RE.match(job_id):
        raise TransportRefusal(f"malformed engine job_id: {job_id!r}")
    if not IDEM_RE.match(job.get("idempotency_key", "")):
        raise TransportRefusal("idempotency_key must match [A-Za-z0-9_-]{16,128}")
    if job.get("access", "read-only") != "read-only":
        raise TransportRefusal(
            "only read-only delegations are transportable at this stage "
            f"(got access={job.get('access')!r})"
        )
    role = job.get("role")
    if role not in ENGINE_T3_ROLES:
        raise TransportRefusal(f"unsupported or missing Engine role: {role!r}")
    model = job.get("model", "")
    if model not in allowed_models:
        raise TransportRefusal(f"model {model!r} not in allowed pins {allowed_models}")
    if not isinstance(job.get("brief"), str):
        raise TransportRefusal("job brief must be a string")
    brief = job["brief"].strip()
    if not brief:
        raise TransportRefusal("job brief must be non-empty")
    marker = job.get("expect_marker")
    if not marker or not str(marker).strip():
        raise TransportRefusal("job must declare expect_marker for result validation")
    # no secrets in task text, ever (defense in depth; caller must not pass
    # them). Scanned BEFORE redaction (engine output) and AFTER (the exact
    # bytes that will be sent).
    for bad in ("bearer ", "authorization:", "api_key", "secret", "password"):
        if bad in brief.lower():
            raise TransportRefusal("brief appears to contain credential material")
    sent_brief = redact_host_paths(brief)
    for bad in ("bearer ", "authorization:", "api_key", "secret", "password"):
        if bad in sent_brief.lower():
            raise TransportRefusal("brief appears to contain credential material")
    return {
        "job_id": job_id,
        "idempotency_key": job["idempotency_key"],
        "model": model,
        "expect_marker": str(marker),
        # The suffix must not fight the brief's answer format: require the
        # marker on the FINAL line only (observed live: an "exactly one line"
        # suffix made the child drop the brief's content lines).
        "task": (
            f"[engine job {job_id}] Engine role: {role}. Read-only transport task. {sent_brief} "
            "Do not modify any file, host, or configuration. Regardless of "
            f"how many lines you reply with, the LAST line must contain: "
            f"{marker}"
        ),
        "role": role,
        "timeout_ms": int(job.get("timeout_ms", 120_000)),
    }


def client_request_id(job_id: str) -> str:
    """Return a stable correlation key; T3 does not deduplicate by this value."""
    digest = hashlib.sha256(job_id.encode()).hexdigest()[:32]
    return CLIENT_REQ_PREFIX + digest


# --------------------------------------------------------------------------- #
# result validation
# --------------------------------------------------------------------------- #
def validate_result(record: dict, spec: dict, outcome: dict) -> dict:
    """Accept a T3 task outcome only if it is terminal, pinned and marker-true.

    The TRANSPORT contract is: terminal + model-proven + marker present +
    bounded + no pending human stop. Content completeness BEYOND the marker
    (e.g. a brief that asked for two lines and got marker-only) is the
    CALLER's business check — the live probe implements it via its exit code.
    """
    status = outcome.get("status")
    terminal = outcome.get("latestTerminalStatus") or status
    if terminal != "completed" or status != "completed":
        raise TransportRefusal(f"task not completed (status={status!r} terminal={terminal!r})")
    if outcome.get("hasPendingQuestion") or outcome.get("pendingApproval"):
        raise TransportRefusal(
            "task outcome carries a pending human question/approval — "
            "an automated pipeline must not consume it"
        )
    executed = outcome.get("executedModel") or outcome.get("model")
    if not executed:
        # review F4: fail CLOSED — an outcome that cannot prove which model
        # ran must not validate (best-effort pinning was an inert arm).
        raise TransportRefusal("model pin unverifiable: outcome carries no model/executedModel")
    if executed != spec["model"]:
        raise TransportRefusal(f"model pin violation: executed {executed!r} != pinned {spec['model']!r}")
    summary = outcome.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise TransportRefusal("task summary missing/empty")
    if spec["expect_marker"] not in summary:
        raise TransportRefusal(f"result marker {spec['expect_marker']!r} absent from summary")
    if len(summary) > MAX_ASSISTANT_SUMMARY_CHARS:
        raise TransportRefusal("task summary exceeds bounded size")
    return {
        "protocol_version": PROTOCOL,
        "job_id": spec["job_id"],
        "task_id": outcome.get("taskId"),
        "state": S_COMPLETED,
        "executed_model": executed,
        "summary": summary.strip(),
        "validated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# --------------------------------------------------------------------------- #
# the transport
# --------------------------------------------------------------------------- #
class T3Transport:
    """Engine-job -> T3-task transport with durable correlation.

    client: object with delegate(task, *, model, role, client_request_id,
    timeout_ms, expect_marker) -> dict, status(task_id) -> dict,
    cancel(task_id, reason) -> dict. FakeT3Client (tests) or
    HttpT3Client (live probe) implement it.
    """

    def __init__(
        self,
        store: CorrelationStore,
        client,
        *,
        allowed_models: list[str],
        allow_send: bool = False,
        allow_cancel: bool = False,
        recovery_project: str | None = None,
    ):
        self.store = store
        self.client = client
        self.allowed_models = list(allowed_models)
        self.allow_send = bool(allow_send)  # least privilege (LAUNCH_AUTH-like)
        self.allow_cancel = bool(allow_cancel)  # independent gate
        # Optional binding to the project threads launched for THIS
        # transport live in. The launch path uses it when set (instead
        # of scratch), and the reconciliation lookup enumerates ONLY
        # this project — never a wider set. Injected by the
        # launcher/config; never guessed. Legacy records without
        # project_id fall back to full enumeration.
        self.recovery_project = str(recovery_project) if recovery_project else None

    # -- phase 1: durable intent (no network) ------------------------------- #
    def begin_intent(self, job: dict) -> dict:
        spec = build_task_spec(job, allowed_models=self.allowed_models)
        existing = self.store.get(spec["job_id"])
        if existing is not None:
            if existing.get("idempotency_key") != spec["idempotency_key"]:
                raise TransportRefusal("job_id reused with a divergent idempotency_key")
            return existing  # idempotent: never re-plan
        rec = {
            "job_id": spec["job_id"],
            "idempotency_key": spec["idempotency_key"],
            "state": S_INTENT,
            "task_id": None,
            "client_request_id": client_request_id(spec["job_id"]),
            "model": spec["model"],
            "expect_marker": spec["expect_marker"],
            "project_id": self.recovery_project,
            "attempts": 0,
            "history": [{"state": S_INTENT, "utc": _now()}],
        }
        self.store.put(rec)
        return rec

    # -- phase 2: send (durable marker BEFORE the network call) ------------- #
    def send(self, job: dict) -> dict:
        spec = build_task_spec(job, allowed_models=self.allowed_models)
        rec = self.store.get(spec["job_id"])
        if rec is None:
            rec = self.begin_intent(job)
        elif rec.get("idempotency_key") != spec["idempotency_key"]:
            # review F3: enforce on the send() path too, not just begin_intent
            raise TransportRefusal("job_id reused with a divergent idempotency_key")
        if rec["state"] in (S_SENT, S_COMPLETED, S_FAILED, S_CANCELLED):
            return rec  # idempotent: already sent/terminal
        if rec["state"] in (S_SENDING, S_UNCERTAIN):
            # a durable marker from an EARLIER send may have a child
            # already running at T3: sending again would orphan the
            # original reply. Both states mean "outcome unknown".
            raise TransportUncertain("prior send outcome unknown; run reattach() before send()")
        if not self.allow_send:
            raise TransportRefusal(
                "send gate closed (allow_send=False) — engine launch "
                "authorization is required before any delegation"
            )
        # durable marker BEFORE network: a crash from here on is detectable.
        # The per-attempt token is minted here and written with the S_SENDING
        # marker — it exists only in the durable record and in the message
        # the child receives; it is never observable at T3 beforehand, so it
        # cannot be guessed or forged by another thread.
        nonce = secrets.token_hex(16)
        rec["dispatch_nonce"] = nonce
        rec["state"] = S_SENDING
        rec["attempts"] = int(rec.get("attempts", 0)) + 1
        rec["history"].append({"state": S_SENDING, "utc": _now()})
        self.store.put(rec)
        outbound_task = (
            spec["task"].replace(
                " Regardless of how many lines",
                f" Include the exact line `Per-attempt token: {nonce}` "
                "somewhere in your reply. Regardless of how many lines",
                1,
            )
            if " Regardless of how many lines" in spec["task"]
            else spec["task"] + f" Include the exact line "
            f"`Per-attempt token: {nonce}` somewhere "
            "in your reply."
        )
        try:
            outcome = self.client.delegate(
                task=outbound_task,
                model=spec["model"],
                role=spec["role"],
                client_request_id=rec["client_request_id"],
                timeout_ms=spec["timeout_ms"],
                expect_marker=spec["expect_marker"],
                project_id=rec.get("project_id"),
            )
        except Exception as exc:  # outcome unknown => parked
            rec["state"] = S_UNCERTAIN
            rec["error"] = scrub_secret(f"{type(exc).__name__}: {exc}", getattr(self.client, "_token", None))[
                :300
            ]
            rec["history"].append({"state": S_UNCERTAIN, "utc": _now()})
            self.store.put(rec)
            raise TransportUncertain(
                f"send outcome unknown ({rec['error']}); record parked as "
                "uncertain — reconcile via reattach()"
            ) from exc
        task_id = outcome.get("taskId")
        if not task_id:
            rec["state"] = S_UNCERTAIN
            rec["error"] = "delegate returned no taskId"
            rec["history"].append({"state": S_UNCERTAIN, "utc": _now()})
            self.store.put(rec)
            raise TransportUncertain("delegate returned no taskId; parked")
        rec["state"] = S_SENT
        rec["task_id"] = task_id
        # persist the launch's actual project (the reply carries it) so the
        # reconciliation lookup enumerates ONLY that project, never wider
        _raw = outcome.get("raw") or {}
        if _raw.get("projectId"):
            rec["project_id"] = _raw["projectId"]
        rec["history"].append({"state": S_SENT, "task_id": task_id, "utc": _now()})
        self.store.put(rec)
        return rec

    # -- phase 3: reattach after crash / uncertain reconcile ---------------- #
    def reattach(self, job_id: str) -> dict:
        """Reconcile an interrupted send. NEVER re-sends, NEVER re-creates a
        thread, NEVER adopts a thread looked up by title/content alone.

        Installed T3 (0.1.1) does not honor clientRequestId as a duplicate
        guard — every launch creates its own thread (proven). Re-sending on
        an uncertain outcome would create an orphan thread whose output copy
        cannot substitute for the original. The original is equally
        unreachable: the provider (or any T3-write actor) can copy our task
        text — including the attempt's per-attempt token — into its own
        thread, and projection delay/invisibility makes the original
        indistinguishable from a copied impostor. Unique ownership of a
        looked-up thread can therefore NOT be proven by this transport.

        The ONLY identity the transport may trust is a task_id that is itself
        durable in OUR correlation record (known-identity branch below).
        Everything else is DIAGNOSTIC ONLY: the lookup enumerates visible
        projects (or just the bound recovery project, when send() recorded
        one) and reports possible matches in the reconciliation error for the
        owner — it never adopts them. Uncertain sends always park as
        reconciliation-required.

        Bounded evidence gathering: enumeration failures and "projection has
        not landed yet" are retryable (per-record `lookup_pending` counter,
        cap 3 attempts across processes); after the bound the park is
        permanent. Missing metadata (createdAt / send marker / legacy
        record) and ambiguous candidates park immediately.
        """
        rec = self.store.get(job_id)
        if rec is None:
            raise TransportRefusal(f"unknown job_id {job_id!r}")
        if rec["state"] in (S_SENT, S_COMPLETED, S_FAILED, S_CANCELLED):
            return rec
        if rec["state"] == S_INTENT:
            # crash before any network call: safe to send now (nothing left T3)
            return rec
        # S_SENDING (crash between marker and reply) or S_UNCERTAIN (outcome
        # unknown): the record is our only witness.
        if rec.get("task_id"):
            # A known identity is NEVER replaced by a title search. This is
            # the only adoptable case: task_id is part of OUR durable record,
            # so re-polling THAT specific task id is safe reconciliation
            # evidence (projection delays are handled by collect()).
            rec["state"] = S_SENT
            rec["history"].append(
                {"state": S_SENT, "task_id": rec["task_id"], "via": "known-identity", "utc": _now()}
            )
            self.store.put(rec)
            return rec
        marker = self._send_marker_utc(rec)
        if not marker:
            return self._park_reconciliation(rec, "missing S_SENDING marker; cannot scope lookup")
        try:
            outcome = self._lookup_own_thread(rec)
        except TransportReconciliationRequired:
            raise
        except Exception as exc:
            outcome = {"candidates": [], "error": f"lookup raised: {type(exc).__name__}"}
        err = outcome.get("error")
        if err and outcome.get("permanent"):
            return self._park_reconciliation(rec, err)
        candidates = outcome.get("candidates") or []
        if len(candidates) >= 1:
            # Diagnostic evidence only. Adopting would be guessing — copied
            # tokens, delayed projection, foreign projects: ownership cannot be
            # proven locally. The owner reconciles.
            hints = ", ".join(f"{c.get('threadId')} createdAt={c.get('createdAt')}" for c in candidates[:3])
            return self._park_reconciliation(
                rec,
                f"identity not uniquely provable: {len(candidates)} "
                f"candidate(s) match title/marker window [{hints}]; "
                "resolve manually (never adopted automatically)",
            )
        # zero verified candidates, enumeration complete: either projection
        # has not landed (eventual consistency) or it never will — retryable,
        # bounded by a durable per-record counter, then park for reconcile
        MAX_LOOKUP_UNVERIFIED = 3
        pending = int(rec.get("lookup_pending", 0)) + 1
        rec["lookup_pending"] = pending
        err_suffix = f" ({err})" if err else ""
        if pending > MAX_LOOKUP_UNVERIFIED:
            return self._park_reconciliation(
                rec, f"thread identity never became verifiable after " f"{pending - 1} attempts{err_suffix}"
            )
        self.store.put(rec)
        raise TransportUncertain(
            f"identity not yet verifiable{err_suffix} " f"(attempt {pending}); poll again"
        )

    def _send_marker_utc(self, rec: dict) -> str | None:
        """The UTC of THIS send — the durable S_SENDING marker.

        NOT history[0] (that is L_PENDING). S_SENDING is the marker the
        transport writes just before the network call — any thread it created
        must be created strictly after it. Any earlier thread belongs to a
        previous send of the same deterministic job_id.
        """
        for h in rec.get("history") or []:
            if h.get("state") == S_SENDING and h.get("utc"):
                return str(h["utc"])
        return None

    def _park_reconciliation(self, rec: dict, why: str) -> dict:
        rec["state"] = S_UNCERTAIN  # no terminal, no guess
        rec["error"] = f"reconciliation required ({why})"
        rec["history"].append({"state": S_UNCERTAIN, "error": rec["error"], "utc": _now()})
        self.store.put(rec)
        raise TransportReconciliationRequired(rec["error"])

    def _list_all(self, name: str, args: dict, items_key: str) -> list[dict]:
        """Paginate a T3 read tool to EXHAUSTION.

        A single page is a prefix; we can only call the enumeration complete
        when the server returns nextCursor=null. Any deviation — missing
        key, repeated cursor, >200 pages, non-list items — proves nothing
        and the caller parks instead of guessing.
        """
        items: list[dict] = []
        cursor = None
        seen: set = set()
        for _ in range(200):  # hard ceiling, never unbounded
            call = dict(args)
            if cursor is not None:
                call["cursor"] = cursor
            out = self.client._tool(name, call)
            if not isinstance(out, dict):
                raise ValueError(f"{name}: non-dict response")
            page = out.get(items_key)
            if not isinstance(page, list):
                raise ValueError(f"{name}: missing {items_key!r} list")
            for element in page:
                if not isinstance(element, dict):
                    raise ValueError(
                        f"{name}: non-dict page element " f"({type(element).__name__}); wire schema violated"
                    )
            items.extend(page)
            if "nextCursor" not in out:
                raise ValueError(f"{name}: missing nextCursor; " "cannot prove completeness")
            cursor = out["nextCursor"]
            if cursor is None:
                return items
            if not isinstance(cursor, int):
                raise ValueError(f"{name}: unexpected cursor {cursor!r}")
            if cursor in seen:
                raise ValueError(f"{name}: repeated cursor {cursor}")
            seen.add(cursor)
        raise ValueError(f"{name}: exceeded 200 pages")

    def _lookup_own_thread(self, rec: dict) -> dict:
        """Read-only identity lookup for the thread THIS send created.

        ALL of the following must hold, otherwise the send stays parked:
          (i)   the durable S_SENDING marker of THIS send (content token is
                bound to that send — not to the job, not to prior attempts);
          (ii)  complete enumeration of T3 projects and, per project, of
                title-matching threads — pagination to nextCursor=null, no
                truncation ever;
          (iii) exact launch title `engine job <job-id>`;
          (iv)  createdAt present, normalized to ms precision, strictly
                after the S_SENDING marker (same-second included);
          (v)   the thread's assistant content contains BOTH this attempt's
                expect_marker AND this attempt's per-attempt token
                (`Per-attempt token: <128-bit hex>`) — verifiable only by the
                process that sent the message, so another thread cannot
                impersonate ours even with an identical title.

        If the API cannot guarantee any of these (missing metadata, missing
        nextCursor, lookup errors, more matches than one) we park with
        transport-level reconciliation — we NEVER guess.
        """
        job_id = rec.get("job_id") or ""
        expected = f"engine job {job_id}"
        marker = self._send_marker_utc(rec)
        if not marker:
            return {
                "candidates": [],
                "permanent": True,
                "error": "missing S_SENDING marker; cannot scope lookup",
            }
        expect_marker = str(rec.get("expect_marker") or "")
        nonce = str(rec.get("dispatch_nonce") or "")
        if not nonce:
            return {
                "candidates": [],
                "permanent": True,
                "error": ("record predates per-attempt token; " "cannot content-verify — park for reconcile"),
            }
        norm_after = _normalize_ts(marker)

        bound = str(rec.get("project_id") or "")
        if bound:
            # scoped: enumerate ONLY the bound recovery project — never a
            # wider set, even if other projects exist. A thread elsewhere is
            # by definition not provably ours.
            pids = [bound]
        else:
            try:
                projects = self._list_all("t3_project_list", {"limit": 100}, "projects")
            except Exception as exc:
                return {"candidates": [], "error": f"project_list: {exc}"}
            pids = []
            for project in projects:
                pid = (project or {}).get("projectId") or (project or {}).get("id")
                if not pid:
                    return {
                        "candidates": [],
                        "error": (
                            "project_list incomplete: project missing " "id — cannot bound the enumeration"
                        ),
                    }
                pids.append(str(pid))

        suspect_missing_time = 0
        candidates: list[dict] = []
        for pid in pids:
            try:
                threads = self._list_all(
                    "t3_thread_list", {"projectId": pid, "titleContains": expected, "limit": 100}, "threads"
                )
            except Exception as exc:
                return {"candidates": [], "error": f"thread_list[{pid}]: {exc}"}
            for item in threads:
                if not isinstance(item, dict):
                    # unreachable (page elements were checked), but keep the
                    # path retryable rather than raw on defense-in-depth
                    return {"candidates": [], "error": "thread_list: non-dict thread element"}
                if str(item.get("title") or "") != expected:
                    continue  # substring search only narrows
                created = _normalize_ts(str((item or {}).get("createdAt") or ""))
                if not created:
                    # title matches but we cannot order the send — safest is
                    # to park, never adopt.
                    suspect_missing_time += 1
                    continue
                if created < norm_after:
                    continue  # pre-send thread: same job,
                    #                                 older attempt
                candidates.append(item)
        if suspect_missing_time:
            return {
                "candidates": [],
                "permanent": True,
                "error": ("exact-title candidate is missing createdAt; " "cannot prove send order — park"),
            }
        if not candidates:
            return {"candidates": [], "error": None}

        # (v) content verification — the attempt's copyable correlation
        # marker and token echoed in the thread's assistant messages.
        verified: list[dict] = []
        for item in candidates:
            tid = (item or {}).get("threadId")
            if not tid:
                return {"candidates": [], "error": "candidate missing threadId; park"}
            try:
                out = self.client._tool(
                    "t3_thread_read",
                    {
                        "threadId": tid,
                        "view": "messages",
                        "limit": 50,
                        "runLimit": 2,
                        "maxCharsPerItem": MAX_ASSISTANT_ITEM_CHARS,
                    },
                )
            except Exception as exc:
                return {"candidates": [], "error": f"thread_read: {exc}"}
            if "nextCursor" in out and out["nextCursor"] not in (None, 0):
                # more pages of messages; cannot prove full content — park
                return {
                    "candidates": [],
                    "permanent": True,
                    "error": "thread messages paginated; cannot " "prove content completeness — park",
                }
            assistant_messages = [
                entry
                for entry in (out.get("items") or [])
                if isinstance(entry, dict) and entry.get("type") == "assistant_message"
            ]
            if any(
                entry.get("textTruncated")
                or (isinstance(entry.get("text"), str) and len(entry["text"]) >= MAX_ASSISTANT_ITEM_CHARS)
                for entry in assistant_messages
            ):
                return {
                    "candidates": [],
                    "permanent": True,
                    "error": "thread assistant text truncated; cannot prove content completeness — park",
                }
            text = _assistant_text(out)
            if expect_marker in text and f"Per-attempt token: {nonce}" in text:
                verified.append(item)
        return {"candidates": verified, "error": None}

    # -- phase 4: collect + validate --------------------------------------- #
    def collect(self, job_id: str) -> dict:
        rec = self.store.get(job_id)
        if rec is None:
            raise TransportRefusal(f"unknown job_id {job_id!r}")
        if rec["state"] == S_INTENT:
            raise TransportRefusal("job never sent; nothing to collect")
        if rec["state"] in (S_SENDING, S_UNCERTAIN) or not rec.get("task_id"):
            raise TransportUncertain("outcome unknown; run reattach() before collect()")
        if rec["state"] in (S_COMPLETED, S_FAILED, S_CANCELLED):
            return rec
        spec = {
            "job_id": rec["job_id"],
            "model": rec["model"],
            "expect_marker": rec.get("expect_marker") or "",
        }
        outcome = self.client.status(rec["task_id"])
        # IN-FLIGHT: the task exists but has not reached a terminal state.
        # Return the record unchanged (still sent) so the caller can poll —
        # marking it failed here would destroy a healthy delegation.
        if outcome.get("status") in ("preparing", "queued", "starting", "running", "waiting", "idle"):
            return rec
        # TERMINAL-BUT-PROJECTION-MISSING: T3 can report a completed run
        # before the assistant message is projected (observed once). Fail-
        # closed retry with a small bound — never accept an empty result,
        # never hide a genuine malformed one (non-empty but invalid still
        # fails validation below). If the projection never lands, park with
        # an explicit reconciliation-required outcome.
        if (outcome.get("latestTerminalStatus") or outcome.get("status")) == "completed" and not str(
            outcome.get("summary") or ""
        ).strip():
            for _ in range(2):
                time.sleep(2.0)
                outcome = self.client.status(rec["task_id"])
                if (outcome.get("latestTerminalStatus") or outcome.get("status")) != "completed" or str(
                    outcome.get("summary") or ""
                ).strip():
                    break
            if (outcome.get("latestTerminalStatus") or outcome.get("status")) == "completed" and not str(
                outcome.get("summary") or ""
            ).strip():
                rec["state"] = S_UNCERTAIN
                rec["error"] = "terminal-completed but projection missing/empty " "after bounded retry"
                rec["history"].append({"state": S_UNCERTAIN, "error": rec["error"], "utc": _now()})
                self.store.put(rec)
                raise TransportReconciliationRequired(rec["error"])
        try:
            receipt = validate_result(rec, spec, outcome)
        except TransportRefusal as exc:
            rec["state"] = S_FAILED
            rec["error"] = str(exc)[:300]
            rec["history"].append({"state": S_FAILED, "utc": _now()})
            self.store.put(rec)
            raise
        rec.update(
            state=S_COMPLETED,
            receipt=receipt,
            history=rec["history"] + [{"state": S_COMPLETED, "utc": _now()}],
        )
        rec.pop("error", None)  # stale send/reattach error no longer applies
        self.store.put(rec)
        return rec

    # -- scoped cancellation (own correlation only) ------------------------- #
    def cancel(self, job_id: str, reason: str) -> dict:
        rec = self.store.get(job_id)
        if rec is None:
            # SCOPED: we refuse to even name a task we do not correlate
            raise TransportRefusal(
                f"cancel refused: job_id {job_id!r} is not in our correlation " "store (scoped cancellation)"
            )
        if not self.allow_cancel:
            raise TransportRefusal("cancel gate closed (allow_cancel=False)")
        if rec["state"] in (S_COMPLETED, S_FAILED, S_CANCELLED):
            raise TransportRefusal(f"job already terminal ({rec['state']})")
        if not rec.get("task_id"):
            raise TransportUncertain("no correlated task_id yet; reconcile before cancel()")
        self.client.cancel(rec["task_id"], reason=str(reason)[:200])
        rec["state"] = S_CANCELLED
        rec["history"].append({"state": S_CANCELLED, "reason": str(reason)[:200], "utc": _now()})
        self.store.put(rec)
        return rec


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------- #
# live HTTP MCP client (used only by the env-gated real probe)
# --------------------------------------------------------------------------- #
def obtain_mcp_token(
    *,
    base_url: str,
    t3_cli: str,
    scopes: tuple[str, ...] = ("orchestration:read", "orchestration:operate"),
    access: str = "read-only",
    label: str = "wp1-engine-transport",
    env: dict | None = None,
) -> dict:
    """Headless MCP OAuth for the local T3 server (no browser, no human step).

    Flow recovered from the server's own API contract:
      POST /oauth/mcp/register  -> public client_id (PKCE S256)
      POST /oauth/mcp/approval  -> validates the authorization request
      `t3 auth pairing create`  -> one-time pairing credential (CLI = the
                                   documented headless authorization act)
      POST /oauth/mcp/decision  -> {type: "pairing-code", access, code}
                                   -> redirectTo carries the auth code
      POST /oauth/mcp/token     -> Bearer access token (resource-bound to /mcp)

    The pairing credential is SINGLE-USE and is revoked immediately after the
    exchange. `access` is the runtime-mode ceiling for the resulting session
    (read-only => token scope capped to orchestration:read).

    AUTHORITY BASIS (token binding != per-human authentication): minting the
    pairing credential is SAME-OS-USER authority — ANY process running as this
    OS user can call `t3 auth pairing create`. Nothing here proves a specific
    HUMAN approved anything; the credential proves scope/TTL/resource binding
    only. Distinguishing humans within the OS user remains WP3 (the bridge
    principal is likewise config-injected; sessionID is correlation-only).
    Returns the parsed token document plus client_id/verifier/session fields
    needed by HttpT3Client. The caller owns revocation/cleanup of what it
    creates (registered public client is harmless stateless metadata; tokens
    expire by expires_in).
    """
    import base64
    import hashlib
    import subprocess
    import urllib.error
    import urllib.parse
    import urllib.request

    # Network containment first: no request of any kind leaves loopback.
    require_loopback(base_url)

    def post(path: str, payload: dict, headers: dict | None = None, form: bool = False):
        data = (urllib.parse.urlencode(payload) if form else json.dumps(payload)).encode()
        req = urllib.request.Request(
            base_url + path,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded" if form else "application/json",
                "Accept": "application/json",
                **(headers or {}),
            },
        )
        try:
            with _loopback_opener().open(req, timeout=15) as resp:
                return resp.status, json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            try:
                return exc.code, json.loads(body)
            except Exception:
                return exc.code, {"raw": body[:400]}

    redirect = "http://127.0.0.1:8765/cb"
    resource = base_url.rstrip("/") + "/mcp"
    code_status, reg = post(
        "/oauth/mcp/register",
        {
            "client_name": label,
            "redirect_uris": [redirect],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    )
    if code_status not in (200, 201) or "client_id" not in reg:
        raise TransportRefusal(f"mcp client registration failed: {reg}")
    client_id = reg["client_id"]
    verifier = base64.urlsafe_b64encode(os.urandom(48)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip("=")
    authz = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "resource": resource,
    }
    st, appr = post("/oauth/mcp/approval", authz, headers={"authorization": json.dumps(authz)})
    if st != 200:
        raise TransportRefusal(f"mcp approval failed ({st}): {appr}")
    # one-time pairing credential via the local CLI (headless authorization)
    proc = subprocess.run(
        [
            t3_cli,
            "auth",
            "pairing",
            "create",
            *[f"--scope={sc}" for sc in scopes],
            "--ttl",
            "10m",
            "--label",
            label,
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        raise TransportRefusal(f"pairing create failed: {proc.stderr[:300]}")
    pair = json.loads(proc.stdout)
    # discriminant MUST be `_tag` (server-side zod union on { _tag, ... });
    # a `type` key yields HTTP 400 with an empty body.
    decision = {
        "authorization": authz,
        "decision": {"_tag": "pairing-code", "access": access, "code": pair["credential"]},
    }
    try:
        st, dec = post("/oauth/mcp/decision", decision, headers={"authorization": json.dumps(authz)})
    finally:
        # Revoke even if the decision request times out or the connection is
        # lost; otherwise a still-valid pairing code could survive the caller.
        subprocess.run(
            [t3_cli, "auth", "pairing", "revoke", pair["id"]], capture_output=True, timeout=20, env=env
        )
    if st != 200 or "redirectTo" not in dec:
        raise TransportRefusal(f"mcp decision failed ({st}): {dec}")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(dec["redirectTo"]).query)
    auth_code = (query.get("code") or [""])[0]
    if not auth_code:
        raise TransportRefusal("decision produced no authorization code")
    st, tok = post(
        "/oauth/mcp/token",
        {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": resource,
        },
        form=True,
    )
    if st != 200 or "access_token" not in tok:
        raise TransportRefusal(f"mcp token exchange failed ({st}): {tok}")
    tok.update(client_id=client_id, verifier=verifier, pairing_id=pair["id"], resource=resource)
    return tok


class HttpT3Client:
    """Minimal streamable-HTTP MCP client for the local T3 server /mcp.

    The Bearer token lives ONLY in the Authorization header of in-memory
    requests: it is never stored, logged, or embedded in task text.
    """

    def __init__(self, base_url: str, token: str, *, timeout: float = 30.0, provider: str = "opencode"):
        if not token or len(token) < 20:
            raise TransportRefusal("refusing empty/short bearer token")
        if provider not in ("opencode", "codex"):
            raise TransportRefusal(f"unsupported provider: {provider!r}")
        self.provider = provider
        self.base_url = require_loopback(str(base_url)).rstrip("/")
        self._token = token  # in-memory only
        self.timeout = timeout
        self._session_id: str | None = None
        self._id = 0

    # -- plumbing ---------------------------------------------------------- #
    def _post(self, body: dict) -> dict:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            self.base_url + "/mcp",
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {self._token}",
                **({"Mcp-Session-Id": self._session_id} if self._session_id else {}),
            },
        )
        try:
            with _loopback_opener().open(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self._session_id = sid
                raw = resp.read().decode()
        except urllib.error.HTTPError as exc:  # never echo token material
            detail = scrub_secret(exc.read().decode(errors="replace")[:300], self._token)
            raise TransportRefusal(f"T3 /mcp HTTP {exc.code}: {detail}") from None
        if not raw.strip():
            return {}
        ctype = ""  # body may be JSON or SSE (streamable HTTP)
        if raw.lstrip().startswith("{"):
            try:
                return json.loads(raw)
            except ValueError as exc:
                raise TransportRefusal("unparseable MCP JSON body") from exc
        for line in raw.splitlines():  # SSE: data: {...}
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload:
                    return json.loads(payload)
        raise TransportRefusal("unparseable MCP response body")

    def initialize(self) -> dict:
        self._id += 1
        out = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "wp1-engine-transport", "version": "1"},
                },
            }
        )
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return out

    def list_tools(self) -> list[str]:
        self._id += 1
        out = self._post({"jsonrpc": "2.0", "id": self._id, "method": "tools/list", "params": {}})
        return [t["name"] for t in out.get("result", {}).get("tools", [])]

    def _tool(self, name: str, arguments: dict) -> dict:
        self._id += 1
        out = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        if "error" in out:
            detail = scrub_secret(json.dumps(out["error"]), self._token)[:300]
            raise TransportRefusal(f"T3 tool {name} error: {detail}")
        result = out.get("result", {})
        if result.get("isError"):
            detail = scrub_secret(json.dumps(result), self._token)[:300]
            raise TransportRefusal(f"T3 tool {name} reported error: " f"{detail}")
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        return json.loads(texts[0]) if texts else {}

    # -- transport interface ---------------------------------------------- #
    # NOTE on routes (discovered against the live server, documented in the
    # plan): `delegate_task` is THREAD-CREDENTIAL-bound — it "acts as the
    # calling T3 thread" and is refused for MCP clients signing in from
    # outside a thread (`thread_credential_required`), regardless of scope.
    # `t3_thread_launch` is the sanctioned outside-a-thread route; it requires
    # a non-read-only approval ceiling (`capability_denied` under read-only),
    # so the headless flow requests the LEAST-privilege non-read-only level:
    # `approval-required`. The child cannot take unaudited actions either.
    def delegate(
        self, *, task, model, role, client_request_id, timeout_ms, expect_marker, project_id=None
    ) -> dict:
        # (titleContains) can reconcile an orphaned launch by hand, and the
        # server's own guidance ("inspect t3_thread_list before retrying")
        # becomes actionable for our exact job.
        match = re.match(r"\[engine job (job-[0-9a-f]+)\]", task)
        title = f"engine job {match.group(1)}" if match else f"engine transport: {role}"
        launch = {
            "title": title,
            "message": task,
            "modelSelection": {"instanceId": self.provider, "model": model},
            "runtimeMode": "approval-required",  # <= our approved ceiling
            # clientRequestId: NOT deduped on this build (stage-11);
            # reattach reconciles, never re-sends.
            "clientRequestId": client_request_id,
        }
        if project_id:
            # bound recovery project — recovery lookup enumerates ONLY
            # this project, never a wider set
            launch["projectId"] = project_id
        else:
            launch["scratch"] = True  # fresh folder outside any repository
        out = self._tool("t3_thread_launch", launch)
        thread_id = out.get("threadId")
        return {"taskId": thread_id, "raw": out}

    def status(self, task_id: str) -> dict:
        """Normalize t3_thread_read into the transport outcome shape."""
        args = {
            "threadId": task_id,
            "view": "messages",
            "limit": 5,
            "runLimit": 2,
            "maxCharsPerItem": MAX_ASSISTANT_ITEM_CHARS,
        }
        out = self._tool("t3_thread_read", args)
        thread = out.get("thread") or {}
        runs = out.get("recentRuns") or []
        last_run = runs[0] if runs else {}
        items = list(out.get("items") or [])
        # A partial answer is not a terminal result. Bound pagination and
        # refuse an ambiguous or incomplete projection instead of accepting
        # a marker from one page as if it were the whole assistant response.
        seen_positions = set()
        page = out
        for _ in range(9):
            if not page.get("hasMore"):
                break
            position = page.get("nextPosition")
            if not isinstance(position, int) or position in seen_positions:
                raise TransportUncertain("T3 message pagination is incomplete")
            seen_positions.add(position)
            page = self._tool("t3_thread_read", {**args, "afterPosition": position})
            items.extend(page.get("items") or [])
        else:
            if page.get("hasMore"):
                raise TransportUncertain("T3 message pagination exceeded its limit")
        run_id = last_run.get("runId") or thread.get("latestRunId")
        assistant_items = [i for i in items if isinstance(i, dict) and i.get("type") == "assistant_message"]
        if run_id:
            # Responses from prior runs cannot satisfy the current job. If an
            # assistant message lacks a run identity, it cannot be bound safely.
            if any(not i.get("runId") for i in assistant_items):
                raise TransportUncertain("T3 assistant message lacks a run identity")
            assistant_items = [i for i in assistant_items if i["runId"] == run_id]
        if any(
            i.get("textTruncated")
            or (isinstance(i.get("text"), str) and len(i["text"]) >= MAX_ASSISTANT_ITEM_CHARS)
            for i in assistant_items
        ):
            raise TransportUncertain("T3 message text is truncated")
        # capture the ASSISTANT's full answer (all assistant messages joined):
        # taking only the last fragment silently drops earlier result content
        # (observed live: arithmetic line lost, only the marker survived).
        texts = [
            i.get("text") for i in assistant_items if isinstance(i.get("text"), str) and i.get("text").strip()
        ]
        summary = "\n".join(texts)
        if len(summary) > MAX_ASSISTANT_SUMMARY_CHARS:
            raise TransportUncertain("T3 assistant response exceeds the result limit")
        t_status = thread.get("status")  # observed: completed|failed|...
        run_status = last_run.get("status")  # observed: completed|failed|...
        pending = int(thread.get("pendingRequestCount") or 0) > 0
        # observed live shapes: thread.status in
        #   {completed, failed, cancelled, interrupted, running, ...};
        # executedModel may be null with the pin carried in thread/run model.
        terminal = {"completed", "failed", "cancelled", "interrupted", "rolled_back"}
        # `idle` was never observed live; the host schema lists it, so treat
        # it as in-flight (never terminal) rather than failing a healthy thread.
        in_flight = {"preparing", "queued", "starting", "running", "waiting", "idle"}
        if run_status in in_flight or (t_status in in_flight and run_status not in terminal):
            status = t_status if t_status in in_flight else "running"
        elif t_status == "completed" or run_status == "completed":
            status = "completed"
        else:
            status = "failed"
        executed = last_run.get("executedModel")
        configured = last_run.get("model") or thread.get("model")
        return {
            "taskId": task_id,
            "status": status,
            "latestTerminalStatus": (run_status if status in ("completed", "failed") else None),
            "summary": summary,
            "model": configured,
            "executedModel": executed,
            "modelEvidence": "executed" if executed else "configured_only",
            "hasPendingQuestion": pending,
            # thread_read exposes no approval object; pendingRequestCount ->
            # hasPendingQuestion is the LIVE-effective human-stop arm (the
            # pendingApproval arm below is for clients that surface it).
            "pendingApproval": None,
        }

    def cancel(self, task_id: str, reason: str) -> dict:
        return self._tool("t3_thread_interrupt", {"threadId": task_id, "reason": reason})
