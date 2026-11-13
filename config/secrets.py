"""Provider credentials loaded from private local storage.

Priority: environment variables > private user store. Legacy project files are never read.
Never log or return credentials from diagnostic helpers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_PRIVATE_FILE = Path.home() / ".config" / "kaivor" / "news_secrets.json"

_PROVIDER_ENV = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "guardian": "GUARDIAN_API_KEY",
    "brave": "BRAVE_API_KEY",
    "newsdata": "NEWSDATA_API_KEY",
}


def _read_dict(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _read_key(env_name: str, local_name: str) -> str:
    """Read one key without exposing its value in logs or errors."""
    env_value = os.environ.get(env_name, "").strip()
    if env_value:
        return env_value
    private_value = str(_read_dict(_PRIVATE_FILE).get(local_name, "")).strip()
    if private_value:
        return private_value
    return ""


def get_provider_key(provider: str) -> str:
    """Return a provider key using the environment/private-store order."""
    provider = str(provider).strip().lower()
    env_name = _PROVIDER_ENV.get(provider)
    if not env_name:
        return ""
    return _read_key(env_name, provider)


def credential_source(provider: str) -> str:
    """Return source metadata only; never return a credential or its fragment."""
    provider = str(provider).strip().lower()
    env_name = _PROVIDER_ENV.get(provider)
    if not env_name:
        return "unsupported"
    if os.environ.get(env_name, "").strip():
        return "environment"
    if str(_read_dict(_PRIVATE_FILE).get(provider, "")).strip():
        return "private"
    return "missing"


DEEPSEEK_API_KEY = get_provider_key("deepseek")
OPENROUTER_API_KEY = get_provider_key("openrouter")
OPENAI_API_KEY = get_provider_key("openai")
ANTHROPIC_API_KEY = get_provider_key("anthropic")
GOOGLE_API_KEY = get_provider_key("google")
GUARDIAN_API_KEY = get_provider_key("guardian")
BRAVE_API_KEY = get_provider_key("brave")
NEWSDATA_API_KEY = get_provider_key("newsdata")
