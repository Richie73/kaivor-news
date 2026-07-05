"""
Kaivor AI Request
"""

from dataclasses import dataclass, field


@dataclass
class AIRequest:
    """Standard request passed to all AI providers."""

    user: str
    system: str = ""
    history: list = field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int = 2048

    @property
    def messages(self):
        messages = []

        if self.system:
            messages.append(
                {
                    "role": "system",
                    "content": self.system,
                }
            )

        messages.extend(self.history)

        messages.append(
            {
                "role": "user",
                "content": self.user,
            }
        )

        return messages
