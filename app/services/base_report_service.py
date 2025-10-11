"""
Servicio base para reportes reutilizables

Este módulo proporciona una clase base abstracta que puede ser heredada
por diferentes servicios de reporte (gastos, compras, ventas, etc.).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from django.db.models import QuerySet

from .filter_utils import FilterBuilder, FilterOptionsProvider
from .period_utils import (
    PeriodAggregator, 
    StatisticsCalculator,
    AccumulatedCalculator,
    PeriodFormatter
)


class BaseReportService(ABC):
    """
    Clase base abstracta para servicios de reporte
    
    Esta clase proporciona funcionalidad común para diferentes tipos de reportes
    (gastos, compras, ventas, etc.). Las subclases deben implementar los métodos
    abstractos para personalizar el comportamiento específico.
    
    Example:
        >>> class GastosReportService(BaseReportService):
        ...     def get_model(self):
        ...         return Gastos
        ...     
        ...     def get_date_field(self):
        ...         return 'fecha'
        ...     
        ...     def get_amount_field(self):
        ...         return 'monto'
        ...     
        ...     def get_group_fields(self, periodo):
        ...         return [
        ...             'id_categoria__categoria',
        ...             'id_cuenta_banco__nombre',
        ...             'id_sucursal__nombre'
        ...         ]
    """
    
    def __init__(self):
        """Inicializa el servicio con las utilidades necesarias"""
        self.filter_builder = FilterBuilder()
        self.filter_options = FilterOptionsProvider()
        self.period_aggregator = PeriodAggregator()
        self.stats_calculator = StatisticsCalculator()
        self.accumulated_calculator = AccumulatedCalculator()
        self.period_formatter = PeriodFormatter()
    
    # ==================== MÉTODOS ABSTRACTOS ====================
    # Estos métodos DEBEN ser implementados por las subclases
    
    @abstractmethod
    def get_model(self):
        """
        Retorna el modelo Django a usar para este reporte
        
        Returns:
            Modelo de Django (ej: Gastos, Compras, Ventas)
        """
        pass
    
    @abstractmethod
    def get_date_field(self) -> str:
        """
        Retorna el nombre del campo de fecha principal
        
        Returns:
            Nombre del campo (ej: 'fecha', 'fecha_compra', 'fecha_venta')
        """
        pass
    
    @abstractmethod
    def get_amount_field(self) -> str:
        """
        Retorna el nombre del campo de monto/importe
        
        Returns:
            Nombre del campo (ej: 'monto', 'total', 'importe')
        """
        pass
    
    @abstractmethod
    def get_group_fields(self, periodo: str) -> List[str]:
        """
        Retorna los campos por los que agrupar según el período
        
        Args:
            periodo: Tipo de período ('diario', 'semanal', 'mensual')
            
        Returns:
            Lista de campos para agrupar (con lookups si es necesario)
            Ej: ['id_categoria__categoria', 'id_sucursal__nombre']
        """
        pass
    
    # ==================== MÉTODOS CON IMPLEMENTACIÓN POR DEFECTO ====================
    # Estos métodos pueden ser sobreescritos si se necesita personalización
    
    def get_filter_fields(self) -> List[str]:
        """
        Retorna los campos que se pueden usar para filtrar
        
        Returns:
            Lista de nombres de campos
        """
        return [
            'year', 'month', 'selected_months', 'periodo',
            'dia', 'fecha_inicio', 'fecha_fin',
            'cuenta_id', 'sucursal_id'
        ]
    
    def get_filter_options_config(self) -> Dict[str, bool]:
        """
        Retorna la configuración de qué opciones de filtro incluir
        
        Returns:
            Diccionario con flags booleanos para cada tipo de filtro
        """
        return {
            'include_cuentas': True,
            'include_sucursales': True,
            'include_proveedores': False,
            'include_clientes': False
        }
    
    def get_total_annotation_name(self) -> str:
        """
        Retorna el nombre para la anotación del total
        
        Returns:
            Nombre del campo anotado (ej: 'total_gastos', 'total_compras')
        """
        return f'total_{self.get_model()._meta.model_name}'
    
    def should_use_default_year(self) -> bool:
        """
        Indica si debe usar el año actual por defecto si no se proporciona
        
        Returns:
            True si debe usar año por defecto, False si no
        """
        return True
    
    # ==================== MÉTODOS PÚBLICOS DE LA API ====================
    
    def get_filter_data(self) -> Dict[str, Any]:
        """
        Obtiene los datos necesarios para los filtros de la vista
        
        Returns:
            Diccionario con años disponibles, meses, cuentas, sucursales, etc.
        """
        model = self.get_model()
        date_field = self.get_date_field()
        config = self.get_filter_options_config()
        
        return self.filter_options.get_filter_options(
            model=model,
            date_field=date_field,
            **config
        )
    
    def build_filters(
        self,
        cuenta_id: Any = None,
        year: Any = None,
        month: Any = None,
        selected_months: Optional[List[int]] = None,
        periodo: str = 'mensual',
        dia: Any = None,
        fecha_inicio: Any = None,
        fecha_fin: Any = None,
        sucursal_id: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Construye filtros validados desde parámetros
        
        Args:
            cuenta_id: ID de cuenta bancaria
            year: Año a filtrar
            month: Mes a filtrar
            selected_months: Lista de meses
            periodo: Tipo de período
            dia: Día específico
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha fin
            sucursal_id: ID de sucursal
            **kwargs: Parámetros adicionales (proveedor_id, cliente_id, etc.)
            
        Returns:
            Diccionario con filtros validados listos para usar en QuerySet
        """
        return self.filter_builder.build_standard_filters(
            year=year,
            month=month,
            selected_months=selected_months,
            cuenta_id=cuenta_id,
            sucursal_id=sucursal_id,
            periodo=periodo,
            dia=dia,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            use_default_year=self.should_use_default_year(),
            **kwargs
        )
    
    def get_balances_by_period(
        self, 
        filters: Dict[str, Any], 
        periodo: str = 'mensual'
    ) -> QuerySet:
        """
        Obtiene balances agrupados por período
        
        Args:
            filters: Diccionario de filtros a aplicar
            periodo: Tipo de período ('diario', 'semanal', 'mensual')
            
        Returns:
            QuerySet con los datos agregados por período
        """
        model = self.get_model()
        queryset = model.objects.filter(**filters)
        
        group_fields = self.get_group_fields(periodo)
        amount_field = self.get_amount_field()
        date_field = self.get_date_field()
        annotation_name = self.get_total_annotation_name()
        
        return self.period_aggregator.aggregate_by_period(
            queryset=queryset,
            periodo=periodo,
            group_fields=group_fields,
            sum_field=amount_field,
            annotation_name=annotation_name,
            date_field=date_field
        )
    
    def calculate_accumulated(
        self, 
        balances: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calcula valores acumulados sobre los balances
        
        Args:
            balances: Lista de diccionarios con los balances
            
        Returns:
            Lista con el campo 'acumulado' añadido
        """
        annotation_name = self.get_total_annotation_name()
        
        return self.accumulated_calculator.calculate_accumulated(
            data=balances,
            value_field=annotation_name,
            accumulated_field='acumulado'
        )
    
    def calculate_statistics(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula estadísticas sobre los datos filtrados
        
        Args:
            filters: Diccionario de filtros a aplicar
            
        Returns:
            Diccionario con estadísticas (total, promedio, máximo, mínimo, etc.)
        """
        model = self.get_model()
        queryset = model.objects.filter(**filters)
        amount_field = self.get_amount_field()
        
        return self.stats_calculator.calculate_extended_stats(
            queryset=queryset,
            field=amount_field
        )
    
    def extract_filters_from_request(self, request):
        """
        Extrae y valida filtros desde un request de Django
        
        Args:
            request: Objeto HttpRequest
            
        Returns:
            Diccionario con los parámetros filtrados y validados
        """
        filter_fields = self.get_filter_fields()
        
        return self.filter_builder.extract_filters_from_request(
            request=request,
            filter_fields=filter_fields
        )
    
    def format_period(self, periodo: str, date_value) -> str:
        """
        Formatea un valor de fecha según el período para visualización
        
        Args:
            periodo: Tipo de período
            date_value: Valor de fecha
            
        Returns:
            String formateado
        """
        return self.period_formatter.format_period_display(periodo, date_value)
    
    def calculate_percentage_distribution(
        self,
        balances: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calcula la distribución porcentual de los balances
        
        Args:
            balances: Lista de diccionarios con los balances
            
        Returns:
            Lista con porcentajes calculados
        """
        annotation_name = self.get_total_annotation_name()
        
        return self.accumulated_calculator.calculate_percentage_of_total(
            data=balances,
            value_field=annotation_name,
            percentage_field='porcentaje'
        )
    
    def get_grouped_statistics(
        self,
        filters: Dict[str, Any],
        group_field: str
    ) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas agrupadas por un campo específico
        
        Args:
            filters: Filtros a aplicar
            group_field: Campo por el que agrupar
            
        Returns:
            Lista con estadísticas por grupo
        """
        model = self.get_model()
        queryset = model.objects.filter(**filters)
        amount_field = self.get_amount_field()
        
        return self.stats_calculator.calculate_grouped_stats(
            queryset=queryset,
            group_field=group_field,
            value_field=amount_field
        )


class BaseReportServiceWithCategories(BaseReportService):
    """
    Clase base extendida para reportes con categorías
    
    Esta clase extiende BaseReportService añadiendo soporte para
    entidades que tienen categorías (gastos, compras, etc.)
    """
    
    @abstractmethod
    def get_category_field(self) -> str:
        """
        Retorna el nombre del campo de categoría
        
        Returns:
            Nombre del campo (ej: 'id_categoria__categoria')
        """
        pass
    
    def get_filter_fields(self) -> List[str]:
        """Añade categoria_id a los campos de filtro"""
        fields = super().get_filter_fields()
        fields.append('categoria_id')
        return fields
    
    def build_filters(self, categoria_id: Any = None, **kwargs) -> Dict[str, Any]:
        """
        Construye filtros incluyendo categoría
        
        Args:
            categoria_id: ID de categoría a filtrar
            **kwargs: Otros parámetros de filtro
            
        Returns:
            Diccionario con filtros validados
        """
        filters = super().build_filters(**kwargs)
        
        # Validar y añadir filtro de categoría si se proporciona
        validated_categoria = self.filter_builder.validate_id(categoria_id)
        if validated_categoria:
            filters['id_categoria_id'] = validated_categoria
        
        return filters
    
    def get_statistics_by_category(
        self,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas agrupadas por categoría
        
        Args:
            filters: Filtros a aplicar
            
        Returns:
            Lista con estadísticas por categoría
        """
        category_field = self.get_category_field()
        return self.get_grouped_statistics(filters, category_field)
