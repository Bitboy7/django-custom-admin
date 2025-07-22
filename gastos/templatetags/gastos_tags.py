from django import template
from gastos.models import CatGastos, Cuenta
from django.contrib.humanize.templatetags.humanize import intcomma
from decimal import Decimal

register = template.Library()

@register.simple_tag
def get_cat_gastos():
    """Obtiene todas las categorías de gastos"""
    return CatGastos.objects.all().order_by('nombre')

@register.simple_tag
def get_cuentas():
    """Obtiene todas las cuentas"""
    return Cuenta.objects.all().order_by('id_banco__nombre', 'numero_cuenta')

@register.filter
def us_currency(value, decimal_places=2):
    """
    Formatea un número como moneda en formato estadounidense
    Ejemplo: 1234.56 -> 1,234.56
    """
    if value is None or value == '':
        return '0.00'
    
    try:
        # Convertir a Decimal para mayor precisión
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        # Formatear con la cantidad específica de decimales
        formatted = f"{value:.{decimal_places}f}"
        
        # Separar parte entera y decimal
        if '.' in formatted:
            integer_part, decimal_part = formatted.split('.')
        else:
            integer_part, decimal_part = formatted, ''
        
        # Agregar separadores de miles
        integer_with_commas = intcomma(integer_part)
        
        # Retornar formato completo
        if decimal_places > 0:
            return f"{integer_with_commas}.{decimal_part}"
        else:
            return integer_with_commas
            
    except (ValueError, TypeError, AttributeError):
        return '0.00'

@register.filter
def us_number(value, decimal_places=2):
    """
    Formatea un número en formato estadounidense sin símbolo de moneda
    Ejemplo: 1234.56 -> 1,234.56
    """
    return us_currency(value, decimal_places)
