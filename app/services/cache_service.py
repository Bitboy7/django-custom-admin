"""
Servicio central de cache para la aplicación Django
Maneja todas las operaciones de cache Redis con patrones optimizados
"""

from django.core.cache import caches, cache
from django.conf import settings
from django.utils import timezone
from django.db.models import QuerySet
import hashlib
import json
import logging
from functools import wraps
from typing import Any, Optional, Union, List, Dict
import time

logger = logging.getLogger(__name__)

class CacheService:
    """Servicio centralizado de cache con Redis"""
    
    def __init__(self):
        self.default_cache = cache
        self.static_cache = caches['static_data'] if 'static_data' in caches else cache
        self.timeouts = getattr(settings, 'CACHE_TIMEOUTS', {})
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Genera una clave de cache única y consistente"""
        # Crear string único basado en argumentos
        key_parts = [prefix]
        key_parts.extend([str(arg) for arg in args])
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        
        key_string = "|".join(key_parts)
        
        # Usar hash para keys muy largos
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        # Limpiar caracteres problemáticos
        return key_string.replace(" ", "_").replace(":", "-")
    
    def get(self, key: str, default=None, cache_alias='default') -> Any:
        """Obtiene un valor del cache"""
        try:
            cache_instance = caches[cache_alias] if cache_alias != 'default' else self.default_cache
            return cache_instance.get(key, default)
        except Exception as e:
            logger.error(f"Error al obtener cache {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, cache_alias='default') -> bool:
        """Establece un valor en cache"""
        try:
            cache_instance = caches[cache_alias] if cache_alias != 'default' else self.default_cache
            if timeout is None:
                timeout = 300  # 5 minutos por defecto
            cache_instance.set(key, value, timeout)
            logger.debug(f"Cache set: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Error al establecer cache {key}: {e}")
            return False
    
    def delete(self, key: str, cache_alias='default') -> bool:
        """Elimina una clave del cache"""
        try:
            cache_instance = caches[cache_alias] if cache_alias != 'default' else self.default_cache
            cache_instance.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar cache {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str, cache_alias='default') -> bool:
        """Elimina todas las claves que coinciden con un patrón"""
        try:
            cache_instance = caches[cache_alias] if cache_alias != 'default' else self.default_cache
            if hasattr(cache_instance, 'delete_pattern'):
                cache_instance.delete_pattern(pattern)
                logger.info(f"Cache pattern cleared: {pattern}")
                return True
            else:
                # Fallback para backends que no soportan delete_pattern
                logger.warning(f"Cache backend no soporta delete_pattern para: {pattern}")
                return False
        except Exception as e:
            logger.error(f"Error al limpiar patrón cache {pattern}: {e}")
            return False
    
    def get_or_set_balances(self, cache_key: str, query_function, timeout: Optional[int] = None, **query_kwargs) -> Any:
        """Obtiene balances del cache o ejecuta la consulta"""
        if timeout is None:
            timeout = self.timeouts.get('balances', 900)
        
        # Intentar obtener del cache
        cached_data = self.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache hit: {cache_key}")
            return cached_data
        
        # Ejecutar consulta y cachear
        logger.debug(f"Cache miss: {cache_key} - Ejecutando consulta")
        start_time = time.time()
        
        data = query_function(**query_kwargs)
        
        execution_time = time.time() - start_time
        logger.info(f"Consulta ejecutada en {execution_time:.2f}s: {cache_key}")
        
        # Serializar QuerySet a lista para cache
        if isinstance(data, QuerySet):
            data = list(data.values())
        
        self.set(cache_key, data, timeout)
        return data
    
    def get_or_set_catalogos(self, cache_key: str, query_function, **query_kwargs) -> Any:
        """Cache específico para datos de catálogo (productores, productos, etc.)"""
        timeout = self.timeouts.get('catalogos', 3600)
        return self.get_or_set_balances(cache_key, query_function, timeout, **query_kwargs)
    
    def get_or_set_reportes(self, cache_key: str, query_function, **query_kwargs) -> Any:
        """Cache específico para reportes complejos"""
        timeout = self.timeouts.get('reportes', 1800)
        return self.get_or_set_balances(cache_key, query_function, timeout, **query_kwargs)
    
    def invalidate_related_caches(self, model_name: str, action: str = 'update') -> None:
        """Invalida caches relacionados cuando se actualiza un modelo"""
        patterns_to_clear = []
        
        if model_name == 'gastos':
            patterns_to_clear = [
                'agricola:balances_gastos:*',
                'agricola:dashboard:*',
                'agricola:saldos:*'
            ]
        elif model_name == 'compra':
            patterns_to_clear = [
                'agricola:balances_compras:*',
                'agricola:compras:*',
                'agricola:dashboard:*'
            ]
        elif model_name == 'ventas':
            patterns_to_clear = [
                'agricola:balances_ventas:*',
                'agricola:ventas:*',
                'agricola:dashboard:*'
            ]
        elif model_name in ['productor', 'producto', 'sucursal', 'cuenta']:
            patterns_to_clear = [
                'agricola:catalogos:*',
                'agricola:balances:*'
            ]
        
        for pattern in patterns_to_clear:
            self.clear_pattern(pattern)
        
        logger.info(f"Invalidado cache para modelo: {model_name}")


# Instancia global del servicio de cache
cache_service = CacheService()


def cache_result(cache_type: str = 'default', timeout: Optional[int] = None, key_prefix: str = ''):
    """
    Decorador para cachear resultados de funciones
    
    Uso:
        @cache_result('balances', 900, 'gastos')
        def get_balances_gastos(**kwargs):
            return expensive_query()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de cache
            cache_key = cache_service._generate_cache_key(
                f"{key_prefix}:{func.__name__}" if key_prefix else func.__name__,
                *args, **kwargs
            )
            
            # Usar timeout específico o del tipo
            actual_timeout = timeout or cache_service.timeouts.get(cache_type, 300)
            
            # Obtener o establecer cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, actual_timeout)
            
            return result
        return wrapper
    return decorator


