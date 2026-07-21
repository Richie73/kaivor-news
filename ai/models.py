
"""
Kaivor AI Models

Central registry of supported AI models.
"""

MODELS = {

    # Default ultra-cheap model
    "default": "deepseek/deepseek-v4-flash",

    # General purpose
    "fast": "deepseek/deepseek-v4-flash",

    # Heavy reasoning
    "reasoning": "anthropic/claude-sonnet-4",

    # Vision / OCR
    "vision": "google/gemini-2.5-flash",

    # Highest quality fallback
    "premium": "openai/gpt-5",
}


TASK_ROUTING = {

    "chat": "default",

    "coding": "fast",

    "vision": "vision",

    "ocr": "vision",

    "reasoning": "reasoning",

    "fallback": "premium",
}


def get_model(task="chat"):

    key = TASK_ROUTING.get(task, "default")

    return MODELS[key]