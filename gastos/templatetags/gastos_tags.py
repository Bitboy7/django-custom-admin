from django import template
from gastos.models import CatGastos, Cuenta

register = template.Library()

@register.simple_tag
def get_cat_gastos():
    """Obtiene todas las categorías de gastos"""
    return CatGastos.objects.all().order_by('nombre')

@register.simple_tag
def get_cuentas():
    """Obtiene todas las cuentas"""
    return Cuenta.objects.all().order_by('id_banco__nombre', 'numero_cuenta')
