"""Adapter exposing Kaivor's existing AI engine as a pluggable agent."""

from core.agents.base import BaseAgent
from core.agents.models import AgentResult, AgentTask


class KaivorAIAgent(BaseAgent):
    agent_id = "kaivor_ai"
    display_name = "Kaivor AI"
    agent_type = "native"

    def __init__(self, executor=None) -> None:
        # Injection keeps tests offline and avoids initialising providers until needed.
        self._executor = executor

    def execute(self, task: AgentTask) -> AgentResult:
        if self._executor is None:
            from core.ai.engine import AIEngine
            self._executor = AIEngine()

        prompt = [
            "Execute the following delegated task as Kaivor's native AI agent.",
            f"Task type: {task.task_type}",
            f"Objective: {task.objective}",
            "Constraints:",
            *(f"- {item}" for item in task.constraints),
            f"Required return format: {task.return_format}",
            "Do not claim to have performed external actions. Clearly identify uncertainty and missing evidence.",
        ]
        if hasattr(self._executor, "ask"):
            output = self._executor.ask("research", "\n".join(prompt))
        else:
            output = self._executor(task, "\n".join(prompt))
        return AgentResult(agent_id=self.agent_id, output=str(output))
