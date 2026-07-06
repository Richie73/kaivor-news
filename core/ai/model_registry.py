"""
Kaivor Model Registry
"""


MODELS = {

    "DeepSeek": {
        "chat": True,
        "coding": True,
        "research": True,
        "writing": True,
        "vision": False,
        "long_context": True,
        "cost": 1,
    },

    "OpenAI": {
        "chat": True,
        "coding": True,
        "research": True,
        "writing": True,
        "vision": True,
        "long_context": True,
        "cost": 3,
    },

    "Anthropic": {
        "chat": True,
        "coding": True,
        "research": True,
        "writing": True,
        "vision": True,
        "long_context": True,
        "cost": 4,
    },

    "Google": {
        "chat": True,
        "coding": True,
        "research": True,
        "writing": True,
        "vision": True,
        "long_context": True,
        "cost": 2,
    },

    "OpenRouter": {
        "chat": True,
        "coding": True,
        "research": True,
        "writing": True,
        "vision": True,
        "long_context": True,
        "cost": 2,
    },

    "Ollama": {
        "chat": True,
        "coding": True,
        "research": True,
        "writing": True,
        "vision": False,
        "long_context": False,
        "cost": 0,
    },
}
