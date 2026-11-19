"""
Middleware para registrar actividad en el admin
"""
import logging
from django.urls import Resolver404, resolve
from .request_context import reset_audit_actor, set_audit_actor
from .services import registrar_creacion, registrar_actualizacion, registrar_visualizacion

logger = logging.getLogger('auditoria.middleware')

_SENSITIVE_FIELDS = frozenset([
    'password', 'password1', 'password2', 'old_password', 'new_password',
    'confirm_password', 'secret_key', 'token', 'api_key', 'clave', 'pin',
])


def _sanitize_post_data(post_dict):
    """Redacta campos sensibles antes de registrarlos en auditoría."""
    sanitized = {}
    for key, value in post_dict.items():
        if key.startswith('_') or key == 'csrfmiddlewaretoken':
            continue
        if any(sensitive in key.lower() for sensitive in _SENSITIVE_FIELDS):
            sanitized[key] = '***REDACTED***'
        else:
            sanitized[key] = str(value[0] if isinstance(value, list) else value)[:200] if value else value
    return sanitized


class AdminAuditMiddleware:
    """
    Middleware para registrar actividad en el admin de Django.
    Registra creaciones, actualizaciones, eliminaciones y visualizaciones de objetos.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        token = set_audit_actor(
            usuario if getattr(usuario, 'is_authenticated', False) else None
        )
        try:
            response = self.get_response(request)
        finally:
            reset_audit_actor(token)

        if not getattr(usuario, 'is_authenticated', False):
            return response

        try:
            resolver_match = resolve(request.path_info)
            es_admin = (
                resolver_match.app_name == 'admin'
                or 'admin' in resolver_match.namespaces
            )
            if not es_admin or not resolver_match.url_name:
                return response

            url_name = resolver_match.url_name
            kwargs = resolver_match.kwargs or {}
            app_label = kwargs.get('app_label')
            model_name = kwargs.get('model_name')
            if not model_name:
                partes = (url_name or '').split('_')
                if len(partes) >= 3:
                    app_label = app_label or partes[0]
                    model_name = '_'.join(partes[1:-1])
            if app_label and model_name:
                model_name = f'{app_label}.{model_name}'
            object_id = kwargs.get('object_id')
            es_pago_venta = (model_name or '').lower().endswith('pagoventa')

            if (
                url_name.endswith('_add')
                and request.method == 'POST'
                and response.status_code in (302, 303)
                and model_name
                and not es_pago_venta
            ):
                registrar_creacion(
                    request=request,
                    modelo=model_name,
                    objeto={'pk': 'nuevo'},
                )
            elif (
                url_name.endswith('_change')
                and request.method == 'POST'
                and response.status_code in (302, 303)
                and model_name
                and object_id
                and not es_pago_venta
            ):
                registrar_actualizacion(
                    request=request,
                    modelo=model_name,
                    objeto={'pk': object_id},
                    campos_modificados=_sanitize_post_data(dict(request.POST)),
                )
            elif url_name.endswith('_change') and request.method == 'GET':
                if model_name and object_id:
                    registrar_visualizacion(
                        request=request,
                        modelo=model_name,
                        objeto={'pk': object_id},
                    )
        except Resolver404:
            # Las rutas inexistentes (404) no son actividad del admin que
            # deba reportarse como error operativo de auditoría.
            pass
        except Exception:
            logger.error(
                'Error en AdminAuditMiddleware | Usuario: %s | Path: %s',
                getattr(usuario, 'username', 'anónimo'),
                request.path,
                exc_info=True,
            )

        return response
