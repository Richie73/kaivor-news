"""OpenAI-compatible HTTP API for Kaivor.

Local-first adapter for Open WebUI and other OpenAI-compatible clients.
"""
from __future__ import annotations

import json
import os
import secrets as _secrets
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Kept at module scope for compatibility with the existing API test suite.
from core.knowledge.rag_service import RAGService

MODEL_ID = "kaivor"
MODEL_NAME = "Kaivor"
API_KEY_ENV = "KAIVOR_API_KEY"
ROOT = Path(__file__).resolve().parents[2]


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    return str(content or "")


def _normalise_messages(messages: Any) -> list[dict[str, str]]:
    """Normalise OpenAI-style messages for Kaivor's internal request model."""
    if not isinstance(messages, list):
        raise ValueError("messages must be a JSON array")
    result = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "user"))
        content = _content_to_text(message.get("content", ""))
        if content:
            result.append({"role": role, "content": content})
    if not result:
        raise ValueError("messages must contain at least one non-empty message")
    return result


def _last_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message["role"] == "user":
            return message["content"]
    return messages[-1]["content"]


def _task_from_request(payload: dict[str, Any]) -> str:
    from core.ai.tasks import AITasks
    requested = str(payload.get("task", "chat")).lower()
    valid = {
        AITasks.CHAT, AITasks.CODING, AITasks.RESEARCH, AITasks.WRITING,
        AITasks.RAMS, AITasks.EMAIL, AITasks.NEWS, AITasks.VISION,
    }
    return requested if requested in valid else AITasks.CHAT


def _build_request(messages: list[dict[str, str]], task: str):
    """Build the shared AIRequest while retaining the historical API test contract."""
    from core.ai.request import AIRequest
    from core.config import Config
    config = Config()
    question = _last_user_message(messages)
    rag = RAGService().context(question)
    system_parts = [config.get("system_prompt", "You are Kaivor.")]

    client_system = [
        m["content"] for m in messages
        if m["role"] == "system" and m["content"].strip()
    ]
    if client_system:
        system_parts.append("Client system instructions:\n\n" + "\n\n".join(client_system))

    task_prompts = {
        "coding": "You are assisting with software engineering and coding tasks.",
        "research": "Prioritise evidence, uncertainty, and clear source distinctions.",
        "writing": "Produce clear, polished writing while following the user's instructions.",
        "rams": "Apply careful construction safety reasoning and flag uncertainty.",
        "email": "Write concise, professional email content.",
        "news": "Analyse news carefully and distinguish facts from interpretation.",
        "vision": "Analyse available visual information carefully.",
    }
    if task_prompts.get(task):
        system_parts.append(task_prompts[task])
    if rag.get("context"):
        system_parts.append("Knowledge Context:\n\n" + rag["context"])

    provider_messages = [m for m in messages if m["role"] in {"system", "user", "assistant"}]
    history = [m for m in provider_messages if m["role"] != "system"]
    request = AIRequest(
        user=question,
        system="\n\n".join(system_parts),
        history=history[:-1],
        temperature=float(config.get("temperature", 0.2)),
        max_tokens=int(config.get("max_tokens", 2048)),
    )
    return request, rag


def generate_chat(payload: dict[str, Any]) -> tuple[str, str, list[dict]]:
    from core.ai.router import AIRouter
    from core.config import Config

    messages = _normalise_messages(payload.get("messages"))
    task = _task_from_request(payload)
    request, rag = _build_request(messages, task)
    providers = AIRouter().failover(task)
    if not providers:
        raise RuntimeError(f"No configured providers available for task: {task}")

    retry_attempts = int(Config().get("retry_attempts", 2))
    errors = []
    for provider in providers:
        for _ in range(max(1, retry_attempts)):
            try:
                response = provider.generate(request)
                return str(response), provider.name, rag.get("sources", [])
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
    raise RuntimeError("All Kaivor providers failed: " + " | ".join(errors[-6:]))


