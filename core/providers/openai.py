from core.ai.base import AIProvider


class OpenAIProvider(AIProvider):

    @property
    def name(self):
        return "OpenAI"

    @property
    def enabled(self):
        return False

    def generate(self, prompt: str):
        raise NotImplementedError
