"""
Servicio para análisis de ventas

Análisis completo de ventas usando la arquitectura base reutilizable.
Incluye filtrado, agregación temporal, estadísticas, top clientes, etc.
"""
from .base_report_service import BaseReportService


class VentasAnalysisService(BaseReportService):
    """
    Servicio para análisis de ventas.

    Hereda de BaseReportService (sin categorías, ya que ventas no las tiene).

    Funcionalidad incluida por herencia:
    - Filtrado completo
    - Agregación temporal
    - Estadísticas completas
    - Formateo de períodos
    """

    def get_model(self):
        from ventas.models import Ventas
        return Ventas

    def get_date_field(self) -> str:
        return 'fecha_salida_manifiesto'

    def get_amount_field(self) -> str:
        return 'monto'

    def get_group_fields(self, periodo: str):
        base_fields = [
            'cliente__nombre',
            'producto__nombre',
            'sucursal_id__nombre'
        ]

        if periodo == 'diario':
            return base_fields + ['fecha_salida_manifiesto']
        elif periodo == 'semanal':
            return base_fields + ['semana']
        else:
            return base_fields

    def get_filter_fields(self):
        fields = super().get_filter_fields()
        fields.extend(['cliente_id', 'producto_id'])
        return fields

    def get_filter_options_config(self):
        return {
            'include_cuentas': True,
            'include_sucursales': True,
            'include_proveedores': False,
            'include_clientes': True,
        }

    def build_filters(self, cliente_id=None, producto_id=None, **kwargs):
        filters = super().build_filters(**kwargs)

        if cliente_id:
            validated = self.filter_builder.validate_id(cliente_id)
            if validated:
                filters['cliente_id'] = validated

        if producto_id:
            validated = self.filter_builder.validate_id(producto_id)
            if validated:
                filters['producto_id'] = validated

        return filters

    def get_ventas_por_cliente(self, filters):
        return self.get_grouped_statistics(
            filters=filters,
            group_field='cliente__nombre'
        )

    def get_ventas_por_producto(self, filters):
        return self.get_grouped_statistics(
            filters=filters,
            group_field='producto__nombre'
        )

    def get_ventas_por_agente(self, filters):
        return self.get_grouped_statistics(
            filters=filters,
            group_field='agente_id__nombre'
        )

    def get_top_clientes(self, filters, limit=10):
        stats_por_cliente = self.get_ventas_por_cliente(filters)
        return sorted(
            stats_por_cliente,
            key=lambda x: x['total'] if isinstance(x, dict) else x.total,
            reverse=True
        )[:limit]
