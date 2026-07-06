"""
Kaivor Model Information
"""

from core.ai.model_registry import MODELS


class ModelRegistry:

    def all(self):
        return MODELS

    def get(self, provider):
        return MODELS.get(provider)

    def supports(self, provider, capability):

        model = self.get(provider)

        if not model:
            return False

        return model.get(capability, False)

    def recommend(self, capability):

        candidates = []

        for provider, info in MODELS.items():

            if info.get(capability, False):

                candidates.append(
                    (
                        info.get("cost", 999),
                        provider,
                    )
                )

        if not candidates:
            return None

        candidates.sort()

        return candidates[0][1]
