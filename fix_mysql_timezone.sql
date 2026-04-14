-- Script para habilitar timezone support en MySQL/MariaDB en Windows
-- Ejecutar con: mysql -u root -p < fix_mysql_timezone.sql

-- Opción 1: Configurar timezone a UTC (solución rápida)
SET GLOBAL time_zone = '+00:00';

-- Verificar configuración actual
SELECT @@global.time_zone, @@session.time_zone;

-- NOTA: Para solución completa, necesitas:
-- 1. Descargar timezone data de: https://dev.mysql.com/downloads/timezones.html
-- 2. Importar el archivo SQL correspondiente a tu versión de MySQL
-- 3. O en Linux/Mac usar: mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql
