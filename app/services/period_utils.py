"""
Utilidades para manejo de períodos y agregaciones temporales

Este módulo proporciona funciones reutilizables para agrupar datos
por diferentes períodos de tiempo (diario, semanal, mensual).
"""
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from typing import Dict, List, Optional, Any


class PeriodAggregator:
    """Agregador de datos por períodos de tiempo"""
    
    # Mapeo de períodos a funciones de truncamiento
    PERIOD_TRUNCATORS = {
        'diario': TruncDay,
        'semanal': TruncWeek,
        'mensual': TruncMonth
    }
    
    @staticmethod
    def get_truncator(periodo: str):
        """
        Obtiene la función de truncamiento apropiada para el período
        
        Args:
            periodo: Tipo de período ('diario', 'semanal', 'mensual')
            
        Returns:
            Clase de truncamiento de Django (TruncDay, TruncWeek, TruncMonth)
        """
        return PeriodAggregator.PERIOD_TRUNCATORS.get(
            periodo.lower(), 
            TruncMonth
        )
    
    @staticmethod
    def aggregate_by_period(
        queryset,
        periodo: str,
        group_fields: List[str],
        sum_field: str = 'monto',
        annotation_name: str = 'total',
        date_field: str = 'fecha'
    ):
        """
        Agrega un queryset por período de tiempo
        
        Args:
            queryset: QuerySet de Django a agregar
            periodo: Tipo de período ('diario', 'semanal', 'mensual')
            group_fields: Lista de campos por los que agrupar (ej: ['categoria', 'sucursal'])
            sum_field: Campo a sumar (default: 'monto')
            annotation_name: Nombre para la anotación del total (default: 'total')
            date_field: Campo de fecha a usar (default: 'fecha')
            
        Returns:
            QuerySet anotado con el total y agrupado por los campos especificados
            
        Example:
            >>> aggregate_by_period(
            ...     Gastos.objects.all(),
            ...     'mensual',
            ...     ['id_cuenta_banco__nombre', 'id_sucursal__nombre'],
            ...     'monto',
            ...     'total_gastos'
            ... )
        """
        truncator = PeriodAggregator.get_truncator(periodo)
        
        # Anotar con el período truncado
        queryset = queryset.annotate(
            periodo=truncator(date_field)
        )
        
        # Construir la lista de campos para values()
        # Incluir el período y todos los campos de agrupación
        value_fields = ['periodo'] + group_fields
        
        # Agrupar y sumar
        return queryset.values(*value_fields).annotate(
            **{annotation_name: Sum(sum_field)}
        ).order_by('periodo', *group_fields)
    
    @staticmethod
    def aggregate_with_multiple_sums(
        queryset,
        periodo: str,
        group_fields: List[str],
        sum_fields: Dict[str, str],
        date_field: str = 'fecha'
    ):
        """
        Agrega un queryset por período con múltiples campos a sumar
        
        Args:
            queryset: QuerySet de Django a agregar
            periodo: Tipo de período
            group_fields: Lista de campos por los que agrupar
            sum_fields: Diccionario {nombre_anotación: campo_a_sumar}
            date_field: Campo de fecha a usar
            
        Returns:
            QuerySet con múltiples sumas anotadas
            
        Example:
            >>> aggregate_with_multiple_sums(
            ...     Ventas.objects.all(),
            ...     'mensual',
            ...     ['producto', 'sucursal'],
            ...     {'total_ventas': 'monto', 'total_cantidad': 'cantidad'}
            ... )
        """
        truncator = PeriodAggregator.get_truncator(periodo)
        
        queryset = queryset.annotate(
            periodo=truncator(date_field)
        )
        
        value_fields = ['periodo'] + group_fields
        
        # Construir las anotaciones dinámicamente
        annotations = {
            annotation_name: Sum(field_name)
            for annotation_name, field_name in sum_fields.items()
        }
        
        return queryset.values(*value_fields).annotate(
            **annotations
        ).order_by('periodo', *group_fields)
    
    @staticmethod
    def aggregate_with_count(
        queryset,
        periodo: str,
        group_fields: List[str],
        sum_field: Optional[str] = None,
        count_annotation: str = 'total_registros',
        sum_annotation: Optional[str] = None,
        date_field: str = 'fecha'
    ):
        """
        Agrega un queryset con conteo de registros y opcionalmente suma
        
        Args:
            queryset: QuerySet a agregar
            periodo: Tipo de período
            group_fields: Campos de agrupación
            sum_field: Campo a sumar (opcional)
            count_annotation: Nombre para el conteo
            sum_annotation: Nombre para la suma (requerido si sum_field se proporciona)
            date_field: Campo de fecha
            
        Returns:
            QuerySet con conteo y suma (si aplica)
        """
        truncator = PeriodAggregator.get_truncator(periodo)
        
        queryset = queryset.annotate(
            periodo=truncator(date_field)
        )
        
        value_fields = ['periodo'] + group_fields
        
        annotations = {count_annotation: Count('id')}
        
        if sum_field and sum_annotation:
            annotations[sum_annotation] = Sum(sum_field)
        
        return queryset.values(*value_fields).annotate(
            **annotations
        ).order_by('periodo', *group_fields)


