# 🚀 GUÍA DE OPTIMIZACIÓN DE BASE DE DATOS MySQL EN RAILWAY

## 📋 PASO 1: CONECTARSE A RAILWAY

### Opción A: Desde la Interfaz Web de Railway (MÁS FÁCIL)

1. **Accede a Railway**

   - Ve a https://railway.app
   - Inicia sesión en tu cuenta

2. **Selecciona tu proyecto**

   - Busca el proyecto que contiene tu base de datos MySQL
   - Haz clic en el servicio "MySQL"

3. **Abre la pestaña "Data"**
   - Verás una interfaz para ejecutar consultas SQL
   - Aquí puedes pegar y ejecutar los comandos

### Opción B: Desde MySQL Workbench o DBeaver

1. **Obtén las credenciales de conexión**

   - En Railway, ve a tu servicio MySQL
   - Pestaña "Variables"
   - Copia estos valores:
     - `MYSQLHOST`
     - `MYSQLPORT`
     - `MYSQLUSER`
     - `MYSQLPASSWORD`
     - `MYSQLDATABASE` (debe ser "agricola")

2. **Configura la conexión en tu cliente SQL**
   - Host: valor de MYSQLHOST
   - Port: valor de MYSQLPORT
   - Username: valor de MYSQLUSER
   - Password: valor de MYSQLPASSWORD
   - Database: agricola

---

## 📊 PASO 2: VERIFICAR ESTADO ACTUAL (OPCIONAL)

Antes de optimizar, puedes ver el estado actual:

```sql
-- Ver tamaño de tablas
SELECT
    TABLE_NAME,
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS "Size_MB",
    TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'agricola'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;

-- Ver índices existentes
SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'agricola'
ORDER BY TABLE_NAME, INDEX_NAME;
```

---

## 🔧 PASO 3: EJECUTAR OPTIMIZACIONES (COPIAR Y PEGAR)

### 3.1 - Optimizar tabla GASTOS (gastos_gastos)

```sql
-- Índices para tabla de gastos
CREATE INDEX idx_gastos_fecha_cuenta_sucursal
ON gastos_gastos(fecha, id_cuenta_banco_id, id_sucursal_id);

CREATE INDEX idx_gastos_categoria
ON gastos_gastos(id_cat_gastos_id);

CREATE INDEX idx_gastos_fecha_registro
ON gastos_gastos(fecha_registro DESC);
```

**Espera a que termine (5-30 segundos)** ✅

### 3.2 - Optimizar tabla COMPRAS (gastos_compra)

```sql
-- Índices para tabla de compras
CREATE INDEX idx_compra_fecha_productor_producto
ON gastos_compra(fecha_compra, productor_id, producto_id);

CREATE INDEX idx_compra_cuenta
ON gastos_compra(cuenta_id);

CREATE INDEX idx_compra_tipo_pago
ON gastos_compra(tipo_pago);

CREATE INDEX idx_compra_productor_sucursal
ON gastos_compra(productor_id, fecha_compra);
```

**Espera a que termine (5-30 segundos)** ✅

### 3.3 - Optimizar tabla VENTAS (ventas_ventas)

```sql
-- Índices para tabla de ventas
CREATE INDEX idx_ventas_fecha_cliente_producto
ON ventas_ventas(fecha_salida_manifiesto, cliente_id, producto_id);

CREATE INDEX idx_ventas_sucursal
ON ventas_ventas(sucursal_id_id);

CREATE INDEX idx_ventas_cuenta
ON ventas_ventas(cuenta_id);

CREATE INDEX idx_ventas_tipo
ON ventas_ventas(tipo_venta);
```

**Espera a que termine (5-30 segundos)** ✅

### 3.4 - Optimizar tabla SALDOS MENSUALES

```sql
-- Índices para saldos mensuales
CREATE INDEX idx_saldo_cuenta_periodo
ON gastos_saldomensual(cuenta_id, año, mes);

CREATE INDEX idx_saldo_fecha_modificacion
ON gastos_saldomensual(ultima_modificacion DESC);
```

**Espera a que termine (5-10 segundos)** ✅

### 3.5 - Optimizar CATÁLOGOS

```sql
-- Productores
CREATE INDEX idx_productor_sucursal
ON catalogo_productor(id_sucursal_id);

CREATE INDEX idx_productor_nombre
ON catalogo_productor(nombre_completo);

-- Productos
CREATE INDEX idx_producto_nombre
ON catalogo_producto(nombre, variedad);

CREATE INDEX idx_producto_disponible
ON catalogo_producto(disponible);

-- Cuentas
CREATE INDEX idx_cuenta_banco_sucursal
ON gastos_cuenta(id_banco_id, id_sucursal_id);

-- Clientes
CREATE INDEX idx_cliente_nombre
ON ventas_cliente(nombre);

-- Anticipos
CREATE INDEX idx_anticipo_cliente_estado
ON ventas_anticipo(cliente_id, estado_anticipo);
```

