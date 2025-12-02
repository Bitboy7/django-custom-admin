"""
Comando de gestión Django para manejar Redis cache
Uso: 
  python manage.py cache_admin --stats
  python manage.py cache_admin --warm-up
  python manage.py cache_admin --clear
  python manage.py cache_admin --clear-pattern "balances*"
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from app.services.cache_service import cache_service, CacheUtils
import time


class Command(BaseCommand):
    help = 'Administrar Redis cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Mostrar estadísticas de cache',
        )
        parser.add_argument(
            '--warm-up',
            action='store_true',
            help='Precalentar cache con datos importantes',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar todo el cache',
        )
        parser.add_argument(
            '--clear-pattern',
            type=str,
            help='Limpiar cache que coincida con el patrón',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Probar rendimiento de cache vs sin cache',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("🚀 ADMINISTRADOR DE REDIS CACHE"))
        self.stdout.write("=" * 70)
        self.stdout.write()

        if options['stats']:
            self._show_stats()
        
        elif options['warm_up']:
            self._warm_up_cache()
        
        elif options['clear']:
            self._clear_all_cache()
        
        elif options['clear_pattern']:
            self._clear_pattern(options['clear_pattern'])
        
        elif options['test']:
            self._test_performance()
        
        else:
            self._show_help()

    def _show_stats(self):
        """Mostrar estadísticas de Redis"""
        self.stdout.write(self.style.HTTP_INFO("📊 ESTADÍSTICAS DE REDIS CACHE"))
        self.stdout.write("-" * 70)
        
        stats = CacheUtils.get_cache_stats()
        
        if stats and 'error' not in stats:
            self.stdout.write(f"🔗 Clientes conectados: {stats.get('connected_clients', 'N/A')}")
            self.stdout.write(f"💾 Memoria usada: {stats.get('used_memory_human', 'N/A')}")
            self.stdout.write(f"⚡ Comandos procesados: {stats.get('total_commands_processed', 'N/A')}")
            if isinstance(stats.get('total_commands_processed'), int):
                self.stdout.write(f"⚡ Comandos procesados: {stats.get('total_commands_processed', 'N/A'):,}")
            else:
                self.stdout.write(f"⚡ Comandos procesados: {stats.get('total_commands_processed', 'N/A')}")
            self.stdout.write(f"📈 Tasa de aciertos: {stats.get('cache_hit_rate', 0):.1f}%")
            self.stdout.write(f"🎯 Cache hits: {stats.get('keyspace_hits', 'N/A')}")
            self.stdout.write(f"❌ Cache misses: {stats.get('keyspace_misses', 'N/A')}")
            if isinstance(stats.get('keys_count'), int):
                self.stdout.write(f"🗝️  Total de claves: {stats.get('keys_count', 'N/A'):,}")
            else:
                self.stdout.write(f"🗝️  Total de claves: {stats.get('keys_count', 'N/A')}")
        else:
            error_msg = stats.get('error', 'Desconocido') if stats else 'No se pudieron obtener estadísticas'
            self.stdout.write(self.style.WARNING(f"⚠️  Estadísticas Redis no disponibles: {error_msg}"))
            self.stdout.write(self.style.HTTP_INFO("ℹ️  Posiblemente usando cache local (LocMemCache)"))
            
            # Mostrar tipo de cache actual
            from django.core.cache import cache
            backend_type = type(cache._cache).__name__ if hasattr(cache, '_cache') else type(cache).__name__
            self.stdout.write(f"📦 Backend actual: {backend_type}")
        
        # Probar conexión
        try:
            cache.set('test_connection', 'OK', 10)
            result = cache.get('test_connection')
            if result == 'OK':
                self.stdout.write(self.style.SUCCESS("✅ Conexión Redis: OK"))
                cache.delete('test_connection')
            else:
                self.stdout.write(self.style.ERROR("❌ Conexión Redis: FALLO"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error de conexión: {e}"))

    def _warm_up_cache(self):
        """Precalentar cache"""
        self.stdout.write(self.style.HTTP_INFO("🔥 PRECALENTANDO CACHE..."))
        self.stdout.write("-" * 70)
        
        start_time = time.time()
        
        try:
            CacheUtils.warm_up_cache()
            
            elapsed = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f"✅ Cache precalentado en {elapsed:.2f}s"))
            
            # Mostrar qué se cacheó
            self._show_cached_keys_sample()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error precalentando cache: {e}"))

    def _clear_all_cache(self):
        """Limpiar todo el cache"""
        self.stdout.write(self.style.WARNING("⚠️  LIMPIANDO TODO EL CACHE..."))
        self.stdout.write("-" * 70)
        
        try:
            success = CacheUtils.clear_all_cache()
            if success:
                self.stdout.write(self.style.SUCCESS("✅ Todo el cache ha sido limpiado"))
            else:
                self.stdout.write(self.style.ERROR("❌ Error limpiando cache"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def _clear_pattern(self, pattern):
        """Limpiar cache por patrón"""
        self.stdout.write(self.style.WARNING(f"🗑️  LIMPIANDO CACHE: {pattern}"))
        self.stdout.write("-" * 70)
        
        try:
            success = cache_service.clear_pattern(pattern)
            if success:
                self.stdout.write(self.style.SUCCESS(f"✅ Cache limpiado para patrón: {pattern}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error limpiando patrón: {pattern}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

    def _test_performance(self):
        """Probar rendimiento con/sin cache"""
        self.stdout.write(self.style.HTTP_INFO("⚡ PRUEBA DE RENDIMIENTO"))
        self.stdout.write("-" * 70)
        
        from gastos.models import Gastos
        from app.services.balance_service import BalanceAnalysisService
        
        service = BalanceAnalysisService()
        filters = {'fecha__year': 2025}
        
        # Limpiar cache específico para la prueba
        cache_service.clear_pattern('*balances_gastos*')
        
        # Prueba 1: Sin cache (primera vez)
        start_time = time.time()
        result1 = service.get_balances_by_period(filters)
        time_without_cache = time.time() - start_time
        count1 = len(result1) if hasattr(result1, '__len__') else 0
        
        # Prueba 2: Con cache (segunda vez)
        start_time = time.time()
        result2 = service.get_balances_by_period(filters)
        time_with_cache = time.time() - start_time
        count2 = len(result2) if hasattr(result2, '__len__') else 0
        
        # Resultados
        self.stdout.write(f"📊 Registros procesados: {count1}")
        self.stdout.write(f"⏱️  Sin cache: {time_without_cache:.3f}s")
        self.stdout.write(f"🚀 Con cache: {time_with_cache:.3f}s")
        
        if time_without_cache > 0 and time_with_cache > 0:
            improvement = ((time_without_cache - time_with_cache) / time_without_cache) * 100
            speedup = time_without_cache / time_with_cache if time_with_cache > 0 else float('inf')
            
            self.stdout.write()
            self.stdout.write(self.style.SUCCESS(f"📈 Mejora: {improvement:.1f}%"))
            self.stdout.write(self.style.SUCCESS(f"⚡ Aceleración: {speedup:.1f}x más rápido"))
            
            if improvement > 50:
                self.stdout.write(self.style.SUCCESS("🎉 ¡Excelente mejora de rendimiento!"))
            elif improvement > 20:
                self.stdout.write(self.style.WARNING("👍 Buena mejora de rendimiento"))
            else:
                self.stdout.write(self.style.ERROR("⚠️  Mejora mínima - verificar configuración"))

    def _show_cached_keys_sample(self):
        """Mostrar muestra de claves cacheadas"""
        try:
            # Intentar obtener cliente Redis
            redis_client = None
            
            if hasattr(cache, '_cache'):
                redis_client = cache._cache.get_client()
            elif hasattr(cache, 'get_client'):
                redis_client = cache.get_client()
            elif hasattr(cache, '_get_client'):
                redis_client = cache._get_client()
                
            if redis_client:
                keys = redis_client.keys('agricola:*')[:10]  # Primeras 10 claves
                if keys:
                    self.stdout.write()
                    self.stdout.write("🔑 Muestra de claves cacheadas:")
                    for key in keys:
                        key_str = key.decode() if isinstance(key, bytes) else str(key)
                        ttl = redis_client.ttl(key)
                        self.stdout.write(f"  • {key_str} (TTL: {ttl}s)")
                else:
                    self.stdout.write("ℹ️  No hay claves con prefijo 'agricola:' en cache")
            else:
                self.stdout.write("⚠️  No se pudo obtener cliente Redis para mostrar claves")
        except Exception as e:
            self.stdout.write(f"⚠️  No se pudo mostrar claves: {e}")

    def _show_help(self):
        """Mostrar ayuda de uso"""
        self.stdout.write(self.style.HTTP_INFO("📋 USO DEL COMANDO"))
        self.stdout.write("-" * 70)
        self.stdout.write("Opciones disponibles:")
        self.stdout.write()
        self.stdout.write("📊 --stats              Mostrar estadísticas de Redis")
        self.stdout.write("🔥 --warm-up            Precalentar cache con datos importantes")
        self.stdout.write("🗑️  --clear              Limpiar todo el cache")
        self.stdout.write("🎯 --clear-pattern X    Limpiar cache que coincida con patrón")
        self.stdout.write("⚡ --test               Probar rendimiento con/sin cache")
        self.stdout.write()
        self.stdout.write("Ejemplos:")
        self.stdout.write("  python manage.py cache_admin --stats")
        self.stdout.write("  python manage.py cache_admin --clear-pattern 'balances*'")
        self.stdout.write("  python manage.py cache_admin --warm-up")