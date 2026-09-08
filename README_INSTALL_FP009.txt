
KAIVOR FP009 — PROVIDER INDEPENDENCE
====================================

SOURCE
------
Built from the clean FP008 project snapshot.

WHAT THIS BUNDLE ADDS
---------------------
- Working OpenRouter provider using Kaivor AIRequest.
- Configurable OpenRouter model; default: openrouter/auto.
- Provider/model/usage metadata.
- Provider failover diagnostics.
- Full OpenAI-style conversation history through the Kaivor API.
- FP009 regression and validation tests.

IMPORTANT: SECRETS
------------------
This bundle intentionally does NOT contain config/secrets.py.
Do NOT delete or overwrite your existing config/secrets.py.

OpenRouter can use either:
    export OPENROUTER_API_KEY='your-key'

or the existing local config/secrets.py value.

OPTIONAL MODEL OVERRIDE
-----------------------
    export KAIVOR_OPENROUTER_MODEL='openrouter/auto'

INSTALL — ANDROID / TERMUX
--------------------------
Live project root:
    /storage/emulated/0/Download/KAIVOR/Kaivor

1. Stop the currently running Kaivor API first if it is running.
2. Extract this ZIP directly into the project root and allow overwrite.

    unzip -o /storage/emulated/0/Download/Kaivor_FP009_Provider_Independence.zip \
      -d /storage/emulated/0/Download/KAIVOR/Kaivor

3. Validate FP009:

    cd /storage/emulated/0/Download/KAIVOR/Kaivor
    python tools/validate_fp009.py

4. Start Kaivor API:

    python kaivor.py api

5. Quick API checks:

    curl http://127.0.0.1:8088/health
    curl http://127.0.0.1:8088/v1/models

Open WebUI remains configured for:
    http://127.0.0.1:8088/v1
    model: kaivor

FP009 does not require changing the Open WebUI model connection.

AFTER SUCCESS
-------------
Create the next clean project snapshot before the next milestone:

    cd /storage/emulated/0/Download/KAIVOR/Kaivor && \
    rm -f /storage/emulated/0/Download/Kaivor-latest.zip && \
    zip -qr /storage/emulated/0/Download/Kaivor-latest.zip . \
      -x '.git/*' '__pycache__/*' '*/__pycache__/*' '*.pyc' && \
    cp /storage/emulated/0/Download/Kaivor-latest.zip \
      /storage/emulated/0/Download/KAIVOR-LATEST-2026-09-02-FP009.zip

Android location:
    Downloads/Kaivor-latest.zip
