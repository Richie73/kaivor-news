"""Validated runtime configuration for the standalone Kaivor MCP service."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit


_ALLOWED_ENVIRONMENTS = {"development", "test", "staging", "production"}
_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,80}\Z")


def _integer(env: Mapping[str, str], name: str, default: int, minimum: int, maximum: int) -> int:
    raw = env.get(name, str(default)).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}.")
    return value


def _validate_production_auth(env: Mapping[str, str]) -> None:
    connectors_raw = env.get("KAIVOR_MCP_CONNECTORS", "").strip()
    legacy_token = env.get("KAIVOR_MCP_BEARER_TOKEN", "")
    if connectors_raw:
        if legacy_token:
            raise ValueError("Production must configure either KAIVOR_MCP_CONNECTORS or the single-token settings, not both.")

        def reject_duplicates(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("KAIVOR_MCP_CONNECTORS contains a duplicate identity.")
                result[key] = value
            return result

        try:
            credentials = json.loads(connectors_raw, object_pairs_hook=reject_duplicates)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("KAIVOR_MCP_CONNECTORS must be a valid JSON object.") from exc
        if not isinstance(credentials, dict) or not 1 <= len(credentials) <= 50:
            raise ValueError("KAIVOR_MCP_CONNECTORS must contain between 1 and 50 connectors.")
        tokens = set()
        for identity, token in credentials.items():
            if not isinstance(identity, str) or not _IDENTITY_PATTERN.fullmatch(identity):
                raise ValueError("A connector identity contains unsupported characters.")
            if not isinstance(token, str) or len(token) < 32 or token.strip() != token or any(ch.isspace() for ch in token):
                raise ValueError("Every connector token must contain at least 32 non-whitespace characters.")
            if token in tokens:
                raise ValueError("Each connector must use a unique bearer token.")
            tokens.add(token)
        operator_ids = {
            item.strip() for item in env.get("KAIVOR_MCP_METRICS_IDENTITIES", "").split(",") if item.strip()
        }
        if not operator_ids or not operator_ids.issubset(credentials):
            raise ValueError("Multi-connector production requires KAIVOR_MCP_METRICS_IDENTITIES naming configured operator identities.")
        return

    if len(legacy_token) < 32 or legacy_token.strip() != legacy_token or any(ch.isspace() for ch in legacy_token):
        raise ValueError("Production requires KAIVOR_MCP_BEARER_TOKEN with at least 32 non-whitespace characters.")
    identity = env.get("KAIVOR_MCP_IDENTITY", "meta_muse")
    if not _IDENTITY_PATTERN.fullmatch(identity):
        raise ValueError("KAIVOR_MCP_IDENTITY contains unsupported characters.")


@dataclass(frozen=True)
class MCPRuntimeConfig:
    environment: str
    host: str
    port: int
    log_level: str
    max_concurrency: int
    graceful_shutdown_seconds: int
    keep_alive_seconds: int

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> "MCPRuntimeConfig":
        source = env if env is not None else __import__("os").environ
        environment = source.get("KAIVOR_MCP_ENV", "development").strip().lower()
        if environment not in _ALLOWED_ENVIRONMENTS:
            raise ValueError("KAIVOR_MCP_ENV must be development, test, staging, or production.")

        host = source.get("KAIVOR_MCP_HOST", "127.0.0.1").strip()
        if not host or any(ch.isspace() for ch in host):
            raise ValueError("KAIVOR_MCP_HOST must be a valid non-empty host value.")
        # Render and most container platforms inject PORT. An explicit Kaivor
        # value takes precedence, preserving local development behaviour.
        port_raw = source.get("KAIVOR_MCP_PORT") or source.get("PORT") or "8001"
        port_env = dict(source)
        port_env["_KAIVOR_MCP_EFFECTIVE_PORT"] = str(port_raw)
        port = _integer(port_env, "_KAIVOR_MCP_EFFECTIVE_PORT", 8001, 1, 65535)
        log_level = source.get("KAIVOR_MCP_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in _ALLOWED_LOG_LEVELS:
            raise ValueError("KAIVOR_MCP_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.")

        config = cls(
            environment=environment,
            host=host,
            port=port,
            log_level=log_level,
            max_concurrency=_integer(source, "KAIVOR_MCP_MAX_CONCURRENCY", 100, 1, 2000),
            graceful_shutdown_seconds=_integer(source, "KAIVOR_MCP_GRACEFUL_SHUTDOWN_SECONDS", 30, 1, 300),
            keep_alive_seconds=_integer(source, "KAIVOR_MCP_KEEP_ALIVE_SECONDS", 5, 1, 120),
        )

        if environment == "production":
            if source.get("KAIVOR_MCP_REQUIRE_POSTGRES", "true").strip().lower() != "true":
                raise ValueError("Production requires KAIVOR_MCP_REQUIRE_POSTGRES=true.")
            database_url = source.get("KAIVOR_AGENT_DATABASE_URL", "").strip()
            try:
                parsed = urlsplit(database_url)
                valid_database_url = parsed.scheme in {"postgres", "postgresql", "postgresql+psycopg"} and bool(parsed.hostname)
            except ValueError:
                valid_database_url = False
            if not valid_database_url:
                raise ValueError("Production requires a valid PostgreSQL KAIVOR_AGENT_DATABASE_URL.")
            if host not in {"0.0.0.0", "127.0.0.1"}:
                raise ValueError("Production KAIVOR_MCP_HOST must be 0.0.0.0 or 127.0.0.1.")
            _validate_production_auth(source)

        return config