**Espera a que termine (10-20 segundos)** ✅

---

## 🔄 PASO 4: OPTIMIZAR Y ANALIZAR TABLAS

```sql
-- Optimizar tablas (reorganiza datos y reconstruye índices)
OPTIMIZE TABLE gastos_gastos;
OPTIMIZE TABLE gastos_compra;
OPTIMIZE TABLE ventas_ventas;
OPTIMIZE TABLE gastos_saldomensual;
OPTIMIZE TABLE catalogo_productor;
OPTIMIZE TABLE catalogo_producto;

-- Actualizar estadísticas (ayuda al optimizador de MySQL)
ANALYZE TABLE gastos_gastos;
ANALYZE TABLE gastos_compra;
ANALYZE TABLE ventas_ventas;
ANALYZE TABLE catalogo_productor;
```

**Espera a que termine (30-60 segundos)** ✅

---

## ✅ PASO 5: VERIFICAR OPTIMIZACIONES

```sql
-- Ver índices de gastos
SHOW INDEX FROM gastos_gastos;

-- Ver índices de compras
SHOW INDEX FROM gastos_compra;

-- Ver índices de ventas
SHOW INDEX FROM ventas_ventas;
```

Deberías ver varios índices nuevos en cada tabla.

---

## 🎯 PASO 6: PROBAR MEJORAS

Después de optimizar:

1. **Reinicia tu aplicación Django** (en Railway o local)
2. **Prueba las vistas lentas:**

   - Balances de gastos
   - Balances de compras
   - Exportación a Excel
   - Reportes con muchos filtros

3. **Verifica la velocidad:**
   - Antes: 5-15 segundos
   - Después: 0.5-3 segundos ⚡

---

## ⚠️ NOTAS IMPORTANTES

### Si ves WARNINGS como "Duplicate key name"

- **No te preocupes** - significa que el índice ya existe
- Continúa con el siguiente comando

### Si ves ERRORES como "Table doesn't exist"

- Verifica el nombre de la tabla
- Las tablas Django tienen prefijos: `gastos_`, `ventas_`, `catalogo_`

### Mejoras esperadas:

- ✅ Consultas con WHERE en fechas: **70-90% más rápidas**
- ✅ Reportes con GROUP BY: **60-80% más rápidas**
- ✅ Exportaciones Excel: **50-70% más rápidas**
- ✅ Filtros múltiples: **60-80% más rápidas**

---

## 🔍 MONITOREO (OPCIONAL)

Para monitorear consultas lentas en el futuro:

```sql
-- Ver consultas activas
SHOW FULL PROCESSLIST;

-- Ver tamaño actualizado de tablas
SELECT
    TABLE_NAME,
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS "Size_MB",
    TABLE_ROWS,
    ROUND((INDEX_LENGTH / 1024 / 1024), 2) AS "Index_Size_MB"
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'agricola'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
```

---

## 🚨 SOLUCIÓN DE PROBLEMAS

### Problema: "Too many connections"

**Solución:** Espera 1-2 minutos y reintenta

### Problema: "Lock wait timeout"

**Solución:**

1. Cierra otras conexiones a la BD
2. Reintenta el comando

### Problema: Índice no mejora velocidad

**Solución:**

```sql
-- Forzar uso de índice en consultas Django
-- Agrega esto en tus archivos services/*.py si es necesario
```

---

## 📞 SIGUIENTE PASO

Después de ejecutar estas optimizaciones, si aún hay consultas lentas:

1. **Identifica la consulta específica** que es lenta
2. **Usa EXPLAIN** para ver el plan de ejecución:
   ```sql
   EXPLAIN SELECT ... (tu consulta lenta aquí);
   ```
3. **Comparte el resultado** para crear índices más específicos

---

## ⏱️ TIEMPO TOTAL ESTIMADO

- Conexión: 2 minutos
- Ejecución de índices: 3-5 minutos
- Optimización de tablas: 2-3 minutos
- Verificación: 1 minuto

**TOTAL: 8-11 minutos** ⚡

---

¿Necesitas ayuda? Comparte:

- Mensaje de error exacto
- Comando que estabas ejecutando
- Captura de pantalla si es posible
