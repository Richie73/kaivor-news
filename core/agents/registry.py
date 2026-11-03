"""In-process registry for native and external agent adapters."""

from core.agents.base import BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        agent_id = str(getattr(agent, "agent_id", "")).strip()
        if not agent_id or agent_id == "unknown":
            raise ValueError("Agent must define a stable agent_id.")
        if not callable(getattr(agent, "execute", None)):
            raise TypeError("Agent must implement execute(task).")
        if agent_id in self._agents:
            raise ValueError(f"Agent already registered: {agent_id}")
        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def list(self) -> list[dict[str, str]]:
        return [
            {
                "agent_id": agent.agent_id,
                "display_name": str(getattr(agent, "display_name", agent.agent_id)),
                "type": str(getattr(agent, "agent_type", "native")),
            }
            for agent in sorted(self._agents.values(), key=lambda item: item.agent_id)
        ]
