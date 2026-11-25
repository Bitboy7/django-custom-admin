"""Configuration loaded from environment variables.

The MCP server never reads Django settings. It connects to MySQL with a
dedicated SELECT-only user and every value comes from the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value.strip() == "":
        raise ConfigError(f"Falta la variable de entorno {name}")
    return value.strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser un entero") from exc
    if value <= 0:
        raise ConfigError(f"{name} debe ser mayor que cero")
    return value


LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def log_level_from_env() -> str:
    """MCP_LOG_LEVEL validated against the standard level names (INFO by default)."""
    level = (os.getenv("MCP_LOG_LEVEL") or "INFO").strip().upper()
    if level not in LOG_LEVELS:
        raise ConfigError(f"MCP_LOG_LEVEL debe ser uno de: {', '.join(LOG_LEVELS)}")
    return level


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    http_host: str = "127.0.0.1"
    http_port: int = 8765
    http_path: str = "/mcp"
    http_token: str | None = None
    max_rows: int = 500
    query_timeout_ms: int = 10000
    allow_no_auth: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("MCP_HTTP_TOKEN", "").strip() or None
        if token is not None and len(token) < 32:
            raise ConfigError("MCP_HTTP_TOKEN debe tener al menos 32 caracteres")
        path = os.getenv("MCP_HTTP_PATH", "/mcp").strip() or "/mcp"
        if not path.startswith("/"):
            raise ConfigError("MCP_HTTP_PATH debe comenzar con /")
        port_raw = (os.getenv("MCP_DB_PORT") or os.getenv("DB_PORT") or "3306").strip()
        try:
            default_port = int(port_raw)
        except ValueError as exc:
            raise ConfigError("MCP_DB_PORT/DB_PORT debe ser un entero") from exc
        return cls(
            db_host=_env("MCP_DB_HOST", os.getenv("DB_HOST", "127.0.0.1")),
            db_port=_env_int("MCP_DB_PORT", default_port),
            db_name=_env("MCP_DB_NAME", os.getenv("DB_NAME")),
            db_user=_env("MCP_DB_USER", "mcp_readonly"),
            db_password=_env("MCP_DB_PASSWORD"),
            http_host=os.getenv("MCP_HTTP_HOST", "127.0.0.1").strip() or "127.0.0.1",
            http_port=_env_int("MCP_HTTP_PORT", 8765),
            http_path=path,
            http_token=token,
            max_rows=_env_int("MCP_MAX_ROWS", 500),
            query_timeout_ms=_env_int("MCP_QUERY_TIMEOUT_MS", 10000),
            allow_no_auth=os.getenv("MCP_ALLOW_NO_AUTH", "false").strip().lower()
            in {"1", "true", "yes"},
            log_level=log_level_from_env(),
        )

    @property
    def database_url(self) -> str:
        return (
            "mysql+mysqldb://"
            f"{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )
