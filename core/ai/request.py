"""
Kaivor AI Request
"""

from dataclasses import dataclass, field


@dataclass
class AIRequest:
    """Standard request passed to all AI providers."""

    # FP108: user defaults to "" so direct_messages callers (the
    # chat hub) need not pass a dummy user string.
    user: str = ""
    system: str = ""
    history: list = field(default_factory=list)
    context: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048
    # FP108: two bridges for callers whose messages are already
    # provider-shaped. direct_messages passes the list through
    # verbatim (the chat hub's validated history). image_data_url
    # makes the user message multimodal (the receipt reader's
    # photo); the text part is still `user`.
    direct_messages: list = None
    image_data_url: str = ""

    @property
    def messages(self):
        """Return provider-ready messages."""

        if self.direct_messages is not None:
            return list(self.direct_messages)

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

        if self.image_data_url:
            content = [
                {"type": "text", "text": self.user},
                {"type": "image_url", "image_url": {"url": self.image_data_url}},
            ]
        else:
            content = self.user

        messages.append(
            {
                "role": "user",
                "content": content,
            }
        )

        return messages
