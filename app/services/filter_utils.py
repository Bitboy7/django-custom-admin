"""
Utilidades para manejo de filtros en reportes

Este módulo proporciona funciones reutilizables para construir filtros
de consulta a partir de parámetros de request en diferentes módulos.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any


class FilterBuilder:
    """Constructor de filtros reutilizable para diferentes modelos"""
    
    @staticmethod
    def validate_year(year: Any, default: Optional[int] = None) -> Optional[int]:
        """
        Valida y convierte un año a entero
        
        Args:
            year: Valor a validar (puede ser string, int o None)
            default: Valor por defecto si year es inválido (None o año actual)
            
        Returns:
            Año validado como entero o None
        """
        if not year:
            return default if default else datetime.now().year
            
        try:
            year_int = int(year)
            # Validar rango razonable de años
            current_year = datetime.now().year
            if 2000 <= year_int <= current_year + 10:
                return year_int
            return default if default else current_year
        except (ValueError, TypeError):
            return default if default else datetime.now().year
    
    @staticmethod
    def validate_month(month: Any) -> Optional[int]:
        """
        Valida y convierte un mes a entero
        
        Args:
            month: Valor a validar (puede ser string, int o None)
            
        Returns:
            Mes validado como entero entre 1-12 o None
        """
        if not month:
            return None
            
        try:
            month_int = int(month)
            if 1 <= month_int <= 12:
                return month_int
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_id(value: Any) -> Optional[int]:
        """
        Valida y convierte un ID a entero
        
        Args:
            value: Valor a validar (puede ser string, int o None)
            
        Returns:
            ID validado como entero o None
        """
        if not value:
            return None
            
        try:
            id_int = int(value)
            if id_int > 0:
                return id_int
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def build_date_filters(
        periodo: str,
        dia: Optional[Any] = None,
        fecha_inicio: Optional[Any] = None,
        fecha_fin: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Construye filtros de fecha según el período
        
        Args:
            periodo: Tipo de período ('diario', 'semanal', 'mensual')
            dia: Día específico para período diario
            fecha_inicio: Fecha de inicio para rango
            fecha_fin: Fecha fin para rango
            
        Returns:
            Diccionario con filtros de fecha
        """
        filters = {}
        
        if periodo == 'diario':
            if dia:
                filters['fecha'] = dia
            elif fecha_inicio and fecha_fin:
                filters['fecha__range'] = [fecha_inicio, fecha_fin]
        
        return filters
    
    @staticmethod
    def build_standard_filters(
        year: Any = None,
        month: Any = None,
        selected_months: Optional[List[int]] = None,
        cuenta_id: Any = None,
        sucursal_id: Any = None,
        proveedor_id: Any = None,
        cliente_id: Any = None,
        periodo: str = 'mensual',
        dia: Any = None,
        fecha_inicio: Any = None,
        fecha_fin: Any = None,
        use_default_year: bool = True
    ) -> Dict[str, Any]:
        """
        Construye un diccionario de filtros estándar para reportes
        
        Args:
            year: Año a filtrar
            month: Mes a filtrar
            selected_months: Lista de meses seleccionados
            cuenta_id: ID de cuenta bancaria
            sucursal_id: ID de sucursal
            proveedor_id: ID de proveedor
            cliente_id: ID de cliente
            periodo: Tipo de período
            dia: Día específico
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha fin
            use_default_year: Si debe usar año actual por defecto
            
        Returns:
            Diccionario con filtros validados
        """
        filters = {}
        
        # Filtro de año
        validated_year = FilterBuilder.validate_year(
            year, 
            default=datetime.now().year if use_default_year else None
        )
        if validated_year:
            filters['fecha__year'] = validated_year
        
        # Filtro de cuenta bancaria
        validated_cuenta = FilterBuilder.validate_id(cuenta_id)
        if validated_cuenta:
            filters['id_cuenta_banco_id'] = validated_cuenta
        
        # Filtro de sucursal
        validated_sucursal = FilterBuilder.validate_id(sucursal_id)
        if validated_sucursal:
            filters['id_sucursal_id'] = validated_sucursal
        
        # Filtro de proveedor (para compras)
        validated_proveedor = FilterBuilder.validate_id(proveedor_id)
        if validated_proveedor:
            filters['id_proveedor_id'] = validated_proveedor
        
        # Filtro de cliente (para ventas)
        validated_cliente = FilterBuilder.validate_id(cliente_id)
        if validated_cliente:
            filters['id_cliente_id'] = validated_cliente
        
        # Filtros de mes
        if selected_months and isinstance(selected_months, list) and len(selected_months) > 0:
            # Validar cada mes de la lista
            valid_months = [
                m for m in selected_months 
                if FilterBuilder.validate_month(m) is not None
            ]
            if valid_months:
                filters['fecha__month__in'] = valid_months
        elif month:
            validated_month = FilterBuilder.validate_month(month)
            if validated_month:
                filters['fecha__month'] = validated_month
        
        # Filtros de fecha específicos por período
        date_filters = FilterBuilder.build_date_filters(
            periodo, dia, fecha_inicio, fecha_fin
        )
        filters.update(date_filters)
        
        return filters
    
    @staticmethod
    def extract_filters_from_request(request, filter_fields: Optional[List[str]] = None):
        """
        Extrae filtros desde un objeto request de Django
        
        Args:
            request: Objeto HttpRequest de Django
            filter_fields: Lista de campos a extraer (None = extraer todos los estándar)
            
        Returns:
            Diccionario con los parámetros extraídos
        """
        # Campos estándar que se pueden filtrar
        standard_fields = [
            'cuenta_id', 'sucursal_id', 'proveedor_id', 'cliente_id',
            'year', 'month', 'selected_months', 'periodo',
            'dia', 'fecha_inicio', 'fecha_fin'
        ]
        
        # Si no se especifican campos, usar todos los estándar
        if filter_fields is None:
            filter_fields = standard_fields
        
        extracted = {}
        
        for field in filter_fields:
            # Manejar selected_months como caso especial (puede ser una lista)
            if field == 'selected_months':
                value = request.GET.getlist('selected_months[]', [])
                if value:
                    extracted[field] = [int(m) for m in value if m.isdigit()]
            else:
                value = request.GET.get(field)
                if value:
                    extracted[field] = value
        
        return extracted


