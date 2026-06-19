"""
Middleware para cache automático de vistas
"""

from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
import time
import logging

logger = logging.getLogger(__name__)


class CacheMiddleware(MiddlewareMixin):
    """
    Middleware para cache automático de respuestas de vistas
    Cache páginas completas para usuarios específicos
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Configuración de cache por vista
        self.cache_settings = {
            '/balances/': 600,          # 10 minutos para balances
            '/compras-balances/': 600,  # 10 minutos para compras
            '/ventas-balances/': 600,   # 10 minutos para ventas
            '/admin/': 300,             # 5 minutos para admin
        }
        super().__init__(get_response)
    
    def process_request(self, request):
        """Verificar si hay respuesta cacheada antes de procesar vista"""
        # Solo cachear para usuarios autenticados
        if not request.user.is_authenticated:
            return None
        
        # Solo cachear GET requests
        if request.method != 'GET':
            return None
        
        # Verificar si la URL debe ser cacheada
        cache_timeout = self._get_cache_timeout(request.path)
        if not cache_timeout:
            return None
        
        # Generar clave de cache única por usuario y parámetros
        cache_key = self._generate_cache_key(request)
        
        # Intentar obtener respuesta del cache
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug(f"Cache hit para: {request.path}")
            # Agregar header para identificar respuesta cacheada
            cached_response['X-Cache'] = 'HIT'
            return cached_response
        
        # Marcar que se debe cachear esta request
        request._cache_key = cache_key
        request._cache_timeout = cache_timeout
        return None
    
    def process_response(self, request, response):
        """Cachear respuesta si es necesario"""
        # Solo cachear si se marcó en process_request
        if not hasattr(request, '_cache_key'):
            return response
        
        # Solo cachear respuestas exitosas
        if response.status_code != 200:
            return response
        
        # Solo cachear HTML (no AJAX, JSON, etc.)
        content_type = response.get('Content-Type', '')
        if 'text/html' not in content_type:
            return response
        
        try:
            # Cachear la respuesta
            cache.set(request._cache_key, response, request._cache_timeout)
            logger.debug(f"Cache set para: {request.path} (timeout: {request._cache_timeout}s)")
            
            # Agregar header para identificar respuesta no cacheada
            response['X-Cache'] = 'MISS'
            
        except Exception as e:
            logger.error(f"Error cacheando respuesta: {e}")
        
        return response
    
    def _get_cache_timeout(self, path):
        """Obtiene el timeout de cache para una URL específica"""
        for url_pattern, timeout in self.cache_settings.items():
            if path.startswith(url_pattern):
                return timeout
        return None
    
    def _generate_cache_key(self, request):
        """Genera clave de cache única"""
        # Incluir usuario, path, y parámetros GET
        key_parts = [
            'page_cache',
            str(request.user.id),
            request.path,
            request.GET.urlencode()
        ]
        
        return ':'.join(filter(None, key_parts))


class DatabaseCacheInvalidationMiddleware(MiddlewareMixin):
    """
    Middleware para invalidar cache automáticamente cuando se detectan cambios en BD
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Marcar timestamp de inicio de request"""
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Invalidar cache si hubo escritura a BD en request POST"""
        # Solo procesar requests que modifican datos
        if request.method not in ['POST', 'PUT', 'DELETE', 'PATCH']:
            return response
        
        # Verificar si fue una operación exitosa
        if response.status_code not in [200, 201, 204, 302]:
            return response
        
        # Invalidar caches relacionados basado en la URL
        self._invalidate_related_caches(request)
        
        return response
    
    def _invalidate_related_caches(self, request):
        """Invalida caches basado en la URL de la operación"""
        try:
            # Importación diferida para evitar importación circular
            from app.services.cache_service import cache_service
            
            path = request.path
            
            # Admin de gastos
            if '/admin/gastos/gastos/' in path:
                cache_service.invalidate_related_caches('gastos')
                cache_service.clear_pattern('page_cache:*:balances*')
            
            # Admin de compras
            elif '/admin/gastos/compra/' in path:
                cache_service.invalidate_related_caches('compra')
                cache_service.clear_pattern('page_cache:*:compras*')
            
            # Admin de ventas
            elif '/admin/ventas/ventas/' in path:
                cache_service.invalidate_related_caches('ventas')
                cache_service.clear_pattern('page_cache:*:ventas*')
            
            # Catálogos
            elif any(model in path for model in ['/admin/catalogo/', '/admin/gastos/cuenta/']):
                cache_service.invalidate_related_caches('catalogos')
                cache_service.clear_pattern('page_cache:*')
            
            logger.info(f"Cache invalidado para operación: {path}")
            
        except ImportError:
            logger.warning("Cache service no disponible - saltando invalidación")
        except Exception as e:
            logger.error(f"Error invalidando cache: {e}")


class QueryCountDebugMiddleware(MiddlewareMixin):
    """
    Middleware para debug - cuenta queries de BD por request
    Solo activo en DEBUG mode
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        from django.conf import settings
        if settings.DEBUG:
            from django.db import reset_queries
            reset_queries()
            request._start_time = time.time()
    
    def process_response(self, request, response):
        from django.conf import settings
        if settings.DEBUG and hasattr(request, '_start_time'):
            from django.db import connection
            
            total_time = time.time() - request._start_time
            query_count = len(connection.queries)
            
            if query_count > 10:  # Solo logear si hay muchas queries
                logger.warning(
                    f"🐌 Slow request: {request.path} - "
                    f"{query_count} queries in {total_time:.2f}s"
                )
            
            # Agregar header para debug
            response['X-DB-Queries'] = str(query_count)
            response['X-Response-Time'] = f"{total_time:.3f}s"
        
        return response