"""
Comando simple para probar cache sin dependencias complejas
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
import time


class Command(BaseCommand):
    help = 'Prueba simple de cache'

    def handle(self, *args, **options):
        self.stdout.write("🔧 PRUEBA SIMPLE DE CACHE")
        self.stdout.write("=" * 50)
        
        # Probar conexión básica
        try:
            cache.set('test_key', 'test_value', 30)
            result = cache.get('test_key')
            
            if result == 'test_value':
                self.stdout.write(self.style.SUCCESS("✅ Cache funcionando correctamente"))
                
                # Identificar tipo de backend
                backend = str(type(cache._cache).__name__) if hasattr(cache, '_cache') else str(type(cache).__name__)
                self.stdout.write(f"📦 Backend: {backend}")
                
                # Prueba de rendimiento básica
                start_time = time.time()
                for i in range(100):
                    cache.set(f'test_{i}', f'value_{i}', 60)
                set_time = time.time() - start_time
                
                start_time = time.time()
                for i in range(100):
                    cache.get(f'test_{i}')
                get_time = time.time() - start_time
                
                self.stdout.write(f"⚡ 100 operaciones SET: {set_time:.3f}s")
                self.stdout.write(f"⚡ 100 operaciones GET: {get_time:.3f}s")
                
                # Limpiar claves de prueba
                for i in range(100):
                    cache.delete(f'test_{i}')
                cache.delete('test_key')
                
                self.stdout.write(self.style.SUCCESS("🎉 Cache listo para usar"))
                
            else:
                self.stdout.write(self.style.ERROR("❌ Cache no está funcionando"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error de cache: {e}"))
            self.stdout.write(self.style.WARNING("⚠️  Usando cache local (sin Redis)"))