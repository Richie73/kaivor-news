"""Credential-safe operational observability for the Kaivor MCP gateway.

The middleware emits one-line JSON audit events and exposes bounded-cardinality
Prometheus metrics at an authenticated /metrics endpoint. It deliberately does
not log request/response bodies, query strings, headers, client addresses,
credentials, task objectives, or agent results.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Callable


_LOGGER = logging.getLogger("kaivor.mcp.audit")


def _prometheus_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _route_label(path: str) -> str:
    """Map arbitrary paths to a small, fixed set of metric labels."""
    if path in {"/mcp", "/mcp/"}:
        return "/mcp"
    if path in {"/livez", "/readyz", "/healthz", "/metrics"}:
        return path
    return "other"


class MCPMetrics:
    """Thread-safe in-memory request counters and latency aggregates."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, str, str], int] = defaultdict(int)
        self._duration_count: dict[tuple[str, str, str], int] = defaultdict(int)
        self._duration_sum: dict[tuple[str, str, str], float] = defaultdict(float)

    def observe(self, *, method: str, route: str, status: int, connector: str, duration_seconds: float) -> None:
        method = method if method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"} else "OTHER"
        status_label = str(status) if 100 <= status <= 599 else "500"
        connector = connector[:80] if connector and connector != "unauthenticated" else "unauthenticated"
        request_key = (method, route, status_label, connector)
        duration_key = (method, route, connector)
        with self._lock:
            self._requests[request_key] += 1
            self._duration_count[duration_key] += 1
            self._duration_sum[duration_key] += max(0.0, float(duration_seconds))

    def render_prometheus(self) -> bytes:
        with self._lock:
            requests = dict(self._requests)
            counts = dict(self._duration_count)
            sums = dict(self._duration_sum)

        lines = [
            "# HELP kaivor_mcp_http_requests_total Total MCP HTTP requests.",
            "# TYPE kaivor_mcp_http_requests_total counter",
        ]
        for (method, route, status, connector), value in sorted(requests.items()):
            labels = (f'method="{_prometheus_escape(method)}",route="{_prometheus_escape(route)}",'
                      f'status="{status}",connector="{_prometheus_escape(connector)}"')
            lines.append(f"kaivor_mcp_http_requests_total{{{labels}}} {value}")

        lines.extend([
            "# HELP kaivor_mcp_http_request_duration_seconds_sum Total MCP HTTP request duration in seconds.",
            "# TYPE kaivor_mcp_http_request_duration_seconds_sum counter",
        ])
        for (method, route, connector), value in sorted(sums.items()):
            labels = (f'method="{_prometheus_escape(method)}",route="{_prometheus_escape(route)}",'
                      f'connector="{_prometheus_escape(connector)}"')
            lines.append(f"kaivor_mcp_http_request_duration_seconds_sum{{{labels}}} {value:.9f}")

        lines.extend([
            "# HELP kaivor_mcp_http_request_duration_seconds_count Number of MCP HTTP request duration observations.",
            "# TYPE kaivor_mcp_http_request_duration_seconds_count counter",
        ])
        for (method, route, connector), value in sorted(counts.items()):
            labels = (f'method="{_prometheus_escape(method)}",route="{_prometheus_escape(route)}",'
                      f'connector="{_prometheus_escape(connector)}"')
            lines.append(f"kaivor_mcp_http_request_duration_seconds_count{{{labels}}} {value}")
        return ("\n".join(lines) + "\n").encode("utf-8")


