"""TEST-ONLY synthetic enrollment registry and decision layer.

This module models enrollment relationships and fail-closed decisions for a
future protected enrollment authority. It is an in-memory test model only:
synthetic principals, synthetic records and synthetic audit events. It has no
filesystem, SQLite, Engine, Store, registry-database, service or T3 dependency.
Principal identity and administrative authority are inputs from a future verified
boundary; this module does not authenticate or prove human provenance. The
prototype uses a **global admin** model: an `admin` capability is not limited by
`project_scope`. Public dictionaries/record objects are mutable test state, not a
tamper-resistant authority or enforcement boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,95}\Z")
HINT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}\Z")
CAPABILITIES = frozenset({"read", "admin"})
COLLECTION_TYPES = (set, frozenset, tuple, list)


class EnrollmentError(Exception):
    code = "enrollment_error"


class EnrollmentDenied(EnrollmentError):
    code = "forbidden"


class EnrollmentConflict(EnrollmentError):
    code = "conflict"


class EnrollmentInvalid(EnrollmentError):
    code = "invalid_request"


def _id(value: object, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise EnrollmentInvalid(f"Invalid {label}")
    return value


def _hint(value: object) -> str:
    if not isinstance(value, str) or not HINT_RE.fullmatch(value):
        raise EnrollmentInvalid("Invalid repository hint")
    if value.startswith(("/", "\\")) or ".." in value.split("/"):
        raise EnrollmentInvalid("Repository hint must not be a path escape")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _reason(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise EnrollmentInvalid("A bounded reason is required")
    if "\x00" in value:
        raise EnrollmentInvalid("Reason contains a control character")
    return value.strip()


def _principal_collection(values: object, label: str) -> frozenset[str]:
    if not isinstance(values, COLLECTION_TYPES) or isinstance(values, str | bytes):
        raise EnrollmentInvalid(f"Principal {label} must be an explicit collection")
    try:
        return frozenset(values)
    except TypeError as exc:
        raise EnrollmentInvalid(f"Principal {label} contains an invalid value") from exc


def _hints(values: Iterable[str] | None, *, required: bool) -> frozenset[str]:
    if values is None:
        hints = frozenset()
    elif isinstance(values, str):
        raise EnrollmentInvalid("Repository hints must be an explicit sequence")
    else:
        hints = frozenset(_hint(value) for value in values)
    if required and not hints:
        raise EnrollmentInvalid("At least one repository hint is required")
    return hints


@dataclass(frozen=True)
class SyntheticPrincipal:
    """Test input from a future verified boundary; not authentication proof."""

    subject: str
    capabilities: frozenset[str]
    project_scope: frozenset[str]

    def __post_init__(self):
        _id(self.subject, "subject")
        capabilities = _principal_collection(self.capabilities, "capabilities")
        if not capabilities:
            raise EnrollmentInvalid("Principal capabilities are required")
        if not capabilities <= CAPABILITIES:
            raise EnrollmentInvalid("Unsupported principal capability")
        scope = _principal_collection(self.project_scope, "project scope")
        for project in scope:
            _id(project, "project scope")
        # Frozen dataclass plus immutable copies: later mutation of a caller set
        # cannot change authority.
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "project_scope", scope)


@dataclass
class ProjectRecord:
    project_id: str
    repository_hints: frozenset[str]
    active: bool = True
    revision: int = 1


@dataclass
class WorkItemRecord:
    project_id: str
    work_item_id: str
    repository_hints: frozenset[str]
    active: bool = True
    revision: int = 1


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    action: str
    actor: str
    project_id: str
    work_item_id: str | None
    old_work_item_id: str | None
    new_work_item_id: str | None
    reason: str | None
    detail: str
    at: str


@dataclass(frozen=True)
class EnrollmentDecision:
    subject: str
    project_id: str
    work_item_id: str
    repository_hint: str | None
    project_revision: int
    work_item_revision: int


@dataclass
class SyntheticEnrollmentRegistry:
    """In-memory synthetic enrollment store. Never operational authority."""

    __test__ = False

    projects: dict[str, ProjectRecord] = field(default_factory=dict)
    work_items: dict[tuple[str, str], WorkItemRecord] = field(default_factory=dict)
    audit: list[AuditEvent] = field(default_factory=list)
    _sequence: int = 0

    def _event(
        self,
        action: str,
        actor: str,
        project: str,
        item: str | None,
        detail: str,
        *,
        old_item: str | None = None,
        new_item: str | None = None,
        reason: str | None = None,
    ) -> None:
        self._sequence += 1
        self.audit.append(
            AuditEvent(
                self._sequence,
                action,
                actor,
                project,
                item,
                old_item,
                new_item,
                reason,
                detail,
                _now(),
            )
        )

    @staticmethod
    def _require_admin(principal: SyntheticPrincipal) -> None:
        if not isinstance(principal, SyntheticPrincipal):
            raise EnrollmentDenied("Synthetic principal is required")
        if "admin" not in principal.capabilities:
            raise EnrollmentDenied("Administrative authority is required")

    def enroll_project(
        self,
        principal: SyntheticPrincipal,
        project_id: str,
        repository_hints: Iterable[str],
    ) -> ProjectRecord:
        self._require_admin(principal)
        project_id = _id(project_id, "project_id")
        hints = _hints(repository_hints, required=True)
        existing = self.projects.get(project_id)
        if existing is not None:
            if existing.active and existing.repository_hints == hints:
                return existing
            raise EnrollmentConflict("Project is already enrolled with different binding")
        record = ProjectRecord(project_id, hints)
        self.projects[project_id] = record
        self._event("enroll_project", principal.subject, project_id, None, "project enrolled")
        return record

    def rebind_project(
        self,
        principal: SyntheticPrincipal,
        project_id: str,
        repository_hints: Iterable[str],
        reason: str,
    ) -> ProjectRecord:
        self._require_admin(principal)
        project_id = _id(project_id, "project_id")
        hints = _hints(repository_hints, required=True)
        reason = _reason(reason)
        record = self.projects.get(project_id)
        if record is None or not record.active:
            raise EnrollmentDenied("Project is not actively enrolled")
        record.repository_hints = hints
        record.revision += 1
        self._event(
            "rebind_project",
            principal.subject,
            project_id,
            None,
            reason,
            reason=reason,
        )
        return record

    def revoke_project(self, principal: SyntheticPrincipal, project_id: str, reason: str) -> None:
        self._require_admin(principal)
        project_id = _id(project_id, "project_id")
        reason = _reason(reason)
        record = self.projects.get(project_id)
        if record is None or not record.active:
            raise EnrollmentDenied("Project is not actively enrolled")
        record.active = False
        record.revision += 1
        self._event(
            "revoke_project",
            principal.subject,
            project_id,
            None,
            reason,
            reason=reason,
        )

    def re_enroll_project(
        self, principal: SyntheticPrincipal, project_id: str, repository_hints: Iterable[str]
    ) -> ProjectRecord:
        self._require_admin(principal)
        project_id = _id(project_id, "project_id")
        hints = _hints(repository_hints, required=True)
        record = self.projects.get(project_id)
        if record is None or record.active or record.repository_hints != hints:
            raise EnrollmentDenied("Re-enrollment requires the same revoked binding")
        record.active = True
        record.revision += 1
        self._event("re_enroll_project", principal.subject, project_id, None, "re-enrolled")
        return record

    def enroll_work_item(
        self,
        principal: SyntheticPrincipal,
        project_id: str,
        work_item_id: str,
        repository_hints: Iterable[str] | None = None,
    ) -> WorkItemRecord:
        self._require_admin(principal)
        project_id = _id(project_id, "project_id")
        work_item_id = _id(work_item_id, "work_item_id")
        hints = _hints(repository_hints, required=False)
        project = self.projects.get(project_id)
        if project is None or not project.active:
            raise EnrollmentDenied("Project is not actively enrolled")
        key = (project_id, work_item_id)
        existing = self.work_items.get(key)
        if existing is not None:
            if existing.active and existing.repository_hints == hints:
                return existing
            raise EnrollmentConflict("Work item is already enrolled with different binding")
        record = WorkItemRecord(project_id, work_item_id, hints)
        self.work_items[key] = record
        self._event("enroll_work_item", principal.subject, project_id, work_item_id, "work item enrolled")
        return record

    def revoke_work_item(
        self, principal: SyntheticPrincipal, project_id: str, work_item_id: str, reason: str
    ) -> None:
        self._require_admin(principal)
        project_id = _id(project_id, "project_id")
        work_item_id = _id(work_item_id, "work_item_id")
        reason = _reason(reason)
        project = self.projects.get(project_id)
        if project is None or not project.active:
            raise EnrollmentDenied("Project is not actively enrolled")
        record = self.work_items.get((project_id, work_item_id))
        if record is None or not record.active:
            raise EnrollmentDenied("Work item is not actively enrolled")
        record.active = False
        record.revision += 1
        self._event(
            "revoke_work_item",
            principal.subject,
            project_id,
            work_item_id,
            reason,
            reason=reason,
        )

    def replace_work_item(
        self,
        principal: SyntheticPrincipal,
        project_id: str,
        old_work_item_id: str,
        new_work_item_id: str,
        reason: str,
    ) -> WorkItemRecord:
        self._require_admin(principal)
        project_id = _id(project_id, "project_id")
        old_work_item_id = _id(old_work_item_id, "old_work_item_id")
        new_work_item_id = _id(new_work_item_id, "new_work_item_id")
        if old_work_item_id == new_work_item_id:
            raise EnrollmentConflict("Replacement requires a different work item")
        reason = _reason(reason)
        project = self.projects.get(project_id)
        if project is None or not project.active:
            raise EnrollmentDenied("Project is not actively enrolled")
        old = self.work_items.get((project_id, old_work_item_id))
        if old is None or not old.active:
            raise EnrollmentDenied("Old work item is not actively enrolled")
        if (project_id, new_work_item_id) in self.work_items:
            raise EnrollmentConflict("Replacement work item already exists")
        old.active = False
        old.revision += 1
        record = WorkItemRecord(project_id, new_work_item_id, old.repository_hints)
        self.work_items[(project_id, new_work_item_id)] = record
        self._event(
            "replace_work_item",
            principal.subject,
            project_id,
            new_work_item_id,
            reason,
            old_item=old_work_item_id,
            new_item=new_work_item_id,
            reason=reason,
        )
        return record

    def decide(
        self,
        principal: SyntheticPrincipal,
        project_id: str,
        work_item_id: str,
        *,
        repository_hint: str | None = None,
    ) -> EnrollmentDecision:
        if not isinstance(principal, SyntheticPrincipal):
            raise EnrollmentDenied("Synthetic principal is required")
        if "read" not in principal.capabilities:
            raise EnrollmentDenied("Read capability is required")
        project_id = _id(project_id, "project_id")
        work_item_id = _id(work_item_id, "work_item_id")
        if project_id not in principal.project_scope:
            raise EnrollmentDenied("Principal project scope does not include this project")
        project = self.projects.get(project_id)
        if project is None or not project.active:
            raise EnrollmentDenied("Project is unknown or revoked")
        item = self.work_items.get((project_id, work_item_id))
        if item is None or not item.active:
            raise EnrollmentDenied("Work item is unknown or revoked")
        if repository_hint is not None:
            hint = _hint(repository_hint)
            if hint not in project.repository_hints and hint not in item.repository_hints:
                raise EnrollmentDenied("Repository hint is not enrolled for this object")
        return EnrollmentDecision(
            principal.subject,
            project_id,
            work_item_id,
            repository_hint,
            project.revision,
            item.revision,
        )
