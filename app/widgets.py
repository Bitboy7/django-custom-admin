"""
Widgets personalizados para import-export
"""
from import_export.widgets import Widget
from djmoney.money import Money
from decimal import Decimal, InvalidOperation
import re


class MoneyWidget(Widget):
    """
    Widget personalizado para campos MoneyField que maneja
    la conversión entre string/float y Money objects con validación robusta
    """
    
    def clean(self, value, row=None, *args, **kwargs):
        """
        Convierte el valor importado a un objeto Money
        """
        if not value or value in ['', None]:
            return Money(0, 'MXN')
        
        try:
            # Si es un string, intentar limpiarlo y convertirlo
            if isinstance(value, str):
                # Remover símbolos de moneda, comas, espacios y caracteres especiales
                clean_value = re.sub(r'[^\d.-]', '', value.replace(',', ''))
                if clean_value == '' or clean_value == '-':
                    return Money(0, 'MXN')
                
                # Manejar valores con múltiples puntos (posibles errores de formato)
                if clean_value.count('.') > 1:
                    # Conservar solo el último punto como separador decimal
                    parts = clean_value.split('.')
                    clean_value = ''.join(parts[:-1]) + '.' + parts[-1]
                
                decimal_value = Decimal(clean_value)
                return Money(decimal_value, 'MXN')
            
            # Si es un número, convertir a Decimal primero
            elif isinstance(value, (int, float)):
                # Manejar casos de NaN o infinito
                if str(value).lower() in ['nan', 'inf', '-inf']:
                    return Money(0, 'MXN')
                decimal_value = Decimal(str(value))
                return Money(decimal_value, 'MXN')
            
            # Si ya es un objeto Money, devolverlo tal como está
            elif isinstance(value, Money):
                return value
            
            # Si es un Decimal, crear Money directamente
            elif isinstance(value, Decimal):
                return Money(value, 'MXN')
                
        except (ValueError, InvalidOperation, TypeError) as e:
            # En caso de error, log el valor problemático y devolver 0
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"No se puede convertir '{value}' (tipo: {type(value)}) a Money: {e}")
            return Money(0, 'MXN')
        
        # Fallback para casos no manejados
        return Money(0, 'MXN')
    
    def render(self, value, obj=None, **kwargs):
        """
        Convierte el objeto Money a string para exportación en formato US
        (comas para miles, puntos para decimales)
        """
        try:
            if isinstance(value, Money):
                # Usar el amount como Decimal para mantener precisión
                amount = value.amount
                # Formatear con 2 decimales
                formatted = f"{amount:.2f}"
                
                # Separar parte entera y decimal
                if '.' in formatted:
                    integer_part, decimal_part = formatted.split('.')
                else:
                    integer_part, decimal_part = formatted, '00'
                
                # Agregar separadores de miles (comas)
                # Convertir a int primero para usar el formato de miles
                integer_value = int(float(integer_part))
                integer_with_commas = f"{integer_value:,}"
                
                # Retornar en formato US: 1,234.56
                return f"{integer_with_commas}.{decimal_part}"
            elif value is not None and value != '':
                # Si no es Money, intentar formatear como número
                try:
                    numeric_value = Decimal(str(value))
                    formatted = f"{numeric_value:.2f}"
                    if '.' in formatted:
                        integer_part, decimal_part = formatted.split('.')
                    else:
                        integer_part, decimal_part = formatted, '00'
                    
                    integer_value = int(float(integer_part))
                    integer_with_commas = f"{integer_value:,}"
                    return f"{integer_with_commas}.{decimal_part}"
                except (ValueError, TypeError):
                    return str(value)
            return "0.00"
        except (ValueError, TypeError):
            return "0.00"


class DecimalWidget(Widget):
    """
    Widget para campos Decimal con mejor manejo de errores
    """
    
    def clean(self, value, row=None, *args, **kwargs):
        """
        Convierte el valor a Decimal de manera segura
        """
        if not value or value in ['', None]:
            return Decimal('0.00')
        
        try:
            if isinstance(value, str):
                clean_value = re.sub(r'[^\d.-]', '', value.replace(',', ''))
                if clean_value == '' or clean_value == '-':
                    return Decimal('0.00')
                return Decimal(clean_value)
            elif isinstance(value, (int, float)):
                if str(value).lower() in ['nan', 'inf', '-inf']:
                    return Decimal('0.00')
                return Decimal(str(value))
            elif isinstance(value, Decimal):
                return value
        except (ValueError, InvalidOperation, TypeError):
            return Decimal('0.00')
        
        return Decimal('0.00')
    
    def render(self, value, obj=None, **kwargs):
        """
        Renderiza el Decimal como string
        """
        try:
            if value is not None:
                return str(value)
            return "0.00"
        except (ValueError, TypeError):
            return "0.00"
