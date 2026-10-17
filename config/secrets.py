"""
Kaivor provider secrets.

Live credentials are read from environment variables first, then from
the local config/news_secrets.json file. Never commit that JSON file.
"""

import json
import os
from pathlib import Path

_SECRETS_FILE = Path(__file__).resolve().parent / "news_secrets.json"


def _load_local_secrets() -> dict:
    try:
        with _SECRETS_FILE.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


_LOCAL_SECRETS = _load_local_secrets()


def _read_key(env_name: str, local_name: str) -> str:
    return (
        os.environ.get(env_name, "").strip()
        or str(_LOCAL_SECRETS.get(local_name, "")).strip()
    )


DEEPSEEK_API_KEY = _read_key("DEEPSEEK_API_KEY", "deepseek")
OPENROUTER_API_KEY = _read_key("OPENROUTER_API_KEY", "openrouter")
OPENAI_API_KEY = _read_key("OPENAI_API_KEY", "openai")
ANTHROPIC_API_KEY = _read_key("ANTHROPIC_API_KEY", "anthropic")
GOOGLE_API_KEY = _read_key("GOOGLE_API_KEY", "google")
