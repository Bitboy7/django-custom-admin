"""
Script de optimización automática de base de datos MySQL
Ejecutar con: python manage.py shell < optimize_db_auto.py
O desde Django shell: exec(open('optimize_db_auto.py').read())
"""

from django.db import connection
import time

def ejecutar_sql(sql, descripcion):
    """Ejecuta un comando SQL y reporta el resultado"""
    try:
        with connection.cursor() as cursor:
            inicio = time.time()
            cursor.execute(sql)
            fin = time.time()
            tiempo = round(fin - inicio, 2)
            print(f"✅ {descripcion} - Completado en {tiempo}s")
            return True
    except Exception as e:
        if "Duplicate key name" in str(e):
            print(f"⚠️  {descripcion} - Ya existe (ignorado)")
            return True
        else:
            print(f"❌ {descripcion} - ERROR: {str(e)}")
            return False

def optimizar_base_datos():
    """Ejecuta todas las optimizaciones de la base de datos"""
    
    print("="*70)
    print("🚀 INICIANDO OPTIMIZACIÓN DE BASE DE DATOS MySQL")
    print("="*70)
    print()
    
    tiempo_inicio = time.time()
    exitosas = 0
    fallidas = 0
    
    # ========================================================================
    # PASO 1: TABLA GASTOS
    # ========================================================================
    print("📊 PASO 1: Optimizando tabla GASTOS...")
    print("-" * 70)
    
    indices_gastos = [
        (
            "CREATE INDEX idx_gastos_fecha_cuenta_sucursal ON gastos_gastos(fecha, id_cuenta_banco_id, id_sucursal_id)",
            "Índice compuesto fecha-cuenta-sucursal"
        ),
        (
            "CREATE INDEX idx_gastos_categoria ON gastos_gastos(id_cat_gastos_id)",
            "Índice categoría"
        ),
        (
            "CREATE INDEX idx_gastos_fecha_registro ON gastos_gastos(fecha_registro DESC)",
            "Índice fecha_registro"
        ),
    ]
    
    for sql, desc in indices_gastos:
        if ejecutar_sql(sql, desc):
            exitosas += 1
        else:
            fallidas += 1
    
    print()
    
    # ========================================================================
    # PASO 2: TABLA COMPRAS
    # ========================================================================
    print("🛒 PASO 2: Optimizando tabla COMPRAS...")
    print("-" * 70)
    
    indices_compras = [
        (
            "CREATE INDEX idx_compra_fecha_productor_producto ON gastos_compra(fecha_compra, productor_id, producto_id)",
            "Índice compuesto fecha-productor-producto"
        ),
        (
            "CREATE INDEX idx_compra_cuenta ON gastos_compra(cuenta_id)",
            "Índice cuenta"
        ),
        (
            "CREATE INDEX idx_compra_tipo_pago ON gastos_compra(tipo_pago)",
            "Índice tipo_pago"
        ),
        (
            "CREATE INDEX idx_compra_productor_sucursal ON gastos_compra(productor_id, fecha_compra)",
            "Índice productor-fecha"
        ),
        (
            "CREATE INDEX idx_compra_fecha_registro ON gastos_compra(fecha_registro DESC)",
            "Índice fecha_registro"
        ),
    ]
    
    for sql, desc in indices_compras:
        if ejecutar_sql(sql, desc):
            exitosas += 1
        else:
            fallidas += 1
    
    print()
    
    # ========================================================================
    # PASO 3: TABLA VENTAS
    # ========================================================================
    print("💰 PASO 3: Optimizando tabla VENTAS...")
    print("-" * 70)
    
    indices_ventas = [
        (
            "CREATE INDEX idx_ventas_fecha_cliente_producto ON ventas_ventas(fecha_salida_manifiesto, cliente_id, producto_id)",
            "Índice compuesto fecha-cliente-producto"
        ),
        (
            "CREATE INDEX idx_ventas_sucursal ON ventas_ventas(sucursal_id_id)",
            "Índice sucursal"
        ),
        (
            "CREATE INDEX idx_ventas_cuenta ON ventas_ventas(cuenta_id)",
            "Índice cuenta"
        ),
        (
            "CREATE INDEX idx_ventas_tipo ON ventas_ventas(tipo_venta)",
            "Índice tipo_venta"
        ),
        (
            "CREATE INDEX idx_ventas_fecha_deposito ON ventas_ventas(fecha_deposito)",
            "Índice fecha_deposito"
        ),
    ]
    
    for sql, desc in indices_ventas:
        if ejecutar_sql(sql, desc):
            exitosas += 1
        else:
            fallidas += 1
    
    print()
    
    # ========================================================================
    # PASO 4: TABLA SALDOS MENSUALES
    # ========================================================================
    print("💵 PASO 4: Optimizando tabla SALDOS MENSUALES...")
    print("-" * 70)
    
    indices_saldos = [
        (
            "CREATE INDEX idx_saldo_cuenta_periodo ON gastos_saldomensual(cuenta_id, año, mes)",
            "Índice cuenta-periodo"
        ),
        (
            "CREATE INDEX idx_saldo_fecha_modificacion ON gastos_saldomensual(ultima_modificacion DESC)",
            "Índice última_modificación"
        ),
    ]
    
    for sql, desc in indices_saldos:
        if ejecutar_sql(sql, desc):
            exitosas += 1
        else:
            fallidas += 1
    
    print()
    
    # ========================================================================
    # PASO 5: CATÁLOGOS
    # ========================================================================
    print("📚 PASO 5: Optimizando CATÁLOGOS...")
    print("-" * 70)
    
    indices_catalogos = [
        (
            "CREATE INDEX idx_productor_sucursal ON catalogo_productor(id_sucursal_id)",
            "Índice productor-sucursal"
        ),
        (
            "CREATE INDEX idx_productor_nombre ON catalogo_productor(nombre_completo)",
            "Índice productor-nombre"
        ),
        (
            "CREATE INDEX idx_producto_nombre ON catalogo_producto(nombre, variedad)",
            "Índice producto-nombre-variedad"
        ),
        (
            "CREATE INDEX idx_producto_disponible ON catalogo_producto(disponible)",
            "Índice producto-disponible"
        ),
        (
            "CREATE INDEX idx_cuenta_banco_sucursal ON gastos_cuenta(id_banco_id, id_sucursal_id)",
            "Índice cuenta-banco-sucursal"
        ),
        (
            "CREATE INDEX idx_cliente_nombre ON ventas_cliente(nombre)",
            "Índice cliente-nombre"
        ),
        (
            "CREATE INDEX idx_anticipo_cliente_estado ON ventas_anticipo(cliente_id, estado_anticipo)",
            "Índice anticipo-cliente-estado"
        ),
        (
            "CREATE INDEX idx_anticipo_fecha ON ventas_anticipo(fecha)",
            "Índice anticipo-fecha"
        ),
    ]
    
    for sql, desc in indices_catalogos:
        if ejecutar_sql(sql, desc):
            exitosas += 1
        else:
            fallidas += 1
    
    print()
    
    # ========================================================================
    # PASO 6: OPTIMIZAR TABLAS
    # ========================================================================
    print("🔧 PASO 6: OPTIMIZANDO y ANALIZANDO tablas...")
    print("-" * 70)
    
    tablas_optimizar = [
        "gastos_gastos",
        "gastos_compra",
        "ventas_ventas",
        "gastos_saldomensual",
        "catalogo_productor",
        "catalogo_producto",
        "gastos_cuenta",
        "ventas_cliente",
        "ventas_anticipo",
    ]
    
    for tabla in tablas_optimizar:
        # OPTIMIZE TABLE
        if ejecutar_sql(f"OPTIMIZE TABLE {tabla}", f"Optimizar {tabla}"):
            exitosas += 1
        else:
            fallidas += 1
        
        # ANALYZE TABLE
        if ejecutar_sql(f"ANALYZE TABLE {tabla}", f"Analizar {tabla}"):
            exitosas += 1
        else:
            fallidas += 1
    
    print()
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    tiempo_total = round(time.time() - tiempo_inicio, 2)
    
    print("="*70)
    print("📊 RESUMEN DE OPTIMIZACIÓN")
    print("="*70)
    print(f"✅ Operaciones exitosas: {exitosas}")
    print(f"❌ Operaciones fallidas: {fallidas}")
    print(f"⏱️  Tiempo total: {tiempo_total} segundos")
    print()
    
    if fallidas == 0:
        print("🎉 ¡OPTIMIZACIÓN COMPLETADA CON ÉXITO!")
        print()
        print("📈 Mejoras esperadas:")
        print("   • Consultas con filtros de fecha: 70-90% más rápidas")
        print("   • Reportes con agregaciones: 60-80% más rápidas")
        print("   • Exportaciones Excel/PDF: 50-70% más rápidas")
        print()
        print("🔄 Reinicia tu aplicación Django para aplicar los cambios")
    else:
        print("⚠️  Optimización completada con algunos errores")
        print("   Revisa los mensajes de error arriba")
    
    print("="*70)
    
    # Mostrar información de índices creados
    print()
    print("📋 VERIFICANDO ÍNDICES EN TABLAS PRINCIPALES...")
    print("-" * 70)
    
    tablas_verificar = ["gastos_gastos", "gastos_compra", "ventas_ventas"]
    
    for tabla in tablas_verificar:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW INDEX FROM {tabla}")
                indices = cursor.fetchall()
                print(f"\n{tabla.upper()}: {len(indices)} índices")
                for idx in indices:
                    nombre_idx = idx[2]
                    columna = idx[4]
                    if not nombre_idx.startswith('PRIMARY'):
                        print(f"  • {nombre_idx}: {columna}")
        except Exception as e:
            print(f"  Error al verificar: {e}")
    
    print()
    print("="*70)

# Ejecutar optimización
if __name__ == "__main__":
    optimizar_base_datos()
else:
    # Si se ejecuta desde Django shell
    print("Ejecutando optimización...")
    optimizar_base_datos()
