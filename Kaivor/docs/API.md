# Kaivor API

## OpenAI-compatible API

Kaivor exposes a lightweight OpenAI-compatible HTTP API so external interfaces such as Open WebUI can use the Kaivor AI engine without replacing it.

### Start

```bash
python kaivor.py api
```

Default listener:

```text
http://127.0.0.1:8088
```

For another local interface to reach the service over the Android/Termux network namespace, bind explicitly:

```bash
python kaivor.py api --host 0.0.0.0 --port 8088
```

### Endpoints

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

### Open WebUI

Configure an OpenAI-compatible connection with:

```text
API Base URL: http://127.0.0.1:8088/v1
Model: kaivor
```

If `KAIVOR_API_KEY` is not set, authentication is disabled. For any non-loopback binding, set a strong key:

```bash
export KAIVOR_API_KEY='replace-with-a-long-random-secret'
```

Then supply that value to the Open WebUI connection.

## Architecture

Open WebUI is a client/UI layer. Kaivor remains responsible for provider routing, failover, knowledge retrieval and AI execution.

```text
Open WebUI
    ↓
OpenAI-compatible API
    ↓
Kaivor AI Engine
    ↓
Provider Router / RAG / Memory
    ↓
AI Providers
```

The API intentionally does not copy Open WebUI's database or memory into Kaivor. This keeps the systems loosely coupled and allows the UI to be replaced later.
