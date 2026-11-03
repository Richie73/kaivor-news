"""Base interface for pluggable Kaivor agents."""

from abc import ABC, abstractmethod

from core.agents.models import AgentResult, AgentTask


class BaseAgent(ABC):
    """An agent executes one task within the permissions in its contract."""

    agent_id = "unknown"
    display_name = "Unknown agent"

    @abstractmethod
    def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task and return attributable structured output."""
        raise NotImplementedError
