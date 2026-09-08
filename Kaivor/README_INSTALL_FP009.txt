KAIVOR FP009 — OPENROUTER PROVIDER

Milestone: FP009
Version: 0.9.64

Purpose:
Implement real OpenRouter generation through Kaivor's shared AIRequest/provider
architecture, while keeping DeepSeek as the configured primary provider and
OpenRouter as the next fallback.

OpenRouter model:
  openrouter/auto

The model is configurable in:
  config/ai.json

It can also be temporarily overridden with:
  KAIVOR_OPENROUTER_MODEL

IMPORTANT:
Do NOT overwrite config/secrets.py.

To use OpenRouter, put the key in your existing local config/secrets.py:
  OPENROUTER_API_KEY = "your-key"

Validation:
  cd /storage/emulated/0/Download/KAIVOR/Kaivor
  python tools/validate_fp009.py

Do not change task_routing.json yet. FP009 deliberately keeps DeepSeek as
primary so OpenRouter is validated first as a genuine fallback provider.

After validation passes, test provider failover and then snapshot the project.
