from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from decimal import Decimal
import locale

register = template.Library()

@register.filter
def currency_format(value, currency='USD'):
    """
    Formatea un valor como moneda
    Uso: {{ valor|currency_format:"MXN" }}
    """
    if value is None or value == '':
        return '$0.00'
    
    try:
        # Convertir a float si es necesario
        if isinstance(value, (str, Decimal)):
            value = float(value)
        
        # Formatear como moneda
        if currency == 'MXN':
            return f"${value:,.2f}"
        else:
            return f"${value:,.2f} {currency}"
    except (ValueError, TypeError):
        return '$0.00'

@register.filter
def percentage(value, total):
    """
    Calcula el porcentaje de un valor respecto al total
    Uso: {{ valor|percentage:total }}
    """
    if not total or total == 0:
        return 0
    
    try:
        value = float(value) if value else 0
        total = float(total)
        return round((value / total) * 100, 1)
    except (ValueError, TypeError):
        return 0

@register.filter
def estado_badge_class(estado):
    """
    Devuelve las clases CSS para el estado de cobranza
    Uso: {{ estado|estado_badge_class }}
    """
    if not estado:
        return 'px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600'
    
    class_map = {
        'Pagado': 'px-2 py-1 text-xs rounded-full bg-green-100 text-green-800 font-medium',
        'Pendiente': 'px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 font-medium', 
        'Parcial': 'px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800 font-medium',
        'Vencido': 'px-2 py-1 text-xs rounded-full bg-red-100 text-red-800 font-medium',
        'Incobrable': 'px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600 font-medium'
    }
    
    return class_map.get(estado, 'px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600')

@register.filter
def estado_cobranza_badge(estado):
    """
    Convierte el estado de cobranza en un badge HTML con colores
    Uso: {{ venta.estado_cobranza|estado_cobranza_badge }}
    """
    if not estado:
        return ''
    
    color_map = {
        'Pagado': 'success',
        'Pendiente': 'warning', 
        'Parcial': 'info',
        'Vencido': 'danger',
        'Incobrable': 'secondary'
    }
    
    color = color_map.get(estado, 'secondary')
    
    return format_html(
        '<span class="badge badge-{} estado-{}">{}</span>',
        color,
        estado.lower(),
        estado
    )

@register.filter
def modalidad_pago_class(modalidad):
    """
    Devuelve la clase CSS para la modalidad de pago
    Uso: {{ venta.modalidad_pago|modalidad_pago_class }}
    """
    if modalidad == 'Contado':
        return 'venta-contado'
    elif modalidad == 'Credito':
        return 'venta-credito'
    else:
        return 'text-gray-600'

@register.filter
def days_until_due(fecha_vencimiento):
    """
    Calcula los días hasta el vencimiento
    Uso: {{ venta.fecha_vencimiento|days_until_due }}
    """
    if not fecha_vencimiento:
        return None
    
    from django.utils import timezone
    from datetime import date
    
    if isinstance(fecha_vencimiento, date):
        today = timezone.now().date()
        delta = fecha_vencimiento - today
        return delta.days
    
    return None

@register.filter
def days_overdue_badge(dias):
    """
    Convierte días de vencimiento en badge con colores
    Uso: {{ dias|days_overdue_badge }}
    """
    if dias is None:
        return ''
    
    if dias > 0:
        # Próximo a vencer (verde)
        if dias <= 7:
            color = 'warning'
            icon = 'exclamation-triangle'
        else:
            color = 'success'
            icon = 'calendar-check'
        return format_html(
            '<span class="badge badge-{} d-inline-flex align-items-center">'
            '<i class="fas fa-{} mr-1"></i>{} días</span>',
            color, icon, abs(dias)
        )
    elif dias < 0:
        # Vencido (rojo)
        return format_html(
            '<span class="badge badge-danger d-inline-flex align-items-center">'
            '<i class="fas fa-exclamation-circle mr-1"></i>+{} días</span>',
            abs(dias)
        )
    else:
        # Vence hoy (amarillo)
        return format_html(
            '<span class="badge badge-warning d-inline-flex align-items-center">'
            '<i class="fas fa-clock mr-1"></i>Vence hoy</span>'
        )

