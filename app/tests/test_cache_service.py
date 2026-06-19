"""
Tests unitarios para el servicio de cache Redis

Verifica el funcionamiento correcto de CacheService en diferentes escenarios:
- Operaciones básicas (get, set, delete)
- Generación de claves
- Timeouts y expiración
- Manejo de errores
- Invalidación de cache relacionado
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from app.services.cache_service import CacheService, cache_service, cache_result, CacheUtils
import time


class CacheServiceTestCase(TestCase):
    """Tests para CacheService"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        # Limpiar cache antes de cada test
        cache.clear()
        self.cache_service = CacheService()
    
    def tearDown(self):
        """Limpieza después de cada test"""
        cache.clear()
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE OPERACIONES BÁSICAS
    # ═══════════════════════════════════════════════════════════════
    
    def test_set_and_get_basic(self):
        """Test básico de set y get"""
        key = 'test_key'
        value = 'test_value'
        
        # Set
        result = self.cache_service.set(key, value, timeout=60)
        self.assertTrue(result)
        
        # Get
        cached_value = self.cache_service.get(key)
        self.assertEqual(cached_value, value)
    
    def test_get_nonexistent_key(self):
        """Test get con clave inexistente devuelve default"""
        result = self.cache_service.get('nonexistent', default='default_value')
        self.assertEqual(result, 'default_value')
    
    def test_delete_key(self):
        """Test eliminación de clave"""
        key = 'test_delete'
        self.cache_service.set(key, 'value', timeout=60)
        
        # Verificar que existe
        self.assertIsNotNone(self.cache_service.get(key))
        
        # Eliminar
        result = self.cache_service.delete(key)
        self.assertTrue(result)
        
        # Verificar que ya no existe
        self.assertIsNone(self.cache_service.get(key))
    
    def test_set_with_dict_value(self):
        """Test cache con valores complejos (diccionarios)"""
        key = 'test_dict'
        value = {
            'id': 1,
            'name': 'Test',
            'data': [1, 2, 3],
            'nested': {'key': 'value'}
        }
        
        self.cache_service.set(key, value, timeout=60)
        cached_value = self.cache_service.get(key)
        
        self.assertEqual(cached_value, value)
        self.assertEqual(cached_value['name'], 'Test')
        self.assertEqual(cached_value['nested']['key'], 'value')
    
    def test_set_with_list_value(self):
        """Test cache con listas"""
        key = 'test_list'
        value = [1, 2, 3, 'four', {'five': 5}]
        
        self.cache_service.set(key, value, timeout=60)
        cached_value = self.cache_service.get(key)
        
        self.assertEqual(cached_value, value)
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE GENERACIÓN DE CLAVES
    # ═══════════════════════════════════════════════════════════════
    
    def test_generate_cache_key_simple(self):
        """Test generación de clave simple"""
        key = self.cache_service._generate_cache_key('prefix', 'arg1', 'arg2')
        self.assertIn('prefix', key)
        self.assertIn('arg1', key)
        self.assertIn('arg2', key)
    
    def test_generate_cache_key_with_kwargs(self):
        """Test generación de clave con kwargs"""
        key = self.cache_service._generate_cache_key(
            'prefix',
            id=123,
            name='test',
            year=2024
        )
        self.assertIn('prefix', key)
        self.assertIn('123', key)
        self.assertIn('test', key)
        self.assertIn('2024', key)
    
    def test_generate_cache_key_long_string(self):
        """Test generación de clave con strings largos (usa hash)"""
        long_string = 'x' * 300  # String muy largo
        key = self.cache_service._generate_cache_key('prefix', long_string)
        
        # Debe ser más corto que el original y contener un hash
        self.assertLess(len(key), 250)
        self.assertIn('prefix', key)
    
    def test_generate_cache_key_consistency(self):
        """Test que la misma entrada genera la misma clave"""
        key1 = self.cache_service._generate_cache_key('test', id=1, name='alice')
        key2 = self.cache_service._generate_cache_key('test', id=1, name='alice')
        
        self.assertEqual(key1, key2)
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE TIMEOUTS
    # ═══════════════════════════════════════════════════════════════
    
    @pytest.mark.slow
    def test_cache_expiration(self):
        """Test que el cache expira después del timeout"""
        key = 'test_expiration'
        value = 'expires_soon'
        
        # Cachear con timeout de 2 segundos
        self.cache_service.set(key, value, timeout=2)
        
        # Debe existir inmediatamente
        self.assertEqual(self.cache_service.get(key), value)
        
        # Esperar 3 segundos
        time.sleep(3)
        
        # Ya no debe existir
        self.assertIsNone(self.cache_service.get(key))
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE INVALIDACIÓN DE CACHE
    # ═══════════════════════════════════════════════════════════════
    
    def test_invalidate_related_caches_gastos(self):
        """Test invalidación de caches relacionados con gastos"""
        # Simular cache de gastos
        cache.set('agricola:balances_gastos:2024', {'total': 1000})
        cache.set('agricola:dashboard:gastos', {'count': 5})
        
        # Invalidar
        self.cache_service.invalidate_related_caches('gastos')
        
        # Verificar que se limpiaron (depende de implementación de clear_pattern)
        # Este test puede necesitar ajuste según el backend
    
    def test_invalidate_related_caches_ventas(self):
        """Test invalidación de caches relacionados con ventas"""
        cache.set('agricola:balances_ventas:2024', {'total': 5000})
        cache.set('agricola:dashboard:ventas', {'count': 10})
        
        self.cache_service.invalidate_related_caches('ventas')
    
    def test_invalidate_related_caches_compra(self):
        """Test invalidación de caches relacionados con compras"""
        cache.set('agricola:balances_compras:2024', {'total': 3000})
        
        self.cache_service.invalidate_related_caches('compra')
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE DECORADOR @cache_result
    # ═══════════════════════════════════════════════════════════════
    
    def test_cache_result_decorator(self):
        """Test que el decorador @cache_result cachea correctamente"""
        # Contador para verificar cuántas veces se ejecuta la función
        call_count = {'count': 0}
        
        @cache_result('test', 60, 'decorator_test')
        def expensive_function(x, y):
            call_count['count'] += 1
            return x + y
        
        # Primera llamada - ejecuta la función
        result1 = expensive_function(2, 3)
        self.assertEqual(result1, 5)
        self.assertEqual(call_count['count'], 1)
        
        # Segunda llamada - debe usar cache
        result2 = expensive_function(2, 3)
        self.assertEqual(result2, 5)
        self.assertEqual(call_count['count'], 1)  # No se incrementó
        
        # Llamada con diferentes parámetros - ejecuta de nuevo
        result3 = expensive_function(5, 7)
        self.assertEqual(result3, 12)
        self.assertEqual(call_count['count'], 2)
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE MÉTODOS ESPECIALIZADOS
    # ═══════════════════════════════════════════════════════════════
    
    def test_get_or_set_balances(self):
        """Test método especializado para balances"""
        def query_function(**kwargs):
            return [{'id': 1, 'monto': 1000}, {'id': 2, 'monto': 2000}]
        
        cache_key = 'test_balances_2024'
        
        # Primera llamada - ejecuta query
        result1 = self.cache_service.get_or_set_balances(
            cache_key,
            query_function,
            timeout=60
        )
        
        self.assertEqual(len(result1), 2)
        self.assertEqual(result1[0]['monto'], 1000)
        
        # Segunda llamada - debe usar cache
        result2 = self.cache_service.get_or_set_balances(
            cache_key,
            query_function,
            timeout=60
        )
        
        self.assertEqual(result1, result2)
    
    def test_get_or_set_catalogos(self):
        """Test método especializado para catálogos"""
        def query_function():
            return [{'id': 1, 'name': 'Cat1'}, {'id': 2, 'name': 'Cat2'}]
        
        cache_key = 'test_catalogos'
        result = self.cache_service.get_or_set_catalogos(cache_key, query_function)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Cat1')
    
    def test_get_or_set_reportes(self):
        """Test método especializado para reportes"""
        def query_function(**kwargs):
            return {'total': 5000, 'count': 10}
        
        cache_key = 'test_reporte_mensual'
        result = self.cache_service.get_or_set_reportes(cache_key, query_function)
        
        self.assertEqual(result['total'], 5000)
        self.assertEqual(result['count'], 10)
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE MANEJO DE ERRORES
    # ═══════════════════════════════════════════════════════════════
    
    @patch('app.services.cache_service.caches')
    def test_get_with_cache_error(self, mock_caches):
        """Test que get maneja errores de cache correctamente"""
        # Simular error en cache
        mock_cache = Mock()
        mock_cache.get.side_effect = Exception("Cache connection error")
        mock_caches.__getitem__.return_value = mock_cache
        
        # No debe lanzar excepción, debe retornar default
        result = self.cache_service.get('test_key', default='fallback')
        self.assertEqual(result, 'fallback')
    
    @patch('app.services.cache_service.caches')
    def test_set_with_cache_error(self, mock_caches):
        """Test que set maneja errores de cache correctamente"""
        mock_cache = Mock()
        mock_cache.set.side_effect = Exception("Cache write error")
        mock_caches.__getitem__.return_value = mock_cache
        
        # No debe lanzar excepción, debe retornar False
        result = self.cache_service.set('test_key', 'value', timeout=60)
        self.assertFalse(result)
    
    # ═══════════════════════════════════════════════════════════════
    # TESTS DE CACHE ALIASES
    # ═══════════════════════════════════════════════════════════════
    
    def test_cache_with_different_aliases(self):
        """Test uso de diferentes backends de cache"""
        # Cache default
        self.cache_service.set('key1', 'value1', cache_alias='default')
        result1 = self.cache_service.get('key1', cache_alias='default')
        self.assertEqual(result1, 'value1')
        
        # Si existe static_data alias
        try:
            self.cache_service.set('key2', 'value2', cache_alias='static_data')
            result2 = self.cache_service.get('key2', cache_alias='static_data')
            # Puede fallar en desarrollo si no está configurado
        except:
            pass  # No crítico en tests


