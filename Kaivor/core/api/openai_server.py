"""
Kaivor OpenAI-compatible API server.

Provides the minimum OpenAI-compatible surface required by clients such as
Open WebUI while keeping Kaivor's AI engine as the system of record.
"""

import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from core.ai.engine import AIEngine
from core.ai.request import AIRequest
from core.ai.router import AIRouter
from core.ai.tasks import AITasks
from core.config import Config
from core.knowledge.rag_service import RAGService


MODEL_ID = "kaivor"
MODEL_NAME = "Kaivor"
API_KEY_ENV = "KAIVOR_API_KEY"


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
    requested = str(payload.get("task", "chat")).lower()
    valid = {
        AITasks.CHAT,
        AITasks.CODING,
        AITasks.RESEARCH,
        AITasks.WRITING,
        AITasks.RAMS,
        AITasks.EMAIL,
        AITasks.NEWS,
        AITasks.VISION,
    }
    return requested if requested in valid else AITasks.CHAT


def _build_request(messages: list[dict[str, str]], task: str) -> tuple[AIRequest, dict]:
    config = Config()
    question = _last_user_message(messages)
    rag = RAGService().context(question)

    system_parts = [config.get("system_prompt", "You are Kaivor.")]

    client_system = [
        m["content"] for m in messages
        if m["role"] == "system" and m["content"].strip()
    ]
    if client_system:
        system_parts.append(
            "Client system instructions:\n\n" + "\n\n".join(client_system)
        )

    task_prompts = {
        AITasks.CHAT: "",
        AITasks.CODING: "You are assisting with software engineering and coding tasks.",
        AITasks.RESEARCH: "Prioritise evidence, uncertainty, and clear source distinctions.",
        AITasks.WRITING: "Produce clear, polished writing while following the user's instructions.",
        AITasks.RAMS: "Apply careful construction safety reasoning and flag uncertainty.",
        AITasks.EMAIL: "Write concise, professional email content.",
        AITasks.NEWS: "Analyse news carefully and distinguish facts from interpretation.",
        AITasks.VISION: "Analyse available visual information carefully.",
    }
    if task_prompts.get(task):
        system_parts.append(task_prompts[task])

    if rag["context"]:
        system_parts.append("Knowledge Context:\n\n" + rag["context"])

    provider_messages = []
    for message in messages:
        if message["role"] in {"system", "user", "assistant"}:
            provider_messages.append(message)

    # Replace client system instructions with Kaivor's controlled system layer,
    # while retaining the user's conversation history.
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
    messages = _normalise_messages(payload.get("messages"))
    task = _task_from_request(payload)
    request, rag = _build_request(messages, task)

    router = AIRouter()
    providers = router.failover(task)
    if not providers:
        raise RuntimeError(f"No configured providers available for task: {task}")

    retry_attempts = int(Config().get("retry_attempts", 2))
    errors = []

    for provider in providers:
        for attempt in range(max(1, retry_attempts)):
            try:
                response = provider.generate(request)
                return str(response), provider.name, rag["sources"]
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")

    raise RuntimeError("All Kaivor providers failed: " + " | ".join(errors[-6:]))


class KaivorAPIHandler(BaseHTTPRequestHandler):
    server_version = "KaivorAPI/0.1"

    def _json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorised(self) -> bool:
        expected = os.environ.get(API_KEY_ENV, "").strip()
        if not expected:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {expected}"

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Invalid JSON request: {exc}") from exc

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok", "service": "kaivor"})
            return
        if self.path == "/v1/models":
            self._json(200, {"object": "list", "data": [{
                "id": MODEL_ID,
                "object": "model",
                "owned_by": "kaivor",
            }]})
            return
        if self.path == "/":
            self._json(200, {"service": "Kaivor OpenAI-compatible API", "model": MODEL_ID})
            return
        self._json(404, {"error": {"message": "Not found", "type": "invalid_request_error"}})

    def do_POST(self):
        if not self._authorised():
            self._json(401, {"error": {"message": "Invalid API key", "type": "authentication_error"}})
            return

        if self.path != "/v1/chat/completions":
            self._json(404, {"error": {"message": "Not found", "type": "invalid_request_error"}})
            return

        try:
            payload = self._read_json()
            response, provider, sources = generate_chat(payload)
            model = str(payload.get("model") or MODEL_ID)
            completion_id = "chatcmpl-" + uuid.uuid4().hex
            created = int(time.time())

            if payload.get("stream"):
                self._stream_response(completion_id, created, model, response)
                return

            self._json(200, {
                "id": completion_id,
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": response},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "kaivor": {
                    "provider": provider,
                    "sources": sources,
                },
            })
        except ValueError as exc:
            self._json(400, {"error": {"message": str(exc), "type": "invalid_request_error"}})
        except Exception as exc:
            self._json(500, {"error": {"message": str(exc), "type": "server_error"}})

    def _stream_response(self, completion_id: str, created: int, model: str, response: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        words = response.split(" ")
        for index, word in enumerate(words):
            text = word if index == len(words) - 1 else word + " "
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
            }
            self.wfile.write(("data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n").encode("utf-8"))
            self.wfile.flush()

        final = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        self.wfile.write(("data: " + json.dumps(final) + "\n\ndata: [DONE]\n\n").encode("utf-8"))
        self.wfile.flush()

    def log_message(self, fmt, *args):
        print(f"[Kaivor API] {fmt % args}")


def serve(host: str = "127.0.0.1", port: int = 8088):
    server = ThreadingHTTPServer((host, port), KaivorAPIHandler)
    print("=" * 60)
    print("KAIVOR OPENAI-COMPATIBLE API")
    print("=" * 60)
    print(f"Listening: http://{host}:{port}")
    print(f"Models:    http://{host}:{port}/v1/models")
    print(f"Chat:      http://{host}:{port}/v1/chat/completions")
    print("Press Ctrl+C to stop.")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Kaivor API...")
    finally:
        server.server_close()
