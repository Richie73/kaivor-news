"""FP049 tests for task contracts, persistence, permissions and orchestration."""

import pytest

from core.agents.base import BaseAgent
from core.agents.models import AgentPermissions, AgentResult, AgentTask
from core.agents.orchestrator import AgentOrchestrator
from core.agents.registry import AgentRegistry
from core.agents.store import AgentTaskStore


class StubAgent(BaseAgent):
    agent_id = "stub"
    display_name = "Stub agent"

    def __init__(self, result="verified result", error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def execute(self, task):
        self.calls += 1
        if self.error:
            raise self.error
        return AgentResult(agent_id=self.agent_id, output=self.result)


def build(tmp_path, agent=None):
    registry = AgentRegistry()
    agent = agent or StubAgent()
    registry.register(agent)
    store = AgentTaskStore(tmp_path / "agent_tasks.db")
    return AgentOrchestrator(registry, store), agent


def test_task_contract_round_trip_and_safe_default_permissions():
    task = AgentTask(objective="Research a topic", assigned_to="stub")
    restored = AgentTask.from_dict(task.to_dict())
    assert restored.task_id == task.task_id
    assert restored.permissions.read is True
    assert restored.permissions.write is False
    assert restored.permissions.external_actions is False
    assert restored.permissions.access_secrets is False


def test_registry_rejects_duplicate_agent_ids(tmp_path):
    registry = AgentRegistry()
    registry.register(StubAgent())
    with pytest.raises(ValueError):
        registry.register(StubAgent())


def test_task_is_persisted_and_executes_to_completed(tmp_path):
    orchestrator, agent = build(tmp_path)
    submitted = orchestrator.submit(AgentTask(objective="Research", assigned_to="stub"))
    assert submitted["status"] == "pending"
    completed = orchestrator.run(submitted["task_id"])
    assert completed["status"] == "completed"
    assert completed["result"]["output"] == "verified result"
    assert agent.calls == 1


def test_write_or_external_action_task_waits_for_approval(tmp_path):
    orchestrator, agent = build(tmp_path)
    task = AgentTask(
        objective="Prepare an external action",
        assigned_to="stub",
        permissions=AgentPermissions(write=True),
    )
    submitted = orchestrator.submit(task)
    assert submitted["status"] == "awaiting_approval"
    with pytest.raises(ValueError):
        orchestrator.run(task.task_id)
    assert agent.calls == 0
    with pytest.raises(ValueError):
        orchestrator.approve(task.task_id, " ")
    approved = orchestrator.approve(task.task_id, "user")
    assert approved["status"] == "pending"
    assert approved["task"]["approved_by"] == "user"
    assert orchestrator.run(task.task_id)["status"] == "completed"


def test_external_actions_also_require_approval(tmp_path):
    orchestrator, agent = build(tmp_path)
    task = AgentTask(
        objective="Send a message", assigned_to="stub",
        permissions=AgentPermissions(external_actions=True),
    )
    assert orchestrator.submit(task)["status"] == "awaiting_approval"
    assert agent.calls == 0


def test_agent_failure_is_recorded_without_exception_text(tmp_path):
    orchestrator, _ = build(tmp_path, StubAgent(error=RuntimeError("private token ABC123")))
    task = AgentTask(objective="Fail safely", assigned_to="stub")
    result = orchestrator.run(orchestrator.submit(task)["task_id"])
    assert result["status"] == "failed"
    assert result["error_code"] == "agent_execution_runtimeerror"
    assert "ABC123" not in str(result)


def test_agent_result_identity_must_match_assignee(tmp_path):
    class WrongAgent(StubAgent):
        def execute(self, task):
            return AgentResult(agent_id="other", output="bad")
    orchestrator, _ = build(tmp_path, WrongAgent())
    task = AgentTask(objective="Check identity", assigned_to="stub")
    result = orchestrator.run(orchestrator.submit(task)["task_id"])
    assert result["status"] == "failed"
    assert result["error_code"] == "agent_execution_valueerror"


def test_completed_task_cannot_be_executed_twice(tmp_path):
    orchestrator, agent = build(tmp_path)
    task = AgentTask(objective="One shot", assigned_to="stub")
    task_id = orchestrator.submit(task)["task_id"]
    orchestrator.run(task_id)
    with pytest.raises(ValueError):
        orchestrator.run(task_id)
    assert agent.calls == 1


def test_unknown_assignee_is_rejected_before_persistence(tmp_path):
    orchestrator, _ = build(tmp_path)
    task = AgentTask(objective="No such agent", assigned_to="missing")
    with pytest.raises(ValueError):
        orchestrator.submit(task)
    assert orchestrator.list() == []


def test_secret_access_is_never_granted_to_agents():
    with pytest.raises(ValueError):
        AgentPermissions(access_secrets=True)


def test_permission_values_must_be_booleans():
    with pytest.raises(TypeError):
        AgentPermissions.from_dict({"write": "false"})


def test_non_json_task_metadata_is_rejected():
    with pytest.raises(ValueError):
        AgentTask(objective="Invalid metadata", assigned_to="stub", metadata={"bad": object()})
