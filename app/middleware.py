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
            # Rechazar rutas con componentes peligrosos antes de cualquier operación de FS
            relative_path = request.path[len(settings.MEDIA_URL):]
            if '..' in relative_path.split('/') or '..' in relative_path.split('\\'):
                raise Http404("Ruta no permitida")

            file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            # Resolver symlinks antes de comparar para prevenir path traversal
            real_media_root = os.path.realpath(settings.MEDIA_ROOT)
            real_file_path = os.path.realpath(file_path)

            # Verificar que el archivo resuelto permanece dentro de MEDIA_ROOT
            if not real_file_path.startswith(real_media_root + os.sep):
                raise Http404("Acceso denegado")

            if os.path.exists(real_file_path) and os.path.isfile(real_file_path):
                try:
                    # Determinar el tipo de contenido
                    content_type, _ = mimetypes.guess_type(real_file_path)
                    if content_type is None:
                        content_type = 'application/octet-stream'

                    # Leer y devolver el archivo
                    with open(real_file_path, 'rb') as f:
                        response = HttpResponse(f.read(), content_type=content_type)

                    # Cabeceras de seguridad: sin caché público, sin sniffing de tipo
                    response['Cache-Control'] = 'private, no-cache'
                    response['X-Content-Type-Options'] = 'nosniff'
                    return response

                except (IOError, OSError):
                    raise Http404("Archivo no encontrado")
            else:
                raise Http404("Archivo no encontrado")

        # No es una petición de media o DEBUG=True, continuar normalmente
        return None
