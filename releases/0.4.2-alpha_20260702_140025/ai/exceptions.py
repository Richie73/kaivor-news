"""
Kaivor AI Exceptions
"""


class AIError(Exception):
    pass


class ProviderError(AIError):
    pass


class ConfigurationError(AIError):
    pass