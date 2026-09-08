"""
Kaivor Prompt Builder
"""

from core.ai.prompts import SYSTEM_PROMPT, TASK_PROMPTS


class PromptBuilder:
    """Builds prompts for AI providers."""

    def build(
        self,
        task: str,
        user: str,
        history=None,
        context="",
    ):
        """Build a provider-ready message list."""

        if history is None:
            history = []

        task_prompt = TASK_PROMPTS.get(task, "")

        messages = []

        if SYSTEM_PROMPT:
            messages.append(
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.strip(),
                }
            )

        if task_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": task_prompt,
                }
            )

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Knowledge Context:\n\n"
                        f"{context}"
                    ),
                }
            )

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": user,
            }
        )

        return messages
