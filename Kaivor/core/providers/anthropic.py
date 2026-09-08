from core.ai.base import AIProvider


class AnthropicProvider(AIProvider):

    @property
    def name(self):
        return "Anthropic"

    @property
    def enabled(self):
        return False

    def generate(self, prompt: str):
        raise NotImplementedError
