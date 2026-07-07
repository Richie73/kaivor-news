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
    context: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048

    @property
    def messages(self):
        """Return provider-ready messages."""

        messages = []

        if self.system:
            messages.append(
                {
                    "role": "system",
                    "content": self.system,
                }
            )

        if self.context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Knowledge Context:\n\n"
                        f"{self.context}"
                    ),
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
