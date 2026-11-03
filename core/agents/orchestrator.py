"""Permission-aware task submission and execution for Kaivor agents."""

from datetime import datetime, timezone
from typing import Any

from core.agents.models import AgentResult, AgentTask
from core.agents.registry import AgentRegistry
from core.agents.store import AgentTaskStore


class AgentOrchestrator:
    """Coordinates registered agents without coupling to a specific provider."""

    def __init__(self, registry: AgentRegistry | None = None, store: AgentTaskStore | None = None) -> None:
        self.registry = registry or AgentRegistry()
        self.store = store or AgentTaskStore()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def submit(self, task: AgentTask) -> dict[str, Any]:
        if not isinstance(task, AgentTask):
            raise TypeError("submit() requires an AgentTask.")
        if self.registry.get(task.assigned_to) is None:
            raise ValueError(f"Unknown agent: {task.assigned_to}")
        status = "awaiting_approval" if task.permissions.requires_approval() else "pending"
        self.store.create(task.to_dict(), status)
        return self.store.get(task.task_id)

    def approve(self, task_id: str, approved_by: str) -> dict[str, Any]:
        approver = str(approved_by).strip()
        if not approver:
            raise ValueError("An approver identity is required.")
        record = self.store.get(task_id)
        if record is None:
            raise KeyError(f"Unknown task: {task_id}")
        if record["status"] != "awaiting_approval":
            raise ValueError("Only tasks awaiting approval can be approved.")
        task = AgentTask.from_dict(record["task"])
        task.approved_by = approver
        self.store.update(
            task_id, "pending", task=task.to_dict(), updated_at=self._now(),
            expected_status="awaiting_approval",
        )
        return self.store.get(task_id)

    def run(self, task_id: str) -> dict[str, Any]:
        record = self.store.get(task_id)
        if record is None:
            raise KeyError(f"Unknown task: {task_id}")
        if record["status"] != "pending":
            raise ValueError(f"Task cannot run from status: {record['status']}")

        task = AgentTask.from_dict(record["task"])
        if task.permissions.requires_approval() and not task.approved_by:
            raise PermissionError("Task requires explicit approval before execution.")

        agent = self.registry.get(task.assigned_to)
        if agent is None:
            self.store.update(
                task_id, "failed", error_code="agent_unavailable", updated_at=self._now(),
                expected_status="pending",
            )
            return self.store.get(task_id)

        # Conditional state transition prevents two workers executing the same task.
        self.store.update(
            task_id, "running", updated_at=self._now(), expected_status="pending"
        )
        try:
            result = agent.execute(task)
            if not isinstance(result, AgentResult):
                raise TypeError("Agent must return an AgentResult.")
            if result.agent_id != task.assigned_to:
                raise ValueError("Agent result identity does not match the assigned agent.")
            self.store.update(
                task_id, "completed", result=result.to_dict(), updated_at=self._now(),
                expected_status="running",
            )
        except Exception as exc:
            # Persist only a stable error class, never arbitrary exception text or credentials.
            error_code = f"agent_execution_{type(exc).__name__.lower()}"
            self.store.update(
                task_id, "failed", error_code=error_code, updated_at=self._now(),
                expected_status="running",
            )
        return self.store.get(task_id)

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self.store.get(task_id)

    def list(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        return self.store.list(limit=limit, status=status)
