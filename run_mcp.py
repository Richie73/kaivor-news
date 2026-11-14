"""Run the standalone, protected Kaivor MCP service."""
from __future__ import annotations

import logging

from core.integrations.mcp_runtime import MCPRuntimeConfig


def main() -> None:
    try:
        config = MCPRuntimeConfig.from_environment()
    except ValueError as exc:
        raise SystemExit(f"Invalid Kaivor MCP runtime configuration: {exc}") from exc

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("Install dependencies: pip install -r requirements-mcp.txt") from exc

    from core.integrations.mcp_gateway import build_mcp_app

    app = build_mcp_app()
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        proxy_headers=False,
        access_log=False,
        server_header=False,
        workers=1,
        limit_concurrency=config.max_concurrency,
        timeout_graceful_shutdown=config.graceful_shutdown_seconds,
        timeout_keep_alive=config.keep_alive_seconds,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
