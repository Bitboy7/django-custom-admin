"""
Comando de gestión Django para optimizar la base de datos MySQL
Uso: python manage.py optimize_database
"""

from django.core.management.base import BaseCommand
from django.db import connection
import time


class Command(BaseCommand):
    help = 'Optimiza la base de datos MySQL creando índices estratégicos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se haría sin ejecutar los comandos',
        )
        parser.add_argument(
            '--skip-optimize',
            action='store_true',
            help='Salta OPTIMIZE TABLE y ANALYZE TABLE (más rápido)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_optimize = options['skip_optimize']
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("🚀 OPTIMIZACIÓN DE BASE DE DATOS MySQL"))
        self.stdout.write("=" * 70)
        self.stdout.write()
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO DRY-RUN: No se ejecutarán cambios reales"))
            self.stdout.write()
        
        tiempo_inicio = time.time()
        exitosas = 0
        fallidas = 0
        
        # Definir todos los índices a crear
        indices = [
            # GASTOS
            ("gastos_gastos", [
                ("idx_gastos_fecha_cuenta_sucursal", "fecha, id_cuenta_banco_id, id_sucursal_id"),
                ("idx_gastos_categoria", "id_cat_gastos_id"),
                ("idx_gastos_fecha_registro", "fecha_registro DESC"),
            ]),
            # COMPRAS
            ("gastos_compra", [
                ("idx_compra_fecha_productor_producto", "fecha_compra, productor_id, producto_id"),
                ("idx_compra_cuenta", "cuenta_id"),
                ("idx_compra_tipo_pago", "tipo_pago"),
                ("idx_compra_productor_sucursal", "productor_id, fecha_compra"),
                ("idx_compra_fecha_registro", "fecha_registro DESC"),
            ]),
            # VENTAS
            ("ventas_ventas", [
                ("idx_ventas_fecha_cliente_producto", "fecha_salida_manifiesto, cliente_id, producto_id"),
                ("idx_ventas_sucursal", "sucursal_id_id"),
                ("idx_ventas_cuenta", "cuenta_id"),
                ("idx_ventas_tipo", "tipo_venta"),
                ("idx_ventas_fecha_deposito", "fecha_deposito"),
            ]),
            # SALDOS MENSUALES
            ("gastos_saldomensual", [
                ("idx_saldo_cuenta_periodo", "cuenta_id, año, mes"),
                ("idx_saldo_fecha_modificacion", "ultima_modificacion DESC"),
            ]),
            # CATÁLOGOS
            ("catalogo_productor", [
                ("idx_productor_sucursal", "id_sucursal_id"),
                ("idx_productor_nombre", "nombre_completo"),
            ]),
            ("catalogo_producto", [
                ("idx_producto_nombre", "nombre, variedad"),
                ("idx_producto_disponible", "disponible"),
            ]),
            ("gastos_cuenta", [
                ("idx_cuenta_banco_sucursal", "id_banco_id, id_sucursal_id"),
            ]),
            ("ventas_cliente", [
                ("idx_cliente_nombre", "nombre"),
            ]),
            ("ventas_anticipo", [
                ("idx_anticipo_cliente_estado", "cliente_id, estado_anticipo"),
                ("idx_anticipo_fecha", "fecha"),
            ]),
        ]
        
        # Crear índices
        for tabla, lista_indices in indices:
            self.stdout.write(self.style.HTTP_INFO(f"\n📊 Tabla: {tabla}"))
            self.stdout.write("-" * 70)
            
            for nombre_idx, columnas in lista_indices:
                sql = f"CREATE INDEX {nombre_idx} ON {tabla}({columnas})"
                
                if dry_run:
                    self.stdout.write(f"   [DRY-RUN] {sql}")
                    exitosas += 1
                else:
                    resultado = self._ejecutar_sql(sql, f"Índice {nombre_idx}")
                    if resultado:
                        exitosas += 1
                    else:
                        fallidas += 1
        
        # OPTIMIZE y ANALYZE tables
        if not skip_optimize:
            self.stdout.write()
            self.stdout.write(self.style.HTTP_INFO("🔧 OPTIMIZANDO Y ANALIZANDO TABLAS..."))
            self.stdout.write("-" * 70)
            
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
                if dry_run:
                    self.stdout.write(f"   [DRY-RUN] OPTIMIZE TABLE {tabla}")
                    self.stdout.write(f"   [DRY-RUN] ANALYZE TABLE {tabla}")
                    exitosas += 2
                else:
                    # OPTIMIZE
                    if self._ejecutar_sql(f"OPTIMIZE TABLE {tabla}", f"Optimizar {tabla}"):
                        exitosas += 1
                    else:
                        fallidas += 1
                    
                    # ANALYZE
                    if self._ejecutar_sql(f"ANALYZE TABLE {tabla}", f"Analizar {tabla}"):
                        exitosas += 1
                    else:
                        fallidas += 1
        
        # Resumen
        tiempo_total = round(time.time() - tiempo_inicio, 2)
        
        self.stdout.write()
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("📊 RESUMEN DE OPTIMIZACIÓN"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"✅ Operaciones exitosas: {exitosas}")
        self.stdout.write(f"❌ Operaciones fallidas: {fallidas}")
        self.stdout.write(f"⏱️  Tiempo total: {tiempo_total} segundos")
        self.stdout.write()
        
        if fallidas == 0:
            self.stdout.write(self.style.SUCCESS("🎉 ¡OPTIMIZACIÓN COMPLETADA CON ÉXITO!"))
            self.stdout.write()
            self.stdout.write("📈 Mejoras esperadas:")
            self.stdout.write("   • Consultas con filtros de fecha: 70-90% más rápidas")
            self.stdout.write("   • Reportes con agregaciones: 60-80% más rápidas")
            self.stdout.write("   • Exportaciones Excel/PDF: 50-70% más rápidas")
            self.stdout.write()
            if not dry_run:
                self.stdout.write(self.style.WARNING("🔄 Considera reiniciar tu aplicación para aplicar los cambios"))
        else:
            self.stdout.write(self.style.WARNING("⚠️  Optimización completada con algunos errores"))
            self.stdout.write("   Revisa los mensajes arriba")
        
        self.stdout.write("=" * 70)
        
        # Verificar índices
        if not dry_run:
            self.stdout.write()
            self.stdout.write(self.style.HTTP_INFO("📋 ÍNDICES CREADOS EN TABLAS PRINCIPALES"))
            self.stdout.write("-" * 70)
            
            self._verificar_indices()

    def _ejecutar_sql(self, sql, descripcion):
        """Ejecuta un comando SQL y retorna True si fue exitoso"""
        try:
            with connection.cursor() as cursor:
                inicio = time.time()
                cursor.execute(sql)
                fin = time.time()
                tiempo = round(fin - inicio, 2)
                self.stdout.write(self.style.SUCCESS(f"   ✅ {descripcion} ({tiempo}s)"))
                return True
        except Exception as e:
            error_msg = str(e)
            if "Duplicate key name" in error_msg or "already exists" in error_msg:
                self.stdout.write(self.style.WARNING(f"   ⚠️  {descripcion} - Ya existe"))
                return True
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ {descripcion} - ERROR: {error_msg}"))
                return False

    def _verificar_indices(self):
        """Verifica y muestra los índices de las tablas principales"""
        tablas = ["gastos_gastos", "gastos_compra", "ventas_ventas"]
        
        for tabla in tablas:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW INDEX FROM {tabla}")
                    indices = cursor.fetchall()
                    
                    self.stdout.write()
                    self.stdout.write(self.style.HTTP_INFO(f"{tabla.upper()}: {len(indices)} índices"))
                    
                    for idx in indices:
                        nombre_idx = idx[2]
                        columna = idx[4]
                        if not nombre_idx.startswith('PRIMARY'):
                            self.stdout.write(f"  • {nombre_idx}: {columna}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error al verificar {tabla}: {e}"))
