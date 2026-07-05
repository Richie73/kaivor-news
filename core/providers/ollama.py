from core.ai.base import AIProvider


class OllamaProvider(AIProvider):

    @property
    def name(self):
        return "Ollama"

    @property
    def enabled(self):
        return False

    def generate(self, prompt: str):
        raise NotImplementedError