class StatisticsCalculator:
    """Calculador de estadísticas para reportes"""
    
    @staticmethod
    def calculate_basic_stats(queryset, field: str = 'monto') -> Dict[str, Any]:
        """
        Calcula estadísticas básicas (sum, avg, max, min, count)
        
        Args:
            queryset: QuerySet de Django
            field: Campo numérico sobre el que calcular estadísticas
            
        Returns:
            Diccionario con las estadísticas calculadas
        """
        from django.db.models import Sum, Avg, Max, Min, Count
        
        stats = queryset.aggregate(
            total=Sum(field),
            promedio=Avg(field),
            maximo=Max(field),
            minimo=Min(field),
            cantidad=Count('id')
        )
        
        # Convertir a float para compatibilidad con serialización
        return {
            'total': float(stats['total'] or 0),
            'promedio': float(stats['promedio'] or 0),
            'maximo': float(stats['maximo'] or 0),
            'minimo': float(stats['minimo'] or 0),
            'cantidad': stats['cantidad']
        }
    
    @staticmethod
    def calculate_median(queryset, field: str = 'monto') -> float:
        """
        Calcula la mediana de un campo
        
        Args:
            queryset: QuerySet de Django
            field: Campo numérico
            
        Returns:
            Valor de la mediana
        """
        import numpy as np
        
        values = list(queryset.values_list(field, flat=True))
        
        if not values:
            return 0.0
        
        # Convertir a float para numpy
        float_values = [float(v) for v in values if v is not None]
        
        if not float_values:
            return 0.0
        
        return float(np.median(float_values))
    
    @staticmethod
    def calculate_extended_stats(queryset, field: str = 'monto') -> Dict[str, Any]:
        """
        Calcula estadísticas extendidas incluyendo mediana
        
        Args:
            queryset: QuerySet de Django
            field: Campo numérico
            
        Returns:
            Diccionario con estadísticas básicas + mediana
        """
        stats = StatisticsCalculator.calculate_basic_stats(queryset, field)
        stats['mediana'] = StatisticsCalculator.calculate_median(queryset, field)
        return stats
    
    @staticmethod
    def calculate_grouped_stats(
        queryset,
        group_field: str,
        value_field: str = 'monto'
    ) -> List[Dict[str, Any]]:
        """
        Calcula estadísticas agrupadas por un campo
        
        Args:
            queryset: QuerySet de Django
            group_field: Campo por el que agrupar
            value_field: Campo numérico a analizar
            
        Returns:
            Lista de diccionarios con estadísticas por grupo
        """
        from django.db.models import Sum, Avg, Count
        
        return list(queryset.values(group_field).annotate(
            total=Sum(value_field),
            promedio=Avg(value_field),
            cantidad=Count('id')
        ).order_by('-total'))


