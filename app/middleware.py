"""
Middleware para servir archivos media en producción cuando DEBUG=False
"""
import os
import mimetypes
from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils.deprecation import MiddlewareMixin


class MediaServeMiddleware(MiddlewareMixin):
    """
    Middleware que sirve archivos media en producción
    Similar a django.views.static.serve pero como middleware
    """
    
    def process_request(self, request):
        # Solo actuar si DEBUG=False y la URL es para archivos media
        if not settings.DEBUG and request.path.startswith(settings.MEDIA_URL):
            # Obtener la ruta del archivo
            relative_path = request.path[len(settings.MEDIA_URL):]
            file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            
            # Verificar que el archivo existe y está dentro de MEDIA_ROOT
            if os.path.exists(file_path) and os.path.commonpath([settings.MEDIA_ROOT, file_path]) == settings.MEDIA_ROOT:
                try:
                    # Determinar el tipo de contenido
                    content_type, encoding = mimetypes.guess_type(file_path)
                    if content_type is None:
                        content_type = 'application/octet-stream'
                    
                    # Leer y devolver el archivo
                    with open(file_path, 'rb') as f:
                        response = HttpResponse(f.read(), content_type=content_type)
                        
                    # Agregar headers de cache para mejorar performance
                    response['Cache-Control'] = 'public, max-age=3600'  # Cache por 1 hora
                    return response
                    
                except (IOError, OSError):
                    # Error al leer el archivo
                    raise Http404("Archivo no encontrado")
            else:
                # Archivo no existe
                raise Http404("Archivo no encontrado")
        
        # No es una petición de media o DEBUG=True, continuar normalmente
        return None
