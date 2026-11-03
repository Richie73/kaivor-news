"""Typed contracts shared by native and external Kaivor agents."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import json
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AgentPermissions:
    """Explicit task-scoped permissions; all write/action rights default off."""

    read: bool = True
    write: bool = False
    external_actions: bool = False
    access_secrets: bool = False

    def __post_init__(self) -> None:
        for name in ("read", "write", "external_actions", "access_secrets"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"Permission {name} must be a boolean.")
        if self.access_secrets:
            raise ValueError("Agent tasks cannot be granted access to secrets.")

    def requires_approval(self) -> bool:
        return self.write or self.external_actions

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "AgentPermissions":
        if value is None:
            return cls()
        allowed = {"read", "write", "external_actions", "access_secrets"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unknown permission(s): {', '.join(sorted(unknown))}")
        return cls(**{key: item for key, item in value.items()})


@dataclass
class AgentTask:
    """Portable task contract passed between Kaivor and agent adapters."""

    objective: str
    assigned_to: str
    task_type: str = "research"
    constraints: list[str] = field(default_factory=list)
    permissions: AgentPermissions = field(default_factory=AgentPermissions)
    return_format: str = "structured_report"
    metadata: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid4()))
    created_by: str = "kaivor"
    created_at: str = field(default_factory=utc_now)
    approved_by: str | None = None

    def __post_init__(self) -> None:
        self.objective = str(self.objective).strip()
        self.assigned_to = str(self.assigned_to).strip()
        self.task_type = str(self.task_type).strip().lower()
        if not self.objective:
            raise ValueError("Task objective is required.")
        if not self.assigned_to:
            raise ValueError("Task assignee is required.")
        if not self.task_type:
            raise ValueError("Task type is required.")
        if not isinstance(self.permissions, AgentPermissions):
            self.permissions = AgentPermissions.from_dict(self.permissions)
        self.constraints = [str(item).strip() for item in self.constraints if str(item).strip()]
        if not isinstance(self.metadata, dict):
            raise ValueError("Task metadata must be an object.")
        try:
            json.dumps(self.metadata)
        except (TypeError, ValueError) as exc:
            raise ValueError("Task metadata must contain JSON-compatible values.") from exc
        if not self.task_id or not self.created_by.strip():
            raise ValueError("Task identity and creator are required.")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["permissions"] = self.permissions.to_dict()
        return data

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentTask":
        data = dict(value)
        data["permissions"] = AgentPermissions.from_dict(data.get("permissions"))
        return cls(**data)


@dataclass
class AgentResult:
    """Structured, attributable output returned by an agent."""

    agent_id: str
    output: str
    status: str = "completed"
    sources: list[dict[str, str]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    completed_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("Result agent_id is required.")
        if self.status != "completed":
            raise ValueError("Only completed agent results can be accepted.")
        if not isinstance(self.output, str):
            raise ValueError("Agent output must be text.")
        if not isinstance(self.sources, list) or not isinstance(self.actions, list):
            raise ValueError("Sources and actions must be lists.")
        if not isinstance(self.metadata, dict):
            raise ValueError("Result metadata must be an object.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentResult":
        return cls(**value)
