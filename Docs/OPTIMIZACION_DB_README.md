# 🚀 OPTIMIZACIÓN DE BASE DE DATOS MySQL - RESUMEN RÁPIDO

Tu base de datos está lenta porque **faltan índices** en columnas que usas frecuentemente en consultas (fechas, FKs, filtros).

## 📊 PROBLEMA IDENTIFICADO

- ❌ Consultas de balances tardan 5-15 segundos
- ❌ Exportaciones Excel/PDF muy lentas
- ❌ Filtros con múltiples campos tardan mucho
- ❌ Reportes con agregaciones (SUM, COUNT) lentos

**CAUSA:** Faltan índices en tablas `gastos_gastos`, `gastos_compra`, `ventas_ventas`

---

## ⚡ SOLUCIÓN RÁPIDA (3 OPCIONES)

### OPCIÓN 1: Comando Django (MÁS FÁCIL) ⭐

```bash
# Desde tu terminal local o en Railway
python manage.py optimize_database
```

**Ventajas:**

- ✅ Automático y seguro
- ✅ Muestra progreso en tiempo real
- ✅ Maneja errores automáticamente

---

### OPCIÓN 2: Desde Railway Web (SIN CÓDIGO)

1. Ve a https://railway.app
2. Selecciona tu proyecto → MySQL → Pestaña "Data"
3. Copia y pega este bloque completo:

```sql
-- GASTOS
CREATE INDEX idx_gastos_fecha_cuenta_sucursal ON gastos_gastos(fecha, id_cuenta_banco_id, id_sucursal_id);
CREATE INDEX idx_gastos_categoria ON gastos_gastos(id_cat_gastos_id);

-- COMPRAS
CREATE INDEX idx_compra_fecha_productor_producto ON gastos_compra(fecha_compra, productor_id, producto_id);
CREATE INDEX idx_compra_cuenta ON gastos_compra(cuenta_id);
CREATE INDEX idx_compra_tipo_pago ON gastos_compra(tipo_pago);

-- VENTAS
CREATE INDEX idx_ventas_fecha_cliente_producto ON ventas_ventas(fecha_salida_manifiesto, cliente_id, producto_id);
CREATE INDEX idx_ventas_sucursal ON ventas_ventas(sucursal_id_id);
CREATE INDEX idx_ventas_cuenta ON ventas_ventas(cuenta_id);

-- OPTIMIZAR TABLAS
OPTIMIZE TABLE gastos_gastos, gastos_compra, ventas_ventas;
ANALYZE TABLE gastos_gastos, gastos_compra, ventas_ventas;
```

4. Presiona "Execute" o "Run"

---

### OPCIÓN 3: Script Python Automático

```bash
# Desde tu terminal
python manage.py shell < optimize_db_auto.py
```

---

## 📈 RESULTADOS ESPERADOS

Después de la optimización:

| Operación            | Antes  | Después | Mejora     |
| -------------------- | ------ | ------- | ---------- |
| Balances con filtros | 8-15s  | 1-3s    | **80%** ⚡ |
| Exportación Excel    | 10-20s | 2-4s    | **75%** ⚡ |
| Reportes agregados   | 5-12s  | 1-2s    | **85%** ⚡ |
| Consultas con fechas | 3-8s   | 0.5-1s  | **90%** ⚡ |

---

## ✅ VERIFICACIÓN

Después de ejecutar la optimización:

```sql
-- Ver índices creados
SHOW INDEX FROM gastos_gastos;
SHOW INDEX FROM gastos_compra;
SHOW INDEX FROM ventas_ventas;
```

Deberías ver varios índices nuevos (idx*gastos*_, idx*compra*_, idx*ventas*\*)

---

## 🎯 PRUEBAS

1. **Reinicia tu app** (Railway lo hace automáticamente)
2. **Prueba estas vistas:**

   - 📊 Balances de gastos con filtros de fecha
   - 🛒 Balances de compras por productor
   - 📑 Exportación Excel "Resumen"
   - 💰 Reportes de ventas

3. **Compara velocidad:**
   - Abre DevTools (F12) → Network
   - Filtra por "balances" o "compras"
   - Verifica tiempo de respuesta

---

## 🔍 MONITOREO CONTINUO

### Ver tamaño de tablas:

```sql
SELECT
    TABLE_NAME,
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS "Size_MB",
    TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'agricola'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
```

### Ver consultas activas:

```sql
SHOW FULL PROCESSLIST;
```

---

## ⚠️ NOTAS IMPORTANTES

1. **"Duplicate key name" es NORMAL** - significa que el índice ya existe
2. **Los índices ocupan espacio** - pero mejoran velocidad dramáticamente
3. **Tiempo de ejecución:** 3-5 minutos en total
4. **Sin downtime** - la app sigue funcionando durante la optimización

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### ❌ Error: "Table doesn't exist"

**Causa:** Nombre de tabla incorrecto
**Solución:** Verifica que uses los prefijos correctos (`gastos_`, `ventas_`, `catalogo_`)

### ❌ Error: "Too many connections"

**Solución:** Espera 1-2 minutos y reintenta

### ❌ Sigue lento después de optimizar

**Siguiente paso:**

1. Identifica la consulta lenta específica
2. Ejecuta: `EXPLAIN SELECT ... (tu consulta)`
3. Comparte el resultado para crear índices más específicos

---

## 📁 ARCHIVOS INCLUIDOS

1. **optimize_database.sql** - Script SQL completo manual
2. **GUIA_OPTIMIZACION_RAILWAY.md** - Guía detallada paso a paso
3. **optimize_db_auto.py** - Script Python automático
4. **app/management/commands/optimize_database.py** - Comando Django

---

## 🚀 SIGUIENTE PASO

**Ejecuta OPCIÓN 1** (recomendado):

```bash
python manage.py optimize_database
```

O **OPCIÓN 2** desde Railway Web (más visual)

Tiempo: **5 minutos** ⏱️

---

## 📞 ¿Necesitas ayuda?

Si encuentras algún error:

1. Copia el mensaje de error completo
2. Indica qué opción estabas usando
3. Comparte captura de pantalla si es posible

---

**Creado para:** django-custom-admin  
**Base de datos:** MySQL en Railway (agricola)  
**Fecha:** Diciembre 2025
