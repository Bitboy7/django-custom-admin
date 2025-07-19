"""
Middleware para registrar actividad en el admin
"""
from django.urls import resolve
from .services import registrar_creacion, registrar_actualizacion, registrar_eliminacion, registrar_visualizacion


class AdminAuditMiddleware:
    """
    Middleware para registrar actividad en el admin de Django.
    Registra creaciones, actualizaciones, eliminaciones y visualizaciones de objetos.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Solo procesar si el usuario está autenticado
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Solo procesar solicitudes del admin
        if not request.path.startswith('/admin/'):
            return self.get_response(request)
        
        # Procesar la solicitud
        response = self.get_response(request)
        
        # Intentar resolver la URL para obtener información
        try:
            resolver_match = resolve(request.path)
            url_name = resolver_match.url_name
            view_name = resolver_match.view_name
            app_name = resolver_match.app_name
            namespace = resolver_match.namespace
            
            # Detectar acciones del admin
            if url_name:
                # Obtener el modelo y el ID del objeto si están disponibles
                model_name = None
                object_id = None
                
                # Extraer el modelo del view_name
                if view_name and '_' in view_name:
                    parts = view_name.split('_')
                    if len(parts) >= 2:
                        app_label = parts[0]
                        model_name = parts[1]
                
                # Extraer el ID del objeto de los argumentos de URL
                if resolver_match.kwargs:
                    object_id = resolver_match.kwargs.get('object_id')
                
                # Registrar la acción según el tipo de vista
                if url_name.endswith('_add') and request.method == 'POST' and response.status_code in (302, 303):
                    # Creación exitosa (redirección después de guardar)
                    if hasattr(request, 'POST') and model_name:
                        # Obtener el objeto creado (esto es aproximado, podría mejorar)
                        # En una implementación real habría que acceder al objeto desde la respuesta
                        registrar_creacion(
                            request=request,
                            modelo=model_name,
                            objeto={'pk': 'nuevo'}  # Placeholder
                        )
                
                elif url_name.endswith('_change') and request.method == 'POST' and response.status_code in (302, 303):
                    # Actualización exitosa (redirección después de guardar)
                    if hasattr(request, 'POST') and model_name and object_id:
                        # Obtener los campos modificados (simplificado)
                        campos_modificados = {k: v for k, v in request.POST.items() 
                                            if not k.startswith('_') and k != 'csrfmiddlewaretoken'}
                        
                        registrar_actualizacion(
                            request=request,
                            modelo=model_name,
                            objeto={'pk': object_id},
                            campos_modificados=campos_modificados
                        )
                
                elif url_name.endswith('_delete') and request.method == 'POST' and response.status_code in (302, 303):
                    # Eliminación exitosa (redirección después de eliminar)
                    if model_name and object_id:
                        registrar_eliminacion(
                            request=request,
                            modelo=model_name,
                            objeto_id=object_id
                        )
                
                elif url_name.endswith('_change') and request.method == 'GET':
                    # Visualización de detalle
                    if model_name and object_id:
                        registrar_visualizacion(
                            request=request,
                            modelo=model_name,
                            objeto={'pk': object_id}
                        )
        
        except Exception as e:
            # Silenciar errores para no afectar la funcionalidad principal
            pass
        
        return response
