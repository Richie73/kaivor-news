from core.ai.base import AIProvider


class GoogleProvider(AIProvider):

    @property
    def name(self):
        return "Google"

    @property
    def enabled(self):
        return False

    def generate(self, prompt: str):
        raise NotImplementedError