@register.simple_tag
def progress_bar(current, total, height='4px', color='success'):
    """
    Genera una barra de progreso
    Uso: {% progress_bar pagado total height="6px" color="info" %}
    """
    if not total or total == 0:
        percentage = 0
    else:
        try:
            current = float(current) if current else 0
            total = float(total)
            percentage = min((current / total) * 100, 100)
        except (ValueError, TypeError):
            percentage = 0
    
    return format_html(
        '<div class="progress" style="height: {}">'
        '<div class="progress-bar bg-{}" role="progressbar" style="width: {}%;" '
        'aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100"></div>'
        '</div>',
        height, color, percentage, percentage
    )

@register.simple_tag
def credit_risk_indicator(calificacion):
    """
    Genera un indicador visual de riesgo crediticio
    Uso: {% credit_risk_indicator cliente.calificacion_credito %}
    """
    color_map = {
        'A+': ('success', 'Excelente'),
        'A': ('info', 'Bueno'),
        'B': ('warning', 'Regular'),
        'C': ('danger', 'Riesgoso')
    }
    
    color, descripcion = color_map.get(calificacion, ('secondary', 'Sin calificar'))
    
    return format_html(
        '<span class="badge badge-{} d-inline-flex align-items-center" title="{}">'
        '<i class="fas fa-star mr-1"></i>{}</span>',
        color, descripcion, calificacion
    )

@register.filter
def subtract(value, arg):
    """
    Resta dos números
    Uso: {{ total|subtract:pagado }}
    """
    try:
        value = float(value) if value else 0
        arg = float(arg) if arg else 0
        return value - arg
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """
    Multiplica dos números
    Uso: {{ precio|multiply:cantidad }}
    """
    try:
        value = float(value) if value else 0
        arg = float(arg) if arg else 0
        return value * arg
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Divide dos números
    Uso: {{ total|divide:cantidad }}
    """
    try:
        value = float(value) if value else 0
        arg = float(arg) if arg else 1
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError):
        return 0

@register.simple_tag
def sales_summary_card(title, value, icon, color='primary', subtitle=''):
    """
    Genera una tarjeta de resumen de ventas
    Uso: {% sales_summary_card "Total Ventas" total_ventas "dollar-sign" "success" %}
    """
    return format_html(
        '<div class="card border-{} h-100">'
        '<div class="card-body d-flex align-items-center">'
        '<div class="mr-3">'
        '<i class="fas fa-{} fa-2x text-{}"></i>'
        '</div>'
        '<div>'
        '<h5 class="card-title mb-1">{}</h5>'
        '<p class="card-text h4 text-{} mb-0">${:,.2f}</p>'
        '{}'
        '</div>'
        '</div>'
        '</div>',
        color, icon, color, title, color, float(value) if value else 0,
        f'<small class="text-muted">{subtitle}</small>' if subtitle else ''
    )

@register.inclusion_tag('ventas/partials/client_info.html')
def client_info_card(cliente):
    """
    Template tag de inclusión para mostrar información del cliente
    Uso: {% client_info_card cliente %}
    """
    return {'cliente': cliente}

@register.simple_tag
def format_incoterm(incoterm, cliente_pais=''):
    """
    Formatea y explica los Incoterms
    Uso: {% format_incoterm venta.incoterm venta.cliente.pais.nombre %}
    """
    if not incoterm:
        return ''
    
    incoterm_descriptions = {
        'FOB': 'Free On Board - El vendedor entrega cuando la mercancía sobrepasa la borda del buque',
        'CIF': 'Cost, Insurance and Freight - El vendedor paga costos, seguro y flete hasta puerto destino',
        'EXW': 'Ex Works - El vendedor pone la mercancía a disposición en sus instalaciones',
        'DDP': 'Delivered Duty Paid - El vendedor entrega pagando todos los costos hasta destino'
    }
    
    description = incoterm_descriptions.get(incoterm, incoterm)
    
    return format_html(
        '<span class="badge badge-info" data-toggle="tooltip" title="{}">{}</span>',
        description, incoterm
    )

@register.filter 
def months_between(start_date, end_date):
    """
    Calcula los meses entre dos fechas
    Uso: {{ fecha_inicio|months_between:fecha_fin }}
    """
    if not start_date or not end_date:
        return 0
    
    try:
        from dateutil.relativedelta import relativedelta
        diff = relativedelta(end_date, start_date)
        return diff.months + (diff.years * 12)
    except ImportError:
        # Fallback si dateutil no está disponible
        days_diff = (end_date - start_date).days
        return round(days_diff / 30.44)  # Promedio de días por mes


@register.filter
def get_item(dictionary, key):
    """
    Permite acceder a un diccionario por clave dinámica en templates.
    Uso: {{ mi_dict|get_item:clave }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
