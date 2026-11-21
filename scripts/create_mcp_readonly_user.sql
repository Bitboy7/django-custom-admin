-- ============================================================================
-- Usuario MySQL de SOLO LECTURA para el servidor MCP de reportes
-- Ejecutar como administrador (root) una sola vez por entorno:
--   mysql -u root -p < scripts/create_mcp_readonly_user.sql
--
-- Antes de ejecutar:
--   1. Reemplaza CHANGE_ME por una contraseña larga y aleatoria.
--   2. Ajusta el nombre de la base de datos si no es agricola_costa_db.
--   3. Define la misma contraseña en MCP_DB_PASSWORD del .env del servidor MCP.
--
-- Este usuario NO puede escribir, borrar, crear ni alterar nada.
-- ============================================================================

-- Usuario para conexiones locales y para contenedores/red interna.
CREATE USER IF NOT EXISTS 'mcp_readonly'@'localhost' IDENTIFIED BY 'CHANGE_ME';
CREATE USER IF NOT EXISTS 'mcp_readonly'@'%' IDENTIFIED BY 'CHANGE_ME';
ALTER USER 'mcp_readonly'@'localhost' IDENTIFIED BY 'CHANGE_ME';
ALTER USER 'mcp_readonly'@'%' IDENTIFIED BY 'CHANGE_ME';

-- Solo SELECT sobre las tablas de reporte (misma lista que mcp_server/allowlist.py).
GRANT SELECT ON agricola_costa_db.ventas_ventas          TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.ventas_pagoventa       TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.ventas_cliente         TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.gastos_gastos          TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.gastos_compra          TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.gastos_catgastos       TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.gastos_cuenta          TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.gastos_banco           TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.gastos_saldomensual    TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.catalogo_producto      TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.catalogo_productor     TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.catalogo_sucursal      TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.catalogo_pais          TO 'mcp_readonly'@'localhost';
GRANT SELECT ON agricola_costa_db.catalogo_estado        TO 'mcp_readonly'@'localhost';

GRANT SELECT ON agricola_costa_db.ventas_ventas          TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.ventas_pagoventa       TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.ventas_cliente         TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.gastos_gastos          TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.gastos_compra          TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.gastos_catgastos       TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.gastos_cuenta          TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.gastos_banco           TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.gastos_saldomensual    TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.catalogo_producto      TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.catalogo_productor     TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.catalogo_sucursal      TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.catalogo_pais          TO 'mcp_readonly'@'%';
GRANT SELECT ON agricola_costa_db.catalogo_estado        TO 'mcp_readonly'@'%';

FLUSH PRIVILEGES;

-- Verificación: debe mostrar únicamente privilegios SELECT.
SHOW GRANTS FOR 'mcp_readonly'@'%';
