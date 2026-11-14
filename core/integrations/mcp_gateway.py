"""Hardened Muse-compatible MCP gateway for Kaivor (FP051).

External knowledge access is deny-by-default. Only explicitly allowlisted memory
categories may be returned to an authenticated connector.
"""
from __future__ import annotations

import hmac
import json
import os
import re
from contextvars import ContextVar
from typing import Any, Mapping
from uuid import UUID

from core.agents.models import AgentPermissions, AgentTask
from core.agents.orchestrator import AgentOrchestrator
from core.agents.registry import AgentRegistry
from core.agents.kaivor_ai import KaivorAIAgent
from core.integrations.mcp_security import MCPRequestGuard
from core.integrations.mcp_observability import MCPObservabilityMiddleware, MCPMetrics

_identity: ContextVar[str | None] = ContextVar("kaivor_mcp_identity", default=None)


def _identity_or_raise() -> str:
    value = _identity.get()
    if not value:
        raise PermissionError("Authenticated agent identity is unavailable.")
    return value


def _safe_text(value: Any, *, maximum: int = 4000) -> str:
    if not isinstance(value, str):
        raise ValueError("Input must be text.")
    value = value.strip()
    if not value or len(value) > maximum:
        raise ValueError(f"Text must contain 1 to {maximum} characters.")
    if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
        raise ValueError("Text contains unsupported control characters.")
    return value


def _validate_task_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid task ID.")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("Invalid task ID.") from exc
    if str(parsed) != value.lower():
        raise ValueError("Invalid task ID.")
    return str(parsed)


def _normalise_categories(value: str | set[str] | list[str] | tuple[str, ...] | None) -> frozenset[str]:
    if value is None:
        value = os.environ.get("KAIVOR_MCP_ALLOWED_MEMORY_CATEGORIES", "")
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (set, list, tuple)):
        items = list(value)
    else:
        raise ValueError("Allowed memory categories must be text or a collection of text values.")
    categories: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            raise ValueError("Memory category names must be text.")
        item = item.strip().casefold()
        if item:
            if len(item) > 80 or any(ord(char) < 32 for char in item):
                raise ValueError("Invalid memory category name.")
            categories.add(item)
    return frozenset(categories)


def _memory_to_public_dict(item: Any) -> dict[str, Any] | None:
    """Project a memory onto an explicit, non-sensitive response schema."""
    if isinstance(item, dict):
        data = item
    elif callable(getattr(item, "to_dict", None)):
        data = item.to_dict()
    else:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("category"), str):
        return None
    content = data.get("content", "")
    title = data.get("title", "")
    if not isinstance(content, str) or not isinstance(title, str):
        return None
    return {
        "id": data.get("id"),
        "category": data["category"],
        "title": title[:300],
        "content": content[:2000],
        "created_at": data.get("created_at"),
    }


def _filter_approved_memories(items: Any, allowed_categories: frozenset[str], limit: int) -> list[dict[str, Any]]:
    if not isinstance(items, (list, tuple)) or not allowed_categories:
        return []
    output: list[dict[str, Any]] = []
    for item in items:
        public_item = _memory_to_public_dict(item)
        if public_item and public_item["category"].strip().casefold() in allowed_categories:
            output.append(public_item)
            if len(output) >= limit:
                break
    return output


def _task_owned_by(record: Any, identity: str) -> bool:
    if not isinstance(record, dict):
        return False
    task = record.get("task")
    return isinstance(task, dict) and isinstance(task.get("created_by"), str) and hmac.compare_digest(task["created_by"], identity)


def _run_owned_readonly_task(service: AgentOrchestrator, task_id: str, identity: str) -> dict[str, Any]:
    """Execute only this connector's pending, explicitly read-only Kaivor AI task."""
    record = service.get(task_id)
    if not _task_owned_by(record, identity):
        raise LookupError("Task not found.")
    if record.get("status") != "pending":
        raise ValueError("Task is not pending and cannot be executed.")
    task_data = record.get("task")
    try:
        task = AgentTask.from_dict(task_data)
    except (TypeError, ValueError, KeyError) as exc:
        raise PermissionError("Task permissions or definition are invalid.") from exc
    permissions = task.permissions
    if (
        task.assigned_to != "kaivor_ai"
        or permissions.read is not True
        or permissions.write is not False
        or permissions.external_actions is not False
        or permissions.access_secrets is not False
    ):
        raise PermissionError("Only read-only Kaivor AI tasks may be executed through MCP.")
    result = service.run(task_id)
    return {
        "task_id": task_id,
        "status": result.get("status", "unknown"),
        "error_code": result.get("error_code"),
    }