class CacheUtils:
    """Utilidades adicionales para cache"""
    
    @staticmethod
    def warm_up_cache():
        """Precalienta caches importantes"""
        from catalogo.models import Productor, Producto, Sucursal
        from gastos.models import Cuenta, CatGastos
        
        logger.info("Iniciando precalentamiento de cache...")
        
        # Cachear catálogos básicos
        cache_service.get_or_set_catalogos(
            'catalogos:productores:all',
            lambda: list(Productor.objects.select_related('id_sucursal', 'nacionalidad').values())
        )
        
        cache_service.get_or_set_catalogos(
            'catalogos:productos:all',
            lambda: list(Producto.objects.values())
        )
        
        cache_service.get_or_set_catalogos(
            'catalogos:sucursales:all',
            lambda: list(Sucursal.objects.select_related('id_estado').values())
        )
        
        logger.info("Precalentamiento de cache completado")
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Obtiene estadísticas de cache"""
        try:
            # Intentar obtener cliente Redis de diferentes formas
            redis_client = None
            
            # Método 1: django-redis
            if hasattr(cache_service.default_cache, '_cache'):
                redis_client = cache_service.default_cache._cache.get_client()
            
            # Método 2: conexión directa
            elif hasattr(cache_service.default_cache, 'get_client'):
                redis_client = cache_service.default_cache.get_client()
                
            # Método 3: backend interno
            elif hasattr(cache_service.default_cache, '_get_client'):
                redis_client = cache_service.default_cache._get_client()
            
            if redis_client is None:
                return {'error': 'No se pudo obtener cliente Redis'}
            
            info = redis_client.info()
            keyspace_hits = info.get('keyspace_hits', 0)
            keyspace_misses = info.get('keyspace_misses', 0)
            total_commands = keyspace_hits + keyspace_misses
            hit_rate = (keyspace_hits / max(total_commands, 1)) * 100
            
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'cache_hit_rate': hit_rate,
                'keys_count': redis_client.dbsize(),
                'keyspace_hits': keyspace_hits,
                'keyspace_misses': keyspace_misses
            }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de cache: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def clear_all_cache():
        """Limpia todo el cache (usar con cuidado)"""
        try:
            cache_service.default_cache.clear()
            if 'static_data' in caches:
                caches['static_data'].clear()
            logger.info("Todo el cache ha sido limpiado")
            return True
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")
            return False