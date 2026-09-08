"""
Kaivor AI Resource Manager
"""

from core.ai.settings import get_mode


class AIResourceManager:
    """Select models based on the configured AI mode."""

    def get_mode(self):
        return get_mode()

    def select_model(self):
        mode = self.get_mode()

        model_map = {
            "FREE": "gemini-2.5-flash",
            "ECONOMY": "gemini-2.5-flash",
            "BALANCED": "deepseek-chat",
            "PREMIUM": "openai/gpt-5.5",
        }

        return model_map[mode.name]
