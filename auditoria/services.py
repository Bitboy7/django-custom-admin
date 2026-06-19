"""
Servicio para gestionar los logs de actividad en el sistema.
"""
import ipaddress
from .models import LogActividad

# Rangos de red privada — solo desde estas IPs se confía en X-Forwarded-For
_TRUSTED_PROXY_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),  # Loopback (docker interno)
]


def _get_real_ip(request):
    """
    Obtiene la IP real del cliente de forma segura.
    Solo confía en X-Forwarded-For cuando REMOTE_ADDR pertenece a
    un proxy interno conocido, previniendo IP spoofing desde clientes externos.
    """
    remote_addr = request.META.get('REMOTE_ADDR', '')
    try:
        remote_ip = ipaddress.ip_address(remote_addr)
        is_trusted_proxy = any(remote_ip in net for net in _TRUSTED_PROXY_NETWORKS)
    except ValueError:
        return remote_addr

    if is_trusted_proxy:
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded_for:
            # Primera IP en la cadena = cliente original
            client_ip = forwarded_for.split(',')[0].strip()
            try:
                ipaddress.ip_address(client_ip)  # Validar formato
                return client_ip
            except ValueError:
                pass  # IP malformada — usar REMOTE_ADDR

    return remote_addr


def registrar_log(
    request,
    tipo_accion,
    descripcion,
    modelo_afectado=None,
    objeto_id=None,
    campos_modificados=None
):
    """
    Registra un log de actividad en el sistema.

    Args:
        request: La solicitud HTTP
        tipo_accion: Tipo de acción (login, logout, create, update, delete, view, other)
        descripcion: Descripción detallada de la acción
        modelo_afectado: Nombre del modelo afectado (opcional)
        objeto_id: ID del objeto afectado (opcional)
        campos_modificados: Diccionario con los campos modificados (opcional)

    Returns:
        LogActividad: El registro creado
    """
    # Obtener datos del usuario
    usuario = request.user if request.user.is_authenticated else None
    nombre_usuario = usuario.username if usuario else 'Anónimo'

    # Obtener IP real validando proxies confiables (CRIT-02)
    ip = _get_real_ip(request)

    # Obtener user agent — limitar longitud para prevenir log injection (LOW-02)
    navegador = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    # Crear el log
    log = LogActividad.objects.create(
        usuario=usuario,
        nombre_usuario=nombre_usuario,
        tipo_accion=tipo_accion,
        descripcion=descripcion,
        modelo_afectado=modelo_afectado,
        objeto_id=objeto_id,
        campos_modificados=campos_modificados,
        direccion_ip=ip,
        navegador=navegador
    )
    
    return log


def registrar_login(request, usuario):
    """Registra un inicio de sesión"""
    return registrar_log(
        request=request,
        tipo_accion='login',
        descripcion=f"El usuario {usuario.username} ha iniciado sesión",
    )


def registrar_logout(request, usuario):
    """Registra un cierre de sesión"""
    return registrar_log(
        request=request,
        tipo_accion='logout',
        descripcion=f"El usuario {usuario.username} ha cerrado sesión",
    )


def registrar_creacion(request, modelo, objeto):
    """Registra la creación de un objeto"""
    return registrar_log(
        request=request,
        tipo_accion='create',
        descripcion=f"Se ha creado un nuevo registro de {modelo}",
        modelo_afectado=modelo,
        objeto_id=str(objeto.pk),
    )


def registrar_actualizacion(request, modelo, objeto, campos_modificados):
    """Registra la actualización de un objeto"""
    return registrar_log(
        request=request,
        tipo_accion='update',
        descripcion=f"Se ha actualizado un registro de {modelo}",
        modelo_afectado=modelo,
        objeto_id=str(objeto.pk),
        campos_modificados=campos_modificados
    )


def registrar_eliminacion(request, modelo, objeto_id):
    """Registra la eliminación de un objeto"""
    return registrar_log(
        request=request,
        tipo_accion='delete',
        descripcion=f"Se ha eliminado un registro de {modelo}",
        modelo_afectado=modelo,
        objeto_id=str(objeto_id),
    )


def registrar_visualizacion(request, modelo, objeto):
    """Registra la visualización de un objeto"""
    return registrar_log(
        request=request,
        tipo_accion='view',
        descripcion=f"Se ha visualizado un registro de {modelo}",
        modelo_afectado=modelo,
        objeto_id=str(objeto.pk),
    )
