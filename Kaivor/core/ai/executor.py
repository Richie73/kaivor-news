"""
Kaivor Parallel AI Executor
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from core.config import Config


class ParallelExecutor:
    """Execute AI providers."""

    def __init__(self):
        self.config = Config()

    def enabled(self):
        return self.config.get(
            "parallel_execution",
            False,
        )

    def workers(self):
        return self.config.get(
            "parallel_workers",
            4,
        )

    def execute(self, providers, request):

        if not self.enabled():

            provider = providers[0]

            return (
                provider,
                provider.generate(request),
            )

        with ThreadPoolExecutor(
            max_workers=self.workers(),
        ) as executor:

            futures = {
                executor.submit(
                    provider.generate,
                    request,
                ): provider
                for provider in providers
            }

            for future in as_completed(futures):

                provider = futures[future]

                try:
                    return (
                        provider,
                        future.result(),
                    )

                except Exception:
                    continue

        raise RuntimeError(
            "All providers failed."
        )