class MCPObservabilityMiddleware:
    """Measure requests and expose authenticated Prometheus text metrics."""

    def __init__(
        self,
        app,
        *,
        identity_resolver: Callable[[dict], str | None],
        metrics: MCPMetrics | None = None,
        metrics_authorized_identities: set[str] | frozenset[str] | None = None,
    ):
        if not callable(identity_resolver):
            raise ValueError("identity_resolver must be callable.")
        if metrics_authorized_identities is not None and (
            not isinstance(metrics_authorized_identities, (set, frozenset))
            or any(not isinstance(item, str) or not item for item in metrics_authorized_identities)
        ):
            raise ValueError("metrics_authorized_identities must be a set of non-empty connector identities.")
        self.app = app
        self.identity_resolver = identity_resolver
        self.metrics = metrics or MCPMetrics()
        self.metrics_authorized_identities = (
            frozenset(metrics_authorized_identities) if metrics_authorized_identities is not None else None
        )
        # Keep the metrics endpoint from becoming an unmetered resource sink.
        self.metrics_endpoint_limit = 10
        self._metrics_endpoint_events: dict[str, deque[float]] = defaultdict(deque)
        self._metrics_endpoint_lock = asyncio.Lock()

    @staticmethod
    async def _respond(send, status: int, body: bytes, content_type: bytes) -> None:
        await send({"type": "http.response.start", "status": status, "headers": [
            (b"content-type", content_type),
            (b"content-length", str(len(body)).encode("ascii")),
            (b"cache-control", b"no-store"),
            (b"x-content-type-options", b"nosniff"),
        ]})
        await send({"type": "http.response.body", "body": body})

    def _identity(self, scope) -> str | None:
        try:
            identity = self.identity_resolver(scope)
        except Exception:
            return None
        return identity if isinstance(identity, str) and identity else None

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        route = _route_label(path)
        identity = self._identity(scope)
        connector = identity or "unauthenticated"

        if path == "/metrics":
            supplied = [v for k, v in scope.get("headers", []) if k.lower() == b"authorization"]
            expected_identity = identity
            # Resolver rejects missing, malformed, and duplicate Authorization headers.
            if len(supplied) != 1 or expected_identity is None:
                body = b'{"error":"unauthorized"}'
                await self._respond(send, 401, body, b"application/json")
                self._record(method, route, 401, connector, 0.0)
                return
            if self.metrics_authorized_identities is not None and expected_identity not in self.metrics_authorized_identities:
                body = b'{"error":"forbidden"}'
                await self._respond(send, 403, body, b"application/json")
                self._record(method, route, 403, connector, 0.0)
                return
            if method != "GET":
                body = b'{"error":"method_not_allowed"}'
                await self._respond(send, 405, body, b"application/json")
                self._record(method, route, 405, connector, 0.0)
                return
            now = time.monotonic()
            async with self._metrics_endpoint_lock:
                bucket = self._metrics_endpoint_events[connector]
                while bucket and now - bucket[0] >= 60:
                    bucket.popleft()
                metrics_limited = len(bucket) >= self.metrics_endpoint_limit
                if not metrics_limited:
                    bucket.append(now)
            if metrics_limited:
                body = b'{"error":"rate_limit_exceeded"}'
                await self._respond(send, 429, body, b"application/json")
                self._record(method, route, 429, connector, 0.0)
                return
            body = self.metrics.render_prometheus()
            await self._respond(send, 200, body, b"text/plain; version=0.0.4; charset=utf-8")
            self._record(method, route, 200, connector, 0.0)
            return

        started = time.perf_counter()
        status = 500
        response_started = False

        async def measured_send(message):
            nonlocal status, response_started
            if message.get("type") == "http.response.start":
                response_started = True
                candidate = message.get("status", 500)
                status = candidate if isinstance(candidate, int) else 500
            await send(message)

        error_type = None
        try:
            await self.app(scope, receive, measured_send)
            if not response_started:
                status = 500
        except Exception as exc:
            error_type = type(exc).__name__
            status = 500
            raise
        finally:
            duration = time.perf_counter() - started
            self._record(method, route, status, connector, duration, error_type=error_type)

    def _record(self, method: str, route: str, status: int, connector: str, duration: float, *, error_type: str | None = None) -> None:
        self.metrics.observe(method=method, route=route, status=status, connector=connector, duration_seconds=duration)
        event = {
            "event": "mcp_http_request",
            "method": method if method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"} else "OTHER",
            "route": route,
            "status": status,
            "connector": connector,
            "duration_ms": round(max(0.0, duration) * 1000, 3),
            "outcome": "error" if status >= 500 or error_type else ("denied" if status in {401, 403, 429} else "success"),
        }
        if error_type:
            event["exception_type"] = error_type[:100]
        # JSON is the log message itself, so this remains structured even when
        # the host application has not installed a custom logging formatter.
        _LOGGER.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
