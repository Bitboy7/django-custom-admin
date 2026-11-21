"""CLI entry point: ``python -m mcp_server --transport stdio|http``."""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys

from .config import ConfigError, Settings
from .server import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m mcp_server",
        description="Servidor MCP de reportes de solo lectura (ERP Agrícola de la Costa).",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio para clientes locales; http para clientes remotos (requiere MCP_HTTP_TOKEN).",
    )
    parser.add_argument("--host", help="Sobrescribe MCP_HTTP_HOST")
    parser.add_argument("--port", type=int, help="Sobrescribe MCP_HTTP_PORT")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        settings = Settings.from_env()
        if args.host or args.port:
            settings = dataclasses.replace(
                settings,
                http_host=args.host or settings.http_host,
                http_port=args.port or settings.http_port,
            )
        run(settings, args.transport)
    except ConfigError as exc:
        print(f"Configuración inválida: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