class FilterOptionsProvider:
    """Proveedor de opciones para filtros (dropdowns, etc.)"""
    
    @staticmethod
    def get_years_from_model(model, date_field: str = 'fecha'):
        """
        Obtiene los años disponibles desde un modelo
        
        Args:
            model: Modelo de Django
            date_field: Nombre del campo de fecha
            
        Returns:
            QuerySet con los años disponibles
        """
        return model.objects.dates(date_field, 'year')
    
    @staticmethod
    def get_months_list():
        """
        Obtiene la lista de meses en español
        
        Returns:
            Lista de nombres de meses
        """
        return [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
    
    @staticmethod
    def get_filter_options(
        model,
        include_cuentas: bool = False,
        include_sucursales: bool = False,
        include_proveedores: bool = False,
        include_clientes: bool = False,
        date_field: str = 'fecha'
    ) -> Dict[str, Any]:
        """
        Obtiene opciones para filtros de manera configurable
        
        Args:
            model: Modelo principal del que obtener años
            include_cuentas: Si incluir cuentas bancarias
            include_sucursales: Si incluir sucursales
            include_proveedores: Si incluir proveedores
            include_clientes: Si incluir clientes
            date_field: Campo de fecha para obtener años
            
        Returns:
            Diccionario con las opciones de filtrado
        """
        from catalogo.models import Sucursal
        from gastos.models import Cuenta
        
        options = {
            'available_years': FilterOptionsProvider.get_years_from_model(model, date_field),
            'months': FilterOptionsProvider.get_months_list()
        }
        
        if include_cuentas:
            options['cuentas'] = Cuenta.objects.all()
        
        if include_sucursales:
            options['sucursales'] = Sucursal.objects.all()
        
        if include_proveedores:
            # Importar aquí para evitar dependencias circulares
            try:
                from catalogo.models import Proveedor
                options['proveedores'] = Proveedor.objects.all()
            except ImportError:
                options['proveedores'] = []
        
        if include_clientes:
            # Importar aquí para evitar dependencias circulares
            try:
                from catalogo.models import Cliente
                options['clientes'] = Cliente.objects.all()
            except ImportError:
                options['clientes'] = []
        
        return options