def _normalise_connectors(value: Mapping[str, str] | None) -> dict[str, str]:
    """Validate a connector-identity -> bearer-token mapping."""
    if not isinstance(value, Mapping) or not value:
        raise ValueError("At least one MCP connector credential must be configured.")
    if len(value) > 50:
        raise ValueError("A maximum of 50 MCP connectors may be configured.")
    credentials: dict[str, str] = {}
    seen_tokens: set[str] = set()
    for raw_identity, token in value.items():
        if not isinstance(raw_identity, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", raw_identity):
            raise ValueError("MCP connector identity contains unsupported characters.")
        if not isinstance(token, str) or len(token) < 32 or token.strip() != token or any(ch.isspace() for ch in token):
            raise ValueError("Every MCP connector token must be at least 32 characters and contain no whitespace.")
        if token in seen_tokens:
            raise ValueError("Each MCP connector must have a unique bearer token.")
        seen_tokens.add(token)
        credentials[raw_identity] = token
    return credentials


def _parse_connector_environment(raw: str) -> dict[str, str]:
    """Parse KAIVOR_MCP_CONNECTORS as a JSON object mapping identity to token."""
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate connector identity in KAIVOR_MCP_CONNECTORS.")
            result[key] = value
        return result
    try:
        parsed = json.loads(raw, object_pairs_hook=reject_duplicate_keys)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("KAIVOR_MCP_CONNECTORS must be a valid JSON object.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("KAIVOR_MCP_CONNECTORS must be a JSON object.")
    return _normalise_connectors(parsed)


class BearerAuthMiddleware:
    """ASGI bearer authentication for legacy single-token or multi-connector mode."""
    def __init__(
        self,
        app,
        token: str | None = None,
        identity: str = "meta_muse",
        *,
        credentials: Mapping[str, str] | None = None,
    ):
        if credentials is not None:
            if token is not None:
                raise ValueError("Configure either one bearer token or connector credentials, not both.")
            self.credentials = _normalise_connectors(credentials)
            self.token = None
            self.identity = None
        else:
            if not isinstance(token, str) or len(token) < 32:
                raise ValueError("KAIVOR_MCP_BEARER_TOKEN must be at least 32 characters.")
            if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", identity):
                raise ValueError("KAIVOR_MCP_IDENTITY contains unsupported characters.")
            self.credentials = {identity: token}
            # Preserve the legacy attributes used by existing integrations/tests.
            self.token = token
            self.identity = identity
        self.app = app

    def resolve_identity(self, scope) -> str | None:
        """Resolve a supplied bearer token without exposing configured credentials."""
        auth_values = [value for key, value in scope.get("headers", []) if key.lower() == b"authorization"]
        supplied = auth_values[0].decode("latin1") if len(auth_values) == 1 else ""
        matched_identity = None
        for connector_identity, token in self.credentials.items():
            if hmac.compare_digest(supplied, "Bearer " + token):
                matched_identity = connector_identity
        return matched_identity

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        identity = self.resolve_identity(scope)
        if identity is None:
            body = b'{"error":"unauthorized"}'
            await send({"type": "http.response.start", "status": 401, "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"www-authenticate", b"Bearer"),
                (b"cache-control", b"no-store"),
            ]})
            await send({"type": "http.response.body", "body": body})
            return
        token = _identity.set(identity)
        try:
            await self.app(scope, receive, send)
        finally:
            _identity.reset(token)


def build_mcp_app(
    *,
    orchestrator: AgentOrchestrator | None = None,
    search_fn=None,
    bearer_token: str | None = None,
    identity: str | None = None,
    connectors: Mapping[str, str] | None = None,
    allowed_memory_categories: str | set[str] | list[str] | tuple[str, ...] | None = None,
):
    """Build a protected Streamable HTTP MCP ASGI application."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the MCP dependency with: pip install -r requirements-mcp.txt") from exc

    registry = AgentRegistry()
    registry.register(KaivorAIAgent())
    if orchestrator is not None:
        service = orchestrator
    else:
        database_url = os.environ.get("KAIVOR_AGENT_DATABASE_URL", "").strip()
        require_postgres = os.environ.get("KAIVOR_MCP_REQUIRE_POSTGRES", "false").strip().lower() == "true"
        if database_url:
            from core.agents.postgres_store import PostgresAgentTaskStore
            service = AgentOrchestrator(registry=registry, store=PostgresAgentTaskStore(database_url))
        elif require_postgres:
            raise RuntimeError("Production MCP requires KAIVOR_AGENT_DATABASE_URL; refusing SQLite fallback.")
        else:
            service = AgentOrchestrator(registry=registry)
    search = search_fn or _search_knowledge
    allowed_categories = _normalise_categories(allowed_memory_categories)
    mcp = FastMCP("Kaivor", stateless_http=True, json_response=True)

    @mcp.tool(name="kaivor_search_knowledge", description="Search explicitly allowlisted Kaivor memory categories. Disabled unless categories are configured by the owner.")
    def kaivor_search_knowledge(query: str, limit: int = 5) -> dict[str, Any]:
        _identity_or_raise()
        query = _safe_text(query, maximum=300)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10:
            raise ValueError("limit must be an integer from 1 to 10.")
        if not allowed_categories:
            return {"query": query, "results": [], "count": 0, "access": "disabled_by_default"}
        results = _filter_approved_memories(search(query), allowed_categories, limit)
        return {"query": query, "results": results, "count": len(results), "access": "allowlisted_categories"}

    @mcp.tool(name="kaivor_submit_task", description="Submit a read-only research task to Kaivor. Creates a pending task; does not execute external actions.")
    def kaivor_submit_task(objective: str, task_type: str = "research", constraints: list[str] | None = None) -> dict[str, Any]:
        connector_identity = _identity_or_raise()
        objective = _safe_text(objective, maximum=2000)
        task_type = _safe_text(task_type, maximum=40).lower()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", task_type):
            raise ValueError("task_type contains unsupported characters.")
        if constraints is None:
            constraints = []
        if not isinstance(constraints, list) or len(constraints) > 12 or any(not isinstance(x, str) or len(x) > 500 for x in constraints):
            raise ValueError("constraints must be a list of up to 12 text items (500 characters each).")
        constraints = [x.strip() for x in constraints]
        task = AgentTask(
            objective=objective, assigned_to="kaivor_ai", task_type=task_type,
            constraints=constraints, permissions=AgentPermissions(read=True),
            created_by=connector_identity,
            metadata={"source": "mcp", "external_identity": connector_identity},
        )
        record = service.submit(task)
        return {"task_id": record["task_id"], "status": record["status"], "created_at": record["created_at"]}

    @mcp.tool(name="kaivor_run_task", description="Execute one of your pending, read-only Kaivor AI research tasks. Write permissions and external actions are never allowed.")
    def kaivor_run_task(task_id: str) -> dict[str, Any]:
        connector_identity = _identity_or_raise()
        task_id = _validate_task_id(task_id)
        return _run_owned_readonly_task(service, task_id, connector_identity)

    @mcp.tool(name="kaivor_get_task_status", description="Get the status of a task submitted by this authenticated connector identity.")
    def kaivor_get_task_status(task_id: str) -> dict[str, Any]:
        connector_identity = _identity_or_raise()
        task_id = _validate_task_id(task_id)
        record = service.get(task_id)
        if not _task_owned_by(record, connector_identity):
            raise LookupError("Task not found.")
        return {"task_id": record["task_id"], "status": record["status"], "created_at": record["created_at"], "updated_at": record["updated_at"]}

    @mcp.tool(name="kaivor_get_task_result", description="Get the completed result of a task submitted by this authenticated connector identity.")
    def kaivor_get_task_result(task_id: str) -> dict[str, Any]:
        connector_identity = _identity_or_raise()
        task_id = _validate_task_id(task_id)
        record = service.get(task_id)
        if not _task_owned_by(record, connector_identity):
            raise LookupError("Task not found.")
        if record["status"] != "completed" or not record.get("result"):
            return {"task_id": task_id, "status": record["status"], "result": None}
        result = record["result"]
        return {"task_id": task_id, "status": "completed", "result": {
            "agent_id": result.get("agent_id"),
            "output": str(result.get("output", ""))[:12000],
            "sources": result.get("sources", [])[:20],
            "limitations": result.get("limitations", [])[:20],
        }}

    configured_connectors = connectors
    environment_connectors = os.environ.get("KAIVOR_MCP_CONNECTORS", "").strip()
    if configured_connectors is not None and environment_connectors:
        raise ValueError("Configure MCP connectors through either the function or environment, not both.")
    if configured_connectors is None and environment_connectors:
        configured_connectors = _parse_connector_environment(environment_connectors)

    if configured_connectors is not None:
        if bearer_token is not None or identity is not None:
            raise ValueError("Multi-connector mode cannot be combined with bearer_token or identity arguments.")
        legacy_token = os.environ.get("KAIVOR_MCP_BEARER_TOKEN", "").strip()
        if legacy_token:
            raise ValueError("Remove KAIVOR_MCP_BEARER_TOKEN when using KAIVOR_MCP_CONNECTORS.")
        credentials = _normalise_connectors(configured_connectors)
        authenticated = BearerAuthMiddleware(mcp.streamable_http_app(), credentials=credentials)
    else:
        token = bearer_token if bearer_token is not None else os.environ.get("KAIVOR_MCP_BEARER_TOKEN", "")
        connector_identity = identity if identity is not None else os.environ.get("KAIVOR_MCP_IDENTITY", "meta_muse")
        credentials = _normalise_connectors({connector_identity: token})
        authenticated = BearerAuthMiddleware(mcp.streamable_http_app(), token, connector_identity)

    requests_per_minute = int(os.environ.get("KAIVOR_MCP_RATE_LIMIT_PER_MINUTE", "60"))
    max_body_bytes = int(os.environ.get("KAIVOR_MCP_MAX_BODY_BYTES", "1048576"))
    unauthenticated_limit = int(os.environ.get("KAIVOR_MCP_UNAUTHENTICATED_RATE_LIMIT_PER_MINUTE", "20"))
    metrics_identity_config = os.environ.get("KAIVOR_MCP_METRICS_IDENTITIES", "").strip()
    if metrics_identity_config:
        metrics_authorized_identities = frozenset(
            item.strip() for item in metrics_identity_config.split(",") if item.strip()
        )
        if not metrics_authorized_identities.issubset(credentials):
            raise ValueError("KAIVOR_MCP_METRICS_IDENTITIES must name configured MCP connector identities.")
    elif len(credentials) == 1:
        # Preserve convenient single-connector operation without exposing
        # cross-connector telemetry in multi-connector deployments.
        metrics_authorized_identities = frozenset(credentials)
    else:
        # Multi-connector deployments must explicitly designate an operator.
        metrics_authorized_identities = frozenset()

    def readiness_check():
        store = getattr(service, "store", None)
        check = getattr(store, "health_check", None)
        return True if check is None else check() is True

    guarded = MCPRequestGuard(
        authenticated,
        requests_per_minute=requests_per_minute,
        unauthenticated_requests_per_minute=unauthenticated_limit,
        max_body_bytes=max_body_bytes,
        bearer_token=None,
        authenticated_identity_resolver=authenticated.resolve_identity,
        health_check=readiness_check,
    )
    # Observe outside the guard so authentication failures, rate limits, body
    # rejections, and health checks are included. /metrics has its own strict
    # authenticated per-connector limit in the observability middleware.
    return MCPObservabilityMiddleware(
        guarded,
        identity_resolver=authenticated.resolve_identity,
        metrics=MCPMetrics(),
        metrics_authorized_identities=metrics_authorized_identities,
    )


def _search_knowledge(query: str) -> list[Any]:
    from core.memory.api import search
    return search(query)
