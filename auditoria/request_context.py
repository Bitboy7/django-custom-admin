"""Actor contextual para eventos de dominio y auditoría del modelo."""
from contextvars import ContextVar, Token


_audit_actor = ContextVar('audit_actor', default=None)


def set_audit_actor(user) -> Token:
    return _audit_actor.set(user)


def reset_audit_actor(token: Token) -> None:
    _audit_actor.reset(token)


def get_audit_actor():
    user = _audit_actor.get()
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    return user


def registrar_evento_modelo(
    *, tipo_accion, descripcion, modelo_afectado, objeto_id,
    campos_modificados=None,
):
    """Registra un evento de dominio con el usuario actual o ``Sistema``."""
    from .models import LogActividad

    usuario = get_audit_actor()
    return LogActividad.objects.create(
        usuario=usuario,
        nombre_usuario=usuario.get_username() if usuario else 'Sistema',
        tipo_accion=tipo_accion,
        descripcion=descripcion,
        modelo_afectado=modelo_afectado,
        objeto_id=str(objeto_id) if objeto_id is not None else None,
        campos_modificados=campos_modificados,
    )
