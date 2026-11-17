"""TEST-ONLY O01 provenance design prototype.

This module is not authentication and must never be imported by an ingress,
service listener or login route. It models the verification *semantics* required
by the accepted plan (authenticated principal, actor class, audience, lifetime,
replay, revocation, request binding) using a symmetric test key so WP1 acceptance
tests can be reviewed offline.

Production still requires a selected mechanism (for example OIDC/signed
assertions or mTLS plus an owner session), managed asymmetric keys, a durable
replay/revocation store and a real T3 ingress. A test HMAC key proves neither
key custody nor real human presence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .contract import ID, VERSION
from .offline import Denied
from .offline import timestamp as valid_timestamp

ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}\Z")
HASH_RE = re.compile(r"[a-f0-9]{64}\Z")

ACTOR_CLASSES = ("human", "agent", "monitor", "maintenance")
AUTH_METHODS = ("test_hmac", "local_password", "t3_session", "t3_sso")
ASSURANCES = ("single_factor", "multi_factor")
CAPABILITIES = ("read", "create", "decide", "execute", "lifecycle", "observe", "result")
HUMAN_ONLY = frozenset({"decide", "lifecycle"})
MONITOR_ONLY = frozenset({"observe", "result"})

CLAIM_FIELDS = (
    "schema_version",
    "issuer",
    "key_id",
    "audience",
    "subject",
    "actor_class",
    "project_id",
    "work_item_id",
    "capabilities",
    "auth_method",
    "assurance",
    "session_id",
    "job_id",
    "operation",
    "target_id",
    "request_hash",
    "issued_at",
    "expires_at",
    "jti",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sign(claims: Mapping[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical(dict(claims)), hashlib.sha256).hexdigest()


def _require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise Denied("invalid_request", f"Invalid {field}")
    return value


def _require_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise Denied("invalid_request", f"Invalid {field}")
    return value


def _require_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not valid_timestamp(value):
        raise Denied("invalid_request", f"Invalid {field}")
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00"))


def _shape_claims(claims: Any) -> dict[str, Any]:
    if not isinstance(claims, dict) or set(claims) != set(CLAIM_FIELDS):
        raise Denied("unauthenticated", "Unknown or missing assertion fields")
    if claims["schema_version"] != VERSION:
        raise Denied("unsupported_version")
    for field in (
        "issuer",
        "key_id",
        "audience",
        "subject",
        "project_id",
        "work_item_id",
        "session_id",
        "operation",
        "target_id",
        "jti",
    ):
        _require_id(claims[field], field)
    if claims["actor_class"] not in ACTOR_CLASSES:
        raise Denied("forbidden", "Unknown actor class")
    if claims["auth_method"] not in AUTH_METHODS or claims["assurance"] not in ASSURANCES:
        raise Denied("forbidden", "Unsupported authentication method or assurance")
    capabilities = claims["capabilities"]
    if (
        not isinstance(capabilities, list)
        or not 1 <= len(capabilities) <= len(CAPABILITIES)
        or len(set(capabilities)) != len(capabilities)
        or any(c not in CAPABILITIES for c in capabilities)
    ):
        raise Denied("forbidden", "Invalid capability set")
    job_id = claims["job_id"]
    if job_id is not None and (not isinstance(job_id, str) or not ID_RE.fullmatch(job_id)):
        raise Denied("invalid_request", "Invalid job binding")
    if claims["actor_class"] == "monitor" and job_id is None:
        raise Denied("forbidden", "Monitor assertion requires a job binding")
    if claims["actor_class"] != "monitor" and job_id is not None:
        raise Denied("forbidden", "Non-monitor assertion cannot carry a job binding")
    _require_hash(claims["request_hash"], "request_hash")
    issued = _require_time(claims["issued_at"], "issued_at")
    expires = _require_time(claims["expires_at"], "expires_at")
    if expires <= issued:
        raise Denied("invalid_request", "Assertion expiry must follow issue time")
    return dict(claims)


@dataclass(frozen=True)
class VerifiedPrincipal:
    """Verified claims only; never deserialize this from caller JSON."""

    issuer: str
    subject: str
    actor_class: str
    project_id: str
    work_item_id: str
    capabilities: frozenset[str]
    auth_method: str
    assurance: str
    session_id: str
    job_id: str | None
    operation: str
    target_id: str
    request_hash: str
    jti: str
    expires_at: datetime


class TestAssertionIssuer:
    """Test-only signer. A shared HMAC key is not a production trust design."""

    __test__ = False

    def __init__(
        self,
        keys: Mapping[str, bytes],
        issuer: str = "test-issuer",
        audience: str = "engineering-control",
    ):
        if not keys:
            raise ValueError("At least one test key is required")
        self.keys = dict(keys)
        self.issuer = issuer
        self.audience = audience

    def issue(
        self,
        *,
        key_id: str = "k1",
        subject: str = "owner",
        actor_class: str = "human",
        project_id: str = "project-1",
        work_item_id: str = "work-1",
        capabilities: tuple[str, ...] = ("read", "decide", "lifecycle"),
        auth_method: str = "t3_sso",
        assurance: str = "multi_factor",
        session_id: str = "session-1",
        job_id: str | None = None,
        operation: str = "decisions",
        target_id: str = "work-1",
        request_hash: str = "a" * 64,
        now: datetime | None = None,
        lifetime_seconds: int = 120,
        **overrides: Any,
    ) -> dict[str, Any]:
        issued = now or datetime.now(timezone.utc)
        claims: dict[str, Any] = {
            "schema_version": VERSION,
            "issuer": self.issuer,
            "key_id": key_id,
            "audience": self.audience,
            "subject": subject,
            "actor_class": actor_class,
            "project_id": project_id,
            "work_item_id": work_item_id,
            "capabilities": list(capabilities),
            "auth_method": auth_method,
            "assurance": assurance,
            "session_id": session_id,
            "job_id": job_id,
            "operation": operation,
            "target_id": target_id,
            "request_hash": request_hash,
            "issued_at": issued.isoformat().replace("+00:00", "Z"),
            "expires_at": (issued + timedelta(seconds=lifetime_seconds)).isoformat().replace("+00:00", "Z"),
            "jti": "jti-1",
        }
        claims.update(overrides)
        return {"claims": claims, "signature": sign(claims, self.keys[key_id])}


class ProvenanceVerifier:
    """Offline verifier for the proposed assertion-envelope design.

    Order: strict shape -> signature -> trusted issuer -> audience -> lifetime ->
    request/operation/target/object binding -> revocation -> replay identity.
    The decision-assurance rule is a proposed default and remains an owner policy
    choice, not an established production control.
    """

    __test__ = False

    def __init__(
        self,
        keys_by_issuer: Mapping[str, Mapping[str, bytes]],
        *,
        audience: str = "engineering-control",
        trusted_issuers: tuple[str, ...] = ("test-issuer",),
        max_lifetime_seconds: int = 300,
        clock_skew_seconds: int = 30,
        decision_assurance: str = "multi_factor",
    ):
        self.keys_by_issuer = {issuer: dict(keys) for issuer, keys in keys_by_issuer.items()}
        self.audience = audience
        self.trusted_issuers = frozenset(trusted_issuers)
        self.max_lifetime_seconds = max_lifetime_seconds
        self.clock_skew_seconds = clock_skew_seconds
        self.decision_assurance = decision_assurance
        self._seen: dict[tuple[str, str, str], str] = {}
        self._revoked_subjects: set[tuple[str, str]] = set()
        self._revoked_sessions: set[tuple[str, str]] = set()

    def revoke_subject(self, issuer: str, subject: str) -> None:
        self._revoked_subjects.add((issuer, subject))

    def revoke_session(self, issuer: str, session_id: str) -> None:
        self._revoked_sessions.add((issuer, session_id))

    def verify(
        self,
        envelope: Any,
        *,
        expected_operation: str,
        expected_target: str,
        expected_request_hash: str,
        expected_project: str | None = None,
        expected_work_item: str | None = None,
        now: datetime | None = None,
    ) -> VerifiedPrincipal:
        if not isinstance(envelope, dict) or set(envelope) != {"claims", "signature"}:
            raise Denied("unauthenticated", "Unknown assertion envelope fields")
        claims = _shape_claims(envelope["claims"])
        signature = envelope["signature"]
        _require_hash(signature, "signature")

        issuer = claims["issuer"]
        if issuer not in self.keys_by_issuer or issuer not in self.trusted_issuers:
            raise Denied("unauthenticated", "Untrusted assertion issuer")
        key = self.keys_by_issuer[issuer].get(claims["key_id"])
        if key is None:
            raise Denied("unauthenticated", "Unknown assertion key")
        if not hmac.compare_digest(signature, sign(claims, key)):
            raise Denied("unauthenticated", "Assertion signature mismatch")

        if claims["audience"] != self.audience:
            raise Denied("unauthenticated", "Assertion audience mismatch")

        current = now or datetime.now(timezone.utc)
        issued = datetime.fromisoformat(claims["issued_at"].upper().replace("Z", "+00:00"))
        expires = datetime.fromisoformat(claims["expires_at"].upper().replace("Z", "+00:00"))
        skew = timedelta(seconds=self.clock_skew_seconds)
        if issued > current + skew:
            raise Denied("unauthenticated", "Assertion not yet valid")
        if expires < current - skew or current > expires + skew:
            raise Denied("unauthenticated", "Assertion expired")
        if (expires - issued).total_seconds() > self.max_lifetime_seconds:
            raise Denied("unauthenticated", "Assertion lifetime exceeds policy")

        if (
            claims["operation"] != expected_operation
            or claims["target_id"] != expected_target
            or claims["request_hash"] != expected_request_hash
        ):
            raise Denied("conflict", "Assertion is not bound to this request")
        if expected_project is not None and claims["project_id"] != expected_project:
            raise Denied("forbidden", "Assertion project mismatch")
        if expected_work_item is not None and claims["work_item_id"] != expected_work_item:
            raise Denied("forbidden", "Assertion work-item mismatch")

        if (issuer, claims["subject"]) in self._revoked_subjects:
            raise Denied("unauthenticated", "Principal revoked")
        if (issuer, claims["session_id"]) in self._revoked_sessions:
            raise Denied("unauthenticated", "Session revoked")

        replay_key = (issuer, claims["key_id"], claims["jti"])
        # Replay identity binds the complete canonical signed claim set, not a
        # subset. Two signed assertions sharing a jti but differing in project,
        # work item, actor class, capabilities, assurance, auth method, session,
        # job or expiry are not the same request.
        identity = digest(claims)
        prior = self._seen.get(replay_key)
        if prior is not None and prior != identity:
            raise Denied("conflict", "Assertion replay with different request")
        self._seen[replay_key] = identity

        return VerifiedPrincipal(
            issuer=issuer,
            subject=claims["subject"],
            actor_class=claims["actor_class"],
            project_id=claims["project_id"],
            work_item_id=claims["work_item_id"],
            capabilities=frozenset(claims["capabilities"]),
            auth_method=claims["auth_method"],
            assurance=claims["assurance"],
            session_id=claims["session_id"],
            job_id=claims["job_id"],
            operation=claims["operation"],
            target_id=claims["target_id"],
            request_hash=claims["request_hash"],
            jti=claims["jti"],
            expires_at=expires,
        )

    def authorize(self, principal: VerifiedPrincipal, capability: str, *, job_id: str | None = None) -> None:
        """Capability/actor-class check after verification; not a substitute for it."""
        if capability not in CAPABILITIES:
            raise Denied("invalid_request", "Unknown capability")
        if capability not in principal.capabilities:
            raise Denied("forbidden", "Capability not granted")
        if principal.actor_class == "monitor" and capability not in MONITOR_ONLY:
            raise Denied("forbidden", "Monitor cannot perform this operation")
        if capability in MONITOR_ONLY:
            if principal.actor_class != "monitor" or principal.job_id is None:
                raise Denied("forbidden", "Observation requires a monitor principal")
            if job_id is not None and job_id != principal.job_id:
                raise Denied("forbidden", "Monitor is not bound to this job")
        if capability in HUMAN_ONLY and principal.actor_class != "human":
            raise Denied("forbidden", "Human-only capability")
        if capability == "decide" and principal.assurance != self.decision_assurance:
            raise Denied("forbidden", "Decision requires stronger authentication assurance")
