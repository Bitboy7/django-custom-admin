"""Serve user-uploaded media when Django is exposed directly."""
import mimetypes
import os

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils.deprecation import MiddlewareMixin


class MediaServeMiddleware(MiddlewareMixin):
    """Small, guarded media server for deployments that bypass Nginx."""

    def process_request(self, request):
        if settings.DEBUG or not request.path.startswith(settings.MEDIA_URL):
            return None

        relative_path = request.path[len(settings.MEDIA_URL):]
        if ".." in relative_path.split("/") or ".." in relative_path.split("\\"):
            raise Http404("Ruta no permitida")

        file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        real_media_root = os.path.realpath(settings.MEDIA_ROOT)
        real_file_path = os.path.realpath(file_path)

        if not real_file_path.startswith(real_media_root + os.sep):
            raise Http404("Acceso denegado")

        if not os.path.isfile(real_file_path):
            raise Http404("Archivo no encontrado")

        content_type, _ = mimetypes.guess_type(real_file_path)
        response = FileResponse(
            open(real_file_path, "rb"),
            content_type=content_type or "application/octet-stream",
        )
        response["Cache-Control"] = "private, max-age=604800"
        response["X-Content-Type-Options"] = "nosniff"
        return response
