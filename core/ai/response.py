
"""Standard response returned by Kaivor AI providers."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    """Provider-neutral result from an AI generation call."""

    content: str
    provider: str
    model: str
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