def _model_payload() -> dict[str, Any]:
    return {"object": "list", "data": [{
        "id": MODEL_ID, "object": "model", "owned_by": "kaivor", "name": MODEL_NAME,
    }]}


def _error(message: str, error_type: str, code: int | None = None) -> dict[str, Any]:
    return {"error": {"message": message, "type": error_type, "param": None, "code": code}}


class KaivorAPIHandler(BaseHTTPRequestHandler):
    server_version = "KaivorAPI/FP009"

    def _json(self, status: int, data: dict[str, Any], request_id: str | None = None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.write(body)

    def _authorised(self) -> bool:
        expected = os.environ.get(API_KEY_ENV, "").strip()
        if not expected:
            return True
        header = self.headers.get("Authorization", "")
        supplied = header[7:].strip() if header.lower().startswith("bearer ") else ""
        return bool(supplied) and _secrets.compare_digest(supplied, expected)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 4 * 1024 * 1024:
                raise ValueError("Request body must be between 1 byte and 4 MB.")
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid JSON request: {exc}") from exc

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if not self._authorised():
            self._json(401, _error("Invalid or missing API key.", "authentication_error", 401))
            return
        if self.path == "/health":
            self._json(200, {"status": "ok", "service": "kaivor", "model": MODEL_ID})
        elif self.path == "/v1/models":
            self._json(200, _model_payload())
        elif self.path == f"/v1/models/{MODEL_ID}":
            self._json(200, _model_payload()["data"][0])
        elif self.path == "/":
            self._json(200, {"service": "Kaivor OpenAI-compatible API", "model": MODEL_ID})
        else:
            self._json(404, _error("Not found.", "not_found", 404))

    def do_POST(self):
        request_id = "chatcmpl-" + uuid.uuid4().hex
        if not self._authorised():
            self._json(401, _error("Invalid or missing API key.", "authentication_error", 401), request_id)
            return
        if self.path != "/v1/chat/completions":
            self._json(404, _error("Not found.", "not_found", 404), request_id)
            return
        try:
            payload = self._read_json()
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object.")
            model = str(payload.get("model") or MODEL_ID)
            if model != MODEL_ID:
                raise ValueError(f"Unknown model: {model}")
            response, provider, sources = generate_chat(payload)
            created = int(time.time())
            if payload.get("stream"):
                self._stream_response(request_id, created, model, response)
                return
            self._json(200, {
                "id": request_id,
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": response}, "finish_reason": "stop"}],
                "usage": None,
                "kaivor": {"provider": provider, "sources": sources},
            }, request_id)
        except ValueError as exc:
            self._json(400, _error(str(exc), "invalid_request_error", 400), request_id)
        except Exception as exc:
            self._json(500, _error(f"Kaivor generation failed: {exc}", "server_error", 500), request_id)

    def _stream_response(self, completion_id: str, created: int, model: str, response: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        words = response.split(" ")
        for index, word in enumerate(words):
            delta = word if index == 0 else " " + word
            chunk = {"id": completion_id, "object": "chat.completion.chunk", "created": created,
                     "model": model, "choices": [{"index": 0, "delta": ({"role": "assistant", "content": delta} if index == 0 else {"content": delta}), "finish_reason": None}]}
            self.wfile.write(("data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n").encode("utf-8"))
            self.wfile.flush()
        final = {"id": completion_id, "object": "chat.completion.chunk", "created": created,
                 "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        self.wfile.write(("data: " + json.dumps(final) + "\n\ndata: [DONE]\n\n").encode("utf-8"))
        self.wfile.flush()

    def log_message(self, fmt, *args):
        print(f"[Kaivor API] {fmt % args}")


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(host: str = "127.0.0.1", port: int = 8088):
    server = ReusableThreadingHTTPServer((host, port), KaivorAPIHandler)
    print("=" * 60)
    print("KAIVOR OPENAI-COMPATIBLE API")
    print("=" * 60)
    print(f"Listening: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Kaivor API...")
    finally:
        server.server_close()

if __name__ == "__main__":
    serve(host="0.0.0.0", port=8000)
