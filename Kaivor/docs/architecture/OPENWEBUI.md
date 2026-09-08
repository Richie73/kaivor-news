# Open WebUI Integration Architecture

Status: FP007 implementation

Open WebUI is an external user interface for Kaivor. It is not the AI engine and it does not become a dependency of the Kaivor core.

```text
+----------------+
|   Open WebUI   |
+-------+--------+
        |
        | OpenAI-compatible HTTP API
        v
+----------------+
| Kaivor API     |
| /v1/*          |
+-------+--------+
        |
        v
+----------------+
| Kaivor AI      |
| Engine         |
+---+--------+---+
    |        |
    v        v
   RAG     Provider Router
             |
             v
       DeepSeek / OpenRouter /
       Google / Anthropic /
       OpenAI / Ollama
```

## Design rules

1. Open WebUI remains replaceable.
2. Kaivor remains the source of truth for provider routing and knowledge retrieval.
3. The integration uses an OpenAI-compatible API rather than importing Open WebUI code.
4. Open WebUI conversation storage is not copied into Kaivor memory automatically.
5. Local-only binding is the default.
6. If the API is exposed beyond localhost, `KAIVOR_API_KEY` must be configured.

## Current API

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

The API supports normal JSON responses and SSE streaming. Streaming is transport-compatible but currently emits the completed provider response in chunks rather than exposing provider token streaming.
