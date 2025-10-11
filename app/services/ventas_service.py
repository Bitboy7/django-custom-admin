"""
Servicio para análisis de ventas

Otro ejemplo de reutilización de la arquitectura base.
Muestra cómo adaptar el servicio base para ventas.
"""
from .base_report_service import BaseReportService


class VentasAnalysisService(BaseReportService):
    """
    Servicio para análisis de ventas
    
    NOTA: Este es un ejemplo. Asume que existe un modelo Ventas.
    
    A diferencia de compras y gastos, ventas podría NO tener categorías,
    por lo que hereda de BaseReportService en lugar de BaseReportServiceWithCategories.
    
    Funcionalidad incluida por herencia:
    - Filtrado completo
    - Agregación temporal
    - Estadísticas completas
    - Formateo de períodos
    - Y más...
    """
    
    # ==================== IMPLEMENTACIÓN DE MÉTODOS ABSTRACTOS ====================
    
    def get_model(self):
        """
        Retorna el modelo Ventas
        
        NOTA: Descomentar cuando exista el modelo
        """
        # from ventas.models import Ventas
        # return Ventas
        raise NotImplementedError("Modelo Ventas no implementado aún")
    
    def get_date_field(self) -> str:
        """Campo de fecha en Ventas"""
        return 'fecha_venta'  # o 'fecha' según el modelo
    
    def get_amount_field(self) -> str:
        """Campo de monto en Ventas"""
        return 'total'  # o 'monto_total' según el modelo
    
    def get_group_fields(self, periodo: str):
        """
        Campos de agrupación para ventas
        
        Para Ventas, típicamente agruparíamos por:
        - Cliente
        - Producto/Servicio
        - Sucursal
        - Vendedor (si aplica)
        """
        base_fields = [
            'id_cliente__nombre',
            'id_producto__nombre',  # o descripción del servicio
            'id_sucursal__nombre'
        ]
        
        if periodo == 'diario':
            return base_fields + ['fecha_venta']
        elif periodo == 'semanal':
            return base_fields + ['semana']
        else:  # mensual
            return base_fields
    
    # ==================== CONFIGURACIÓN ESPECÍFICA ====================
    
    def get_filter_fields(self):
        """
        Campos de filtro para ventas
        
        Añade cliente_id y producto_id
        """
        fields = super().get_filter_fields()
        fields.extend(['cliente_id', 'producto_id', 'vendedor_id'])
        return fields
    
    def get_filter_options_config(self):
        """
        Configuración de opciones de filtro para ventas
        
        Incluye clientes en lugar de proveedores
        """
        return {
            'include_cuentas': True,
            'include_sucursales': True,
            'include_proveedores': False,
            'include_clientes': True  # Específico para ventas
        }
    
    def get_total_annotation_name(self) -> str:
        """Nombre de la anotación del total"""
        return 'total_ventas'
    
    def build_filters(self, cliente_id=None, producto_id=None, vendedor_id=None, **kwargs):
        """
        Override para añadir filtros específicos de ventas
        
        Args:
            cliente_id: ID del cliente
            producto_id: ID del producto/servicio
            vendedor_id: ID del vendedor
            **kwargs: Otros filtros estándar
        """
        filters = super().build_filters(**kwargs)
        
        # Añadir filtros específicos de ventas
        if cliente_id:
            validated_cliente = self.filter_builder.validate_id(cliente_id)
            if validated_cliente:
                filters['id_cliente_id'] = validated_cliente
        
        if producto_id:
            validated_producto = self.filter_builder.validate_id(producto_id)
            if validated_producto:
                filters['id_producto_id'] = validated_producto
        
        if vendedor_id:
            validated_vendedor = self.filter_builder.validate_id(vendedor_id)
            if validated_vendedor:
                filters['id_vendedor_id'] = validated_vendedor
        
        return filters
    
    # ==================== MÉTODOS PERSONALIZADOS ====================
    
    def get_ventas_por_cliente(self, filters):
        """
        Obtiene estadísticas de ventas agrupadas por cliente
        
        Útil para análisis de mejores clientes
        """
        return self.get_grouped_statistics(
            filters=filters,
            group_field='id_cliente__nombre'
        )
    
    def get_ventas_por_producto(self, filters):
        """
        Obtiene estadísticas de ventas agrupadas por producto
        
        Útil para análisis de productos más vendidos
        """
        return self.get_grouped_statistics(
            filters=filters,
            group_field='id_producto__nombre'
        )
    
    def get_ventas_por_vendedor(self, filters):
        """
        Obtiene estadísticas de ventas agrupadas por vendedor
        
        Útil para comisiones y evaluación de desempeño
        """
        return self.get_grouped_statistics(
            filters=filters,
            group_field='id_vendedor__nombre'
        )
    
    def get_ventas_con_utilidad(self, filters):
        """
        Calcula ventas con margen de utilidad
        
        Ejemplo de cálculo personalizado específico de ventas
        """
        from django.db.models import F, ExpressionWrapper, DecimalField
        
        model = self.get_model()
        queryset = model.objects.filter(**filters)
        
        # Calcular utilidad (asumiendo que existe campo 'costo')
        return queryset.annotate(
            utilidad=ExpressionWrapper(
                F('total') - F('costo'),
                output_field=DecimalField()
            ),
            porcentaje_utilidad=ExpressionWrapper(
                (F('total') - F('costo')) * 100 / F('total'),
                output_field=DecimalField()
            )
        )
    
    def get_top_clientes(self, filters, limit=10):
        """
        Obtiene los N mejores clientes por volumen de ventas
        
        Args:
            filters: Filtros a aplicar
            limit: Número de clientes a retornar
        """
        stats_por_cliente = self.get_ventas_por_cliente(filters)
        return sorted(
            stats_por_cliente, 
            key=lambda x: x['total'], 
            reverse=True
        )[:limit]


# Ejemplo de uso:
"""
# En una vista de Django:

from app.services.ventas_service import VentasAnalysisService

def ventas_report_view(request):
    service = VentasAnalysisService()
    
    # Obtener datos de filtros
    filter_data = service.get_filter_data()
    
    # Extraer parámetros del request
    params = service.extract_filters_from_request(request)
    
    # Construir filtros (con parámetros específicos de ventas)
    filters = service.build_filters(
        cliente_id=request.GET.get('cliente_id'),
        producto_id=request.GET.get('producto_id'),
        vendedor_id=request.GET.get('vendedor_id'),
        **params
    )
    
    # Obtener ventas por período
    ventas = service.get_balances_by_period(filters, params.get('periodo', 'mensual'))
    
    # Calcular acumulados
    ventas = service.calculate_accumulated(ventas)
    
    # Estadísticas generales
    stats = service.calculate_statistics(filters)
    
    # Análisis por cliente
    top_clientes = service.get_top_clientes(filters, limit=10)
    
    # Análisis por producto
    por_producto = service.get_ventas_por_producto(filters)
    
    # Análisis por vendedor (para comisiones)
    por_vendedor = service.get_ventas_por_vendedor(filters)
    
    context = {
        'ventas': ventas,
        'statistics': stats,
        'top_clientes': top_clientes,
        'por_producto': por_producto,
        'por_vendedor': por_vendedor,
        **filter_data
    }
    
    return render(request, 'ventas/report.html', context)

# Con ~80 líneas de código personalizado + la base reutilizable,
# tenemos un sistema completo de análisis de ventas con:
# - Filtrado completo
# - Múltiples agrupaciones
# - Estadísticas avanzadas
# - Top N análisis
# - Cálculos de utilidad
# - Y más...
"""
