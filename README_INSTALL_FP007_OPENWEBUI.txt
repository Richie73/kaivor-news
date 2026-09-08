KAIVOR FP007 - OPEN WEBUI INTEGRATION
=====================================

This bundle adds a lightweight OpenAI-compatible API to Kaivor.

INSTALL
-------
1. Extract/overwrite the bundle into the existing Kaivor project root.
2. Do not overwrite config/secrets.py.
3. From the Kaivor project root run:

   python -m compileall -q core/api commands/api.py kaivor.py tests/test_api.py
   python tests/test_api.py

START API
---------

   python kaivor.py api

Default:
   http://127.0.0.1:8088

HEALTH CHECK
------------

   curl http://127.0.0.1:8088/health

MODELS
------

   curl http://127.0.0.1:8088/v1/models

OPEN WEBUI
----------

Create an OpenAI-compatible connection/provider using:

   API Base URL: http://127.0.0.1:8088/v1
   Model: kaivor

If Open WebUI is running in a different network namespace and cannot reach
127.0.0.1, start Kaivor on 0.0.0.0 instead:

   python kaivor.py api --host 0.0.0.0 --port 8088

For non-loopback binding, set a strong API key first:

   export KAIVOR_API_KEY='YOUR_LONG_RANDOM_KEY'

Then enter that same key in Open WebUI.

ARCHITECTURE
------------
Open WebUI is the UI. Kaivor remains the engine, RAG layer and provider router.
The integration is deliberately loose so another UI can replace Open WebUI later.

SECURITY WARNING
----------------
The project snapshot contained a populated API credential in config/secrets.py.
This bundle does not copy or modify that file. If that credential is real and
has been exposed outside the private environment, rotate/revoke it before
continuing.