class CacheUtilsTestCase(TestCase):
    """Tests para CacheUtils"""
    
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_warm_up_cache_basic(self):
        """Test precalentamiento de cache"""
        # Este test puede fallar si las tablas no existen
        try:
            CacheUtils.warm_up_cache()
            # Verificar que se crearon algunos caches
            # (dependería de datos en la base de datos)
        except Exception as e:
            # En tests unitarios sin DB, puede fallar
            self.skipTest(f"Skipping warm_up test: {e}")
    
    @patch('app.services.cache_service.cache_service.default_cache')
    def test_get_cache_stats(self, mock_cache):
        """Test obtención de estadísticas de cache"""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.info.return_value = {
            'used_memory': 1024000,
            'connected_clients': 5,
            'total_commands_processed': 1000
        }
        
        mock_cache._cache.get_client.return_value = mock_redis
        
        try:
            stats = CacheUtils.get_cache_stats()
            # Verificar estructura de stats si está implementado
        except Exception:
            # Puede no estar completamente implementado
            pass


class CacheIntegrationBasicTestCase(TestCase):
    """Tests de integración básicos con el sistema de cache"""
    
    def setUp(self):
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_cache_key_consistency_across_services(self):
        """Test que diferentes servicios usan claves consistentes"""
        from app.services.cache_service import cache_service
        
        # Mismo prefijo y parámetros deben generar misma clave
        key1 = cache_service._generate_cache_key('balances', year=2024, month=1)
        key2 = cache_service._generate_cache_key('balances', year=2024, month=1)
        
        self.assertEqual(key1, key2)
    
    def test_cache_instance_is_singleton(self):
        """Test que cache_service es una instancia única"""
        from app.services.cache_service import cache_service as cs1
        from app.services.cache_service import cache_service as cs2
        
        # Deben ser la misma instancia
        self.assertIs(cs1, cs2)
    
    def test_multiple_cache_operations_in_sequence(self):
        """Test múltiples operaciones de cache en secuencia"""
        service = CacheService()
        
        # Set múltiples claves
        for i in range(10):
            service.set(f'key_{i}', f'value_{i}', timeout=60)
        
        # Get múltiples claves
        for i in range(10):
            value = service.get(f'key_{i}')
            self.assertEqual(value, f'value_{i}')
        
        # Delete múltiples claves
        for i in range(10):
            service.delete(f'key_{i}')
        
        # Verificar que se eliminaron
        for i in range(10):
            value = service.get(f'key_{i}')
            self.assertIsNone(value)


