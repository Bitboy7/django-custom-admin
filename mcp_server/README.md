# MCP de reportes (solo lectura)

Servidor [MCP](https://modelcontextprotocol.io) que expone los datos de ventas, cartera,
gastos y compras del ERP para consultarlos en lenguaje natural desde Claude, ChatGPT o
cualquier cliente compatible.

Construido siguiendo `.agents/skills/backend-dev-guidelines`.

## Modelo de seguridad (3 barreras)

1. **Usuario MySQL dedicado `mcp_readonly`** con `GRANT SELECT` únicamente sobre las
   tablas de reporte. No puede escribir, borrar ni alterar el esquema.
2. **Allowlist en código** (`mcp_server/allowlist.py`): solo 14 tablas; el resto
   (`auth_user`, sesiones, 2FA, auditoría) es inaccesible.
3. **Guard de SQL** (`mcp_server/guard.py`): una sentencia, solo `SELECT`,
   sin `SELECT *`, sin columnas personales, `LIMIT` forzado y `MAX_EXECUTION_TIME`.

La conexión además abre cada sesión en modo `READ ONLY`.

## Instalación

```powershell
# Desde la raíz del repo, con el venv activo
pip install -r requirements-mcp.txt
```

Crear el usuario de solo lectura (una vez por entorno, como root):

```powershell
mysql -u root -p < scripts/create_mcp_readonly_user.sql
```

Antes de ejecutarlo cambia `CHANGE_ME` por una contraseña larga.

## Variables de entorno

| Variable | Obligatoria | Default | Descripción |
|---|---|---|---|
| `MCP_DB_HOST` | sí | `DB_HOST` o `127.0.0.1` | Host MySQL |
| `MCP_DB_PORT` | no | `DB_PORT` o `3306` | Puerto (dev Docker: `3307`) |
| `MCP_DB_NAME` | sí | `DB_NAME` | Base de datos |
| `MCP_DB_USER` | sí | `mcp_readonly` | Usuario SELECT-only |
| `MCP_DB_PASSWORD` | sí | — | Contraseña del usuario |
| `MCP_MAX_ROWS` | no | `500` | Filas máximas por respuesta |
| `MCP_QUERY_TIMEOUT_MS` | no | `10000` | `MAX_EXECUTION_TIME` |
| `MCP_HTTP_HOST` | no | `127.0.0.1` | Bind HTTP |
| `MCP_HTTP_PORT` | no | `8765` | Puerto HTTP |
| `MCP_HTTP_PATH` | no | `/mcp` | Ruta del endpoint MCP |
| `MCP_HTTP_TOKEN` | sí para HTTP | — | Bearer token (mín. 32 chars) |
| `MCP_ALLOW_NO_AUTH` | no | `false` | Solo para redes privadas de confianza |
| `MCP_LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. Logs a stderr con formato `fecha nivel logger: mensaje`; en `DEBUG` también se registra el SQL ejecutado |

## Uso local (stdio)

```powershell
python -m mcp_server --transport stdio
```

Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agricola-reportes": {
      "command": "C:\\Users\\dev-y\\Documents\\django-custom-admin\\venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server", "--transport", "stdio"],
      "env": {
        "PYTHONPATH": "C:\\Users\\dev-y\\Documents\\django-custom-admin"
      }
    }
  }
}
```

`PYTHONPATH` es obligatorio: Claude Desktop no garantiza que el directorio de trabajo
sea la raíz del repo, y sin él `python -m mcp_server` termina con
`ModuleNotFoundError` (verás "Server disconnected"). Las credenciales se leen del
`.env` del proyecto por ruta absoluta.

Reinicia Claude Desktop y verifica que aparezca el servidor y sus tools.

## Uso remoto (HTTP + Bearer)

```powershell
$env:MCP_HTTP_TOKEN = "un-token-largo-y-aleatorio"
python -m mcp_server --transport http
```

- Endpoint MCP: `http://127.0.0.1:8765/mcp`
- Salud: `http://127.0.0.1:8765/health`

Prueba rápida:

```powershell
curl.exe -H "Authorization: Bearer $env:MCP_HTTP_TOKEN" http://127.0.0.1:8765/health
```

En producción pon el servicio detrás de HTTPS (Nginx/Traefik) y no expongas el puerto
directo a Internet.

**ChatGPT web:** hoy exige OAuth 2.1 para conectores MCP; el Bearer token sirve para
Claude Desktop, clientes locales y despliegues privados. OAuth queda como fase 2.

## Tools disponibles

| Tool | Para qué |
|---|---|
| `listar_tablas` | Descubrir tablas y su propósito |
| `describir_tabla` | Columnas y tipos (oculta PII) |
| `resumen_financiero` | Ventas, gastos, compras y cartera por moneda |
| `resumen_ventas` | Ventas por día/mes/año y moneda |
| `ventas_por_cliente` | Ranking con saldo pendiente |
| `ventas_por_producto` | Ventas por producto/variedad |
| `cartera_por_cliente` | Cuentas por cobrar por cliente |
| `cartera_vencida` | Antigüedad 1-30 / 31-60 / 61-90 / 90+ |
| `pagos_recientes` | Pagos del periodo |
| `resumen_gastos` | Gastos por periodo y moneda |
| `gastos_por_categoria` | Gasto por categoría |
| `compras_por_producto` | Compras por producto/variedad |
| `compras_por_productor` | Compras por productor |
| `saldo_mensual` | Saldos por banco y mes |
| `consultar_sql` | SELECT ad-hoc validado |

## Ejemplos de preguntas

- "¿Cómo cerró el año 2025? Dame ventas, gastos y cartera por moneda."
- "¿Qué clientes me deben más y cuánto está vencido a más de 90 días?"
- "¿Cuáles fueron los 10 productos más vendidos entre enero y junio de 2025?"
- "Compara gastos por categoría de 2024 contra 2025."
- "¿Cuánto compramos a cada productor este año?"

## Tests

```powershell
pytest mcp_server/tests -p no:django -q
```

Los tests validan el guard (escrituras, PII, tablas no permitidas, LIMIT) y que todas
las consultas curadas sean SELECT sobre tablas permitidas.

## Diagnóstico

- `Configuración inválida` → falta una variable en `.env` o en el bloque `env` del cliente.
- `Server disconnected` en Claude → falta `PYTHONPATH`; verifica que apunte a la raíz del repo.
- `HTTP 401` → el header `Authorization: Bearer <token>` falta o no coincide.
- `Table '...' doesn't exist` → revisa el nombre de la BD o corre las migraciones.
- `Access denied` → el usuario existe pero le faltan `GRANT SELECT`; vuelve a ejecutar el script.
- No aparece el servidor en Claude → revisa la ruta absoluta de `python.exe` y reinicia el cliente.
