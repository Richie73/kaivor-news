"""ASGI protections for the standalone Kaivor MCP service."""
from __future__ import annotations

import asyncio
import hmac
import inspect
import json
import time
from collections import deque
from typing import Callable


class MCPRequestGuard:
    """Bound request bodies and apply separate authenticated/abuse quotas.

    When bearer_token is configured, invalid/missing credentials consume only
    the unauthenticated IP bucket. Valid credentials consume the authenticated
    bucket, so unauthenticated traffic cannot exhaust a connector's quota.
    Keep one worker per process; limits are intentionally process-local.
    """

    def __init__(
        self,
        app,
        *,
        requests_per_minute: int = 60,
        unauthenticated_requests_per_minute: int = 20,
        max_body_bytes: int = 1_048_576,
        bearer_token: str | None = None,
        authenticated_identity_resolver: Callable[[dict], str | None] | None = None,
        health_check: Callable[[], object] | None = None,
    ):
        if requests_per_minute < 1 or unauthenticated_requests_per_minute < 1 or max_body_bytes < 1024:
            raise ValueError("Invalid MCP request guard limits.")
        if bearer_token is not None and (not isinstance(bearer_token, str) or len(bearer_token) < 32):
            raise ValueError("bearer_token must contain at least 32 characters.")
        self.app = app
        self.limit = requests_per_minute
        self.unauthenticated_limit = unauthenticated_requests_per_minute
        self.max_body = max_body_bytes
        self.bearer_token = bearer_token
        self.authenticated_identity_resolver = authenticated_identity_resolver
        self.health_check = health_check
        self.events: dict[str, deque[float]] = {}
        self.lock = asyncio.Lock()

    async def _respond(self, send, status: int, payload: dict, headers=()):
        body = json.dumps(payload, separators=(",", ":")).encode()
        await send({"type": "http.response.start", "status": status, "headers": [
            (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
            (b"cache-control", b"no-store"), *headers]})
        await send({"type": "http.response.body", "body": body})

    async def _health(self, path: str, send):
        if path == "/livez":
            await self._respond(send, 200, {"status": "alive", "alive": True})
            return True
        if path not in {"/readyz", "/healthz"}:
            return False
        ready = self.health_check is None
        if self.health_check is not None:
            try:
                result = self.health_check()
                if inspect.isawaitable(result):
                    result = await result
                ready = result is True
            except Exception:
                ready = False
        payload = {"status": "ready" if ready else "not_ready", "ready": ready}
        if path == "/healthz" and ready:
            payload["status"] = "ok"  # Preserve the FP052 liveness response contract.
        await self._respond(send, 200 if ready else 503, payload)
        return True

    def _quota_key(self, scope) -> tuple[str, int]:
        if self.authenticated_identity_resolver is not None:
            try:
                identity = self.authenticated_identity_resolver(scope)
            except Exception:
                identity = None
            if isinstance(identity, str) and identity:
                return "authenticated:" + identity, self.limit
            client = scope.get("client") or ("unknown", 0)
            return "unauthenticated:" + str(client[0]), self.unauthenticated_limit

        headers = scope.get("headers", [])
        auth_values = [value for key, value in headers if key.lower() == b"authorization"]
        if self.bearer_token is not None:
            supplied = auth_values[0].decode("latin1") if len(auth_values) == 1 else ""
            expected = "Bearer " + self.bearer_token
            if len(auth_values) == 1 and hmac.compare_digest(supplied, expected):
                return "authenticated", self.limit
            client = scope.get("client") or ("unknown", 0)
            return "unauthenticated:" + str(client[0]), self.unauthenticated_limit
        client = scope.get("client") or ("unknown", 0)
        return "client:" + str(client[0]), self.limit

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        if await self._health(scope.get("path", ""), send):
            return

        raw_length_values = [v for k, v in scope.get("headers", []) if k.lower() == b"content-length"]
        if len(raw_length_values) > 1:
            await self._respond(send, 400, {"error": "duplicate_content_length"})
            return
        if raw_length_values:
            try:
                length = int(raw_length_values[0])
                if length < 0:
                    raise ValueError
                if length > self.max_body:
                    await self._respond(send, 413, {"error": "request_too_large"})
                    return
            except ValueError:
                await self._respond(send, 400, {"error": "invalid_content_length"})
                return

        bucket_name, limit = self._quota_key(scope)
        client = scope.get("client") or ("unknown", 0)
        key = bucket_name if bucket_name != "client:unknown" else "client:unknown"
        if bucket_name == "authenticated":
            key += ":shared"
        now = time.monotonic()
        rate_limited = False
        async with self.lock:
            bucket = self.events.setdefault(key, deque())
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= limit:
                rate_limited = True
            else:
                bucket.append(now)
            if len(self.events) > 4096:
                self.events = {k: v for k, v in self.events.items() if v and now - v[-1] < 60}

        # Never perform network I/O while holding the shared quota lock.
        if rate_limited:
            await self._respond(send, 429, {"error": "rate_limit_exceeded"}, [(b"retry-after", b"60")])
            return

        messages = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message.get("type") == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_body:
                    await self._respond(send, 413, {"error": "request_too_large"})
                    return
                if not message.get("more_body", False):
                    break
            elif message.get("type") == "http.disconnect":
                return
        index = 0

        async def replay_receive():
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)