class AccumulatedCalculator:
    """Calculador de valores acumulados"""
    
    @staticmethod
    def calculate_accumulated(
        data: List[Dict[str, Any]], 
        value_field: str = 'total',
        accumulated_field: str = 'acumulado'
    ) -> List[Dict[str, Any]]:
        """
        Calcula valores acumulados sobre una lista de diccionarios
        
        Args:
            data: Lista de diccionarios con los datos
            value_field: Nombre del campo con el valor a acumular
            accumulated_field: Nombre del campo donde guardar el acumulado
            
        Returns:
            Lista con el campo acumulado añadido
            
        Example:
            >>> data = [
            ...     {'mes': 'Enero', 'total': 100},
            ...     {'mes': 'Febrero', 'total': 150},
            ...     {'mes': 'Marzo', 'total': 200}
            ... ]
            >>> calculate_accumulated(data)
            [
                {'mes': 'Enero', 'total': 100, 'acumulado': 100},
                {'mes': 'Febrero', 'total': 150, 'acumulado': 250},
                {'mes': 'Marzo', 'total': 200, 'acumulado': 450}
            ]
        """
        accumulated = 0
        result = []
        
        for item in data:
            value = item.get(value_field, 0)
            # Convertir Money a float si es necesario
            if hasattr(value, 'amount'):
                value = float(value.amount)
            else:
                value = float(value or 0)
            
            accumulated += value
            item_copy = item.copy()
            item_copy[accumulated_field] = accumulated
            result.append(item_copy)
        
        return result
    
    @staticmethod
    def calculate_percentage_of_total(
        data: List[Dict[str, Any]],
        value_field: str = 'total',
        percentage_field: str = 'porcentaje'
    ) -> List[Dict[str, Any]]:
        """
        Calcula el porcentaje que representa cada valor del total
        
        Args:
            data: Lista de diccionarios con los datos
            value_field: Campo con el valor
            percentage_field: Campo donde guardar el porcentaje
            
        Returns:
            Lista con porcentajes calculados
        """
        # Calcular total
        total = sum(
            float(item.get(value_field, 0).amount if hasattr(item.get(value_field, 0), 'amount') 
                  else item.get(value_field, 0) or 0)
            for item in data
        )
        
        if total == 0:
            return data
        
        result = []
        for item in data:
            value = item.get(value_field, 0)
            if hasattr(value, 'amount'):
                value = float(value.amount)
            else:
                value = float(value or 0)
            
            item_copy = item.copy()
            item_copy[percentage_field] = round((value / total) * 100, 2)
            result.append(item_copy)
        
        return result


class PeriodFormatter:
    """Formateador de períodos para visualización"""
    
    MONTHS_ES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    @staticmethod
    def format_period_display(periodo: str, date_value) -> str:
        """
        Formatea un valor de fecha según el período para visualización
        
        Args:
            periodo: Tipo de período ('diario', 'semanal', 'mensual')
            date_value: Valor de fecha a formatear
            
        Returns:
            String formateado para mostrar
        """
        if not date_value:
            return "N/A"
        
        periodo = periodo.lower()
        
        if periodo == 'diario':
            return date_value.strftime('%d/%m/%Y')
        elif periodo == 'semanal':
            return f"Semana {date_value.isocalendar()[1]} - {date_value.year}"
        elif periodo == 'mensual':
            month_name = PeriodFormatter.MONTHS_ES[date_value.month - 1]
            return f"{month_name} {date_value.year}"
        else:
            return str(date_value)
    
    @staticmethod
    def get_month_name(month_number: int) -> str:
        """
        Obtiene el nombre del mes en español
        
        Args:
            month_number: Número del mes (1-12)
            
        Returns:
            Nombre del mes
        """
        if 1 <= month_number <= 12:
            return PeriodFormatter.MONTHS_ES[month_number - 1]
        return "Mes inválido"
