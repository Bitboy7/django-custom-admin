"""
Middleware para registrar actividad de autenticación
"""
from .services import registrar_login, registrar_logout


class AuthAuditMiddleware:
    """
    Middleware para registrar los inicios y cierres de sesión de usuarios.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Obtener el usuario antes de procesar la solicitud
        usuario_antes = request.user if hasattr(request, 'user') else None
        autenticado_antes = usuario_antes.is_authenticated if usuario_antes else False
        
        # Procesar la solicitud
        response = self.get_response(request)
        
        # Obtener el usuario después de procesar la solicitud
        usuario_despues = request.user if hasattr(request, 'user') else None
        autenticado_despues = usuario_despues.is_authenticated if usuario_despues else False
        
        # Verificar si el usuario inició sesión durante esta solicitud
        if not autenticado_antes and autenticado_despues:
            # Se ha iniciado sesión
            registrar_login(request, usuario_despues)
        
        # Verificar si el usuario cerró sesión durante esta solicitud
        # Esto se detecta principalmente en la URL de logout
        if request.path.endswith('/logout/') and autenticado_antes:
            # Se ha cerrado sesión
            registrar_logout(request, usuario_antes)
        
        return response
