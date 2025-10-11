"""
Servicio para análisis de compras de fruta

Este servicio utiliza la arquitectura base modular para proporcionar
funcionalidad completa de reportes con código mínimo.
"""
from datetime import datetime
from django.db.models import Sum
from .base_report_service import BaseReportService


class ComprasAnalysisService(BaseReportService):
    """
    Servicio para análisis de compras de fruta
    
    Gracias a la herencia de BaseReportService, solo necesitamos
    implementar 4-5 métodos para tener toda la funcionalidad de:
    - Filtrado por año, mes, cuenta, productor
    - Agregación por período (diario, semanal, mensual)
    - Cálculo de estadísticas (sum, avg, max, min, mediana)
    - Valores acumulados
    - Y más...
    """
    
    # ==================== IMPLEMENTACIÓN DE MÉTODOS ABSTRACTOS ====================
    
    def get_model(self):
        """Retorna el modelo Compra"""
        from gastos.models import Compra
        return Compra
    
    def get_date_field(self) -> str:
        """Campo de fecha en Compra"""
        return 'fecha_compra'
    
    def get_amount_field(self) -> str:
        """Campo de monto en Compra"""
        return 'monto_total'
    
    def get_group_fields(self, periodo: str):
        """
        Campos de agrupación para compras
        
        Para Compras, típicamente agruparíamos por:
        - Categoría
        - Proveedor
        - Sucursal
        - Cuenta (si aplica)
        """
        """
        Campos de agrupación para compras
        
        Para Compras, agrupamos por:
        - Productor
        - Producto
        - Cuenta (si aplica)
        """
        base_fields = [
            'productor__nombre_completo',
            'producto__nombre',
            'cuenta__numero_cuenta'
        ]
        
        if periodo == 'diario':
            return base_fields + ['fecha_compra']
        elif periodo == 'semanal':
            return base_fields + ['semana']
        else:  # mensual
            return base_fields
    
    # ==================== CONFIGURACIÓN ESPECÍFICA ====================
    
    def get_filter_fields(self):
        """
        Campos de filtro para compras
        
        Añade productor_id y producto_id a los filtros estándar
        """
        fields = super().get_filter_fields()
        fields.extend(['productor_id', 'producto_id', 'tipo_pago'])
        return fields
    
    def get_filter_options_config(self):
        """
        Configuración de opciones de filtro para compras
        
        No incluye proveedores ni clientes (usamos productores)
        """
        return {
            'include_cuentas': True,
            'include_sucursales': False,  # Compras no tienen sucursal
            'include_proveedores': False,
            'include_clientes': False
        }
    
    def get_total_annotation_name(self) -> str:
        """Nombre de la anotación del total"""
        return 'total_compras'
    
    def should_use_default_year(self) -> bool:
        """Usar año actual por defecto"""
        return True
    
    # ==================== MÉTODOS PERSONALIZADOS ====================
    
    def get_filter_data(self):
        """
        Obtiene datos específicos para filtros de compras
        
        Override para añadir productores, productos, sucursales
        """
        from gastos.models import Compra, Cuenta
        from catalogo.models import Productor, Producto, Sucursal
        
        data = {
            'available_years': Compra.objects.dates('fecha_compra', 'year'),
            'months': self.period_formatter.MONTHS_ES,
            'cuentas': Cuenta.objects.all(),
            'productores': Productor.objects.all(),
            'productos': Producto.objects.all(),
            'sucursales': Sucursal.objects.all(),
            'tipos_pago': Compra.TipoPago.choices
        }
        
        return data
    
    def build_filters(
        self,
        cuenta_id=None,
        productor_id=None,
        producto_id=None,
        tipo_pago=None,
        sucursal_id=None,
        year=None,
        month=None,
        selected_months=None,
        periodo='mensual',
        dia=None,
        fecha_inicio=None,
        fecha_fin=None,
        **kwargs
    ):
        """
        Construye filtros específicos para Compra
        
        Override completo porque Compra usa nombres de campo diferentes:
        - fecha_compra (no 'fecha')
        - cuenta_id (no 'id_cuenta_banco_id')
        - productor_id (campo propio de Compra)
        - Sucursal se filtra a través de productor__id_sucursal_id
        
        Args:
            cuenta_id: ID de la cuenta bancaria
            productor_id: ID del productor
            producto_id: ID del producto
            tipo_pago: Tipo de pago
            sucursal_id: ID de la sucursal (filtra por productor__id_sucursal_id)
            year: Año a filtrar
            month: Mes a filtrar
            selected_months: Lista de meses seleccionados
            periodo: Tipo de período ('diario', 'semanal', 'mensual')
            dia: Día específico
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha fin
            **kwargs: Otros parámetros
        """
        filters = {}
        
        # Filtro de año (usa fecha_compra)
        validated_year = self.filter_builder.validate_year(
            year, 
            default=datetime.now().year if self.should_use_default_year() else None
        )
        if validated_year:
            filters['fecha_compra__year'] = validated_year
        
        # Filtro de cuenta bancaria (usa cuenta_id, no id_cuenta_banco_id)
        validated_cuenta = self.filter_builder.validate_id(cuenta_id)
        if validated_cuenta:
            filters['cuenta_id'] = validated_cuenta
        
        # Filtro de sucursal (a través de productor__id_sucursal_id)
        validated_sucursal = self.filter_builder.validate_id(sucursal_id)
        if validated_sucursal:
            filters['productor__id_sucursal_id'] = validated_sucursal
        
        # Filtros de mes (usa fecha_compra)
        if selected_months and isinstance(selected_months, list) and len(selected_months) > 0:
            valid_months = [
                m for m in selected_months 
                if self.filter_builder.validate_month(m) is not None
            ]
            if valid_months:
                filters['fecha_compra__month__in'] = valid_months
        elif month:
            validated_month = self.filter_builder.validate_month(month)
            if validated_month:
                filters['fecha_compra__month'] = validated_month
        
        # Filtros de fecha específicos (usa fecha_compra)
        if periodo == 'diario':
            if dia:
                filters['fecha_compra'] = dia
            elif fecha_inicio and fecha_fin:
                filters['fecha_compra__range'] = [fecha_inicio, fecha_fin]
        
        # Filtro de productor
        validated_productor = self.filter_builder.validate_id(productor_id)
        if validated_productor:
            filters['productor_id'] = validated_productor
        
        # Filtro de producto
        validated_producto = self.filter_builder.validate_id(producto_id)
        if validated_producto:
            filters['producto_id'] = validated_producto
        
        # Filtro de tipo de pago
        if tipo_pago:
            filters['tipo_pago'] = tipo_pago
        
        return filters
    
    def get_balances_by_period(self, filters, periodo='mensual'):
        """
        Override para añadir cantidad_total y precio_promedio a los balances
        
        Args:
            filters: Diccionario de filtros
            periodo: Tipo de periodo ('diario', 'semanal', 'mensual')
            
        Returns:
            QuerySet con periodo, group_fields, total_compras, cantidad_total, 
            precio_promedio y acumulado
        """
        from django.db.models import Sum, Avg
        
        # Obtener balances base del padre
        balances = super().get_balances_by_period(filters, periodo)
        
        # Añadir anotaciones adicionales específicas de compras
        balances = balances.annotate(
            cantidad_total=Sum('cantidad'),
            precio_promedio=Avg('precio_unitario')
        )
        
        return balances
    
    def get_compras_por_productor(self, filters):
        """
        Obtiene estadísticas de compras agrupadas por productor
        
        Útil para análisis de proveedores principales
        """
        return self.get_grouped_statistics(
            filters=filters,
            group_field='productor__nombre_completo'
        )
    
    def get_compras_por_producto(self, filters):
        """
        Obtiene estadísticas de compras agrupadas por producto
        
        Útil para análisis de productos más comprados
        """
        return self.get_grouped_statistics(
            filters=filters,
            group_field='producto__nombre'
        )
    
    def get_compras_por_tipo_pago(self, filters):
        """
        Obtiene estadísticas de compras agrupadas por tipo de pago
        
        Útil para análisis de métodos de pago
        """
        return self.get_grouped_statistics(
            filters=filters,
            group_field='tipo_pago'
        )
    
    def calculate_statistics(self, filters):
        """
        Override para añadir estadísticas específicas de compras
        
        Añade información sobre productor y producto con compra máxima/mínima
        """
        from gastos.models import Compra
        
        # Usar estadísticas base
        stats = super().calculate_statistics(filters)
        
        # Añadir estadísticas específicas de compras
        queryset = Compra.objects.filter(**filters)
        
        productor_maximo = None
        producto_maximo = None
        
        if stats['maximo'] > 0:
            compra_max = queryset.filter(monto_total=stats['maximo']).first()
            if compra_max:
                productor_maximo = compra_max.productor.nombre_completo
                producto_maximo = compra_max.producto.nombre
        
        # Renombrar para claridad
        return {
            'total_compras': stats['total'],
            'promedio_compras': stats['promedio'],
            'numero_compras': stats['cantidad'],
            'compra_maxima': stats['maximo'],
            'compra_minima': stats['minimo'],
            'compra_mediana': stats.get('mediana', 0),
            'productor_compra_maxima': productor_maximo,
            'producto_compra_maxima': producto_maximo,
        }
    
    def process_request_parameters(self, request):
        """
        Procesa parámetros del request para compras
        
        Similar a balance_service pero adaptado para compras
        """
        # Obtener el año
        year_param = request.GET.get('year', str(datetime.now().year))
        year_param = str(year_param).replace('\xa0', '').replace('\u00A0', '').strip()
        try:
            year = int(year_param)
        except (ValueError, TypeError):
            year = datetime.now().year
        
        # Extraer otros parámetros
        params = {
            'year': year,
            'month': request.GET.get('month', ''),
            'cuenta_id': request.GET.get('cuenta_id', ''),
            'sucursal_id': request.GET.get('sucursal_id', ''),
            'productor_id': request.GET.get('productor_id', ''),
            'producto_id': request.GET.get('producto_id', ''),
            'tipo_pago': request.GET.get('tipo_pago', ''),
            'periodo': request.GET.get('periodo', 'diario'),
            'dia': request.GET.get('dia', datetime.now().strftime('%Y-%m-%d')),
            'fecha_inicio': request.GET.get('fecha_inicio', ''),
            'fecha_fin': request.GET.get('fecha_fin', '')
        }
        
        # Manejar múltiples meses
        months_param = request.GET.get('months', '')
        selected_months = []
        if months_param and months_param.strip():
            try:
                month_values = months_param.split(',')
                for m in month_values:
                    m_clean = m.strip()
                    if m_clean:
                        month_int = int(m_clean)
                        if 1 <= month_int <= 12:
                            selected_months.append(month_int)
            except (ValueError, TypeError):
                pass
        
        params['selected_months'] = selected_months
        
        return params
    
    def get_full_context(self, request):
        """
        Obtiene el contexto completo para la vista de compras
        
        Combina toda la funcionalidad heredada con procesamiento específico
        """
        # Procesar parámetros
        params = self.process_request_parameters(request)
        
        # Obtener datos de filtros
        filter_data = self.get_filter_data()
        
        # Construir filtros
        filters = self.build_filters(
            cuenta_id=params['cuenta_id'],
            sucursal_id=params['sucursal_id'],
            productor_id=params['productor_id'],
            producto_id=params['producto_id'],
            tipo_pago=params['tipo_pago'],
            year=params['year'],
            month=params['month'],
            selected_months=params.get('selected_months', []),
            periodo=params['periodo'],
            dia=params['dia'],
            fecha_inicio=params['fecha_inicio'],
            fecha_fin=params['fecha_fin']
        )
        
        # Obtener compras por período
        compras = self.get_balances_by_period(filters, params['periodo'])
        
        # Calcular acumulados
        compras = self.calculate_accumulated(compras)
        
        # Calcular estadísticas
        statistics = self.calculate_statistics(filters)
        
        # Análisis adicionales
        por_productor = self.get_compras_por_productor(filters)
        por_producto = self.get_compras_por_producto(filters)
        por_tipo_pago = self.get_compras_por_tipo_pago(filters)
        
        # Combinar contexto
        context = {
            'compras': compras,
            'por_productor': por_productor[:10] if por_productor else [],  # Top 10
            'por_producto': por_producto[:10] if por_producto else [],  # Top 10
            'por_tipo_pago': por_tipo_pago,
            **filter_data,
            **params,
            **statistics,
            'meses_rango': range(1, 13),
        }
        
        # Renombrar para templates
        context.update({
            'selected_cuenta_id': params['cuenta_id'],
            'selected_sucursal_id': params['sucursal_id'],
            'selected_productor_id': params['productor_id'],
            'selected_producto_id': params['producto_id'],
            'selected_tipo_pago': params['tipo_pago'],
            'selected_year': params['year'],
            'selected_month': params['month'],
            'selected_periodo': params['periodo'],
            'selected_dia': params['dia'],
            'selected_fecha_inicio': params['fecha_inicio'],
            'selected_fecha_fin': params['fecha_fin'],
        })
        
        return context