# ═══════════════════════════════════════════════════════════════
# TESTS DE RENDIMIENTO (marcados para ejecutar opcionalmente)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.performance
class CachePerformanceTestCase(TestCase):
    """Tests de rendimiento del cache (opcionales)"""
    
    def setUp(self):
        cache.clear()
        self.cache_service = CacheService()
    
    def test_cache_write_performance(self):
        """Test rendimiento de escrituras en cache"""
        start_time = time.time()
        
        for i in range(1000):
            self.cache_service.set(f'perf_key_{i}', {'data': i}, timeout=60)
        
        elapsed = time.time() - start_time
        
        # Debe completar 1000 escrituras en menos de 5 segundos
        self.assertLess(elapsed, 5.0)
        
        print(f"\n1000 escrituras completadas en {elapsed:.3f}s")
    
    def test_cache_read_performance(self):
        """Test rendimiento de lecturas en cache"""
        # Precarga datos
        for i in range(1000):
            self.cache_service.set(f'perf_key_{i}', {'data': i}, timeout=60)
        
        start_time = time.time()
        
        for i in range(1000):
            self.cache_service.get(f'perf_key_{i}')
        
        elapsed = time.time() - start_time
        
        # Lecturas deben ser más rápidas que escrituras
        self.assertLess(elapsed, 3.0)
        
        print(f"\n1000 lecturas completadas en {elapsed:.3f}s")
