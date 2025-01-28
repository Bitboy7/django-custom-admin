from django import template
from gastos.models import Cuenta

register = template.Library()

@register.filter
def get_cuenta(cuentas, cuenta_id):
    try:
        return cuentas.get(id=cuenta_id)
    except Cuenta.DoesNotExist:
        return None

@register.filter
def get_logotipo_url(cuenta):
    if cuenta and cuenta.id_banco and cuenta.id_banco.logotipo:
        return cuenta.id_banco.logotipo.url
    return ''