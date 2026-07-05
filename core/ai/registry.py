"""
Kaivor AI Registry
"""

MODELS = {

    "deepseek-free": {
        "provider": "openrouter",
        "free": True,
        "quality": 7,
        "speed": 9,
        "context": 64000,
        "coding": True,
        "vision": False,
    },

    "gemini-2.5-flash": {
        "provider": "google",
        "free": True,
        "quality": 8,
        "speed": 10,
        "context": 1000000,
        "coding": True,
        "vision": True,
    },

    "gpt-5.5": {
        "provider": "openai",
        "free": False,
        "quality": 10,
        "speed": 8,
        "context": 400000,
        "coding": True,
        "vision": True,
    },

    "claude-sonnet": {
        "provider": "anthropic",
        "free": False,
        "quality": 10,
        "speed": 8,
        "context": 200000,
        "coding": True,
        "vision": True,
    },

}


def get_models():
    return MODELS


def get_model(name):
    return MODELS.get(name)


def get_free_models():
    return {
        k: v
        for k, v in MODELS.items()
        if v["free"]
    }


def get_paid_models():
    return {
        k: v
        for k, v in MODELS.items()
        if not v["free"]
    }
