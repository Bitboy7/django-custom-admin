"""
Servicio de reportes para Capital e Inversiones

Este servicio hereda de BaseReportService y proporciona funcionalidad
específica para generar reportes acumulados de inversiones por:
- Sucursal
- Categoría
- Día, Semana, Mes, Año
- Tipo de movimiento (Entradas/Salidas)
"""

from app.services.base_report_service import BaseReportService
from capital_inversiones.models import Inversion
from django.db.models import Sum, Q, F, Value, CharField, When, Case, Count, DecimalField
from django.db.models.functions import Concat
from djmoney.models.fields import MoneyField
from typing import Dict, List
from django.db import models


class InversionesReportService(BaseReportService):
    """
    Servicio de reportes para inversiones y capital
    
    Hereda toda la funcionalidad de BaseReportService y la personaliza
    para el modelo de Inversion.
    """
    
    def get_model(self):
        """Retorna el modelo Inversion"""
        return Inversion
    
    def get_date_field(self) -> str:
        """Campo de fecha para filtros"""
        return 'fecha'
    
    def get_amount_field(self) -> str:
        """Campo de monto para agregaciones"""
        return 'monto'
    
    def get_group_fields(self, periodo: str) -> List[str]:
        """
        Campos de agrupación según el período
        
        Args:
            periodo: 'diario', 'semanal', 'mensual', 'anual'
        
        Returns:
            Lista de campos para agrupar
        """
        base_fields = [
            'id_sucursal__nombre',
            'id_cat_inversion__nombre',
            'tipo_movimiento'
        ]
        
        # Agregar agrupación temporal según período
        if periodo == 'diario':
            return base_fields + ['fecha']
        elif periodo == 'semanal':
            return base_fields + ['fecha__week', 'fecha__year']
        elif periodo == 'mensual':
            return base_fields + ['fecha__month', 'fecha__year']
        elif periodo == 'anual':
            return base_fields + ['fecha__year']
        
        return base_fields
    
    def get_default_order_by(self) -> List[str]:
        """Orden por defecto de los resultados"""
        return ['-fecha', 'id_sucursal__nombre']
    
    # ==================== MÉTODOS ADICIONALES ESPECÍFICOS ====================
    
    def get_balance_por_sucursal(self, fecha_inicio=None, fecha_fin=None):
        """
        Calcula el balance (entradas - salidas) por sucursal
        
        Args:
            fecha_inicio: Fecha inicial del período
            fecha_fin: Fecha final del período
        
        Returns:
            QuerySet con balance por sucursal
        """
        queryset = self.get_model().objects.all()
        
        # Aplicar filtros de fecha
        filters = self.filter_builder.build_date_filters(
            self.get_date_field(),
            fecha_inicio,
            fecha_fin
        )
        if filters:
            queryset = queryset.filter(filters)
        
        # Calcular totales por tipo de movimiento
        return queryset.values('id_sucursal__nombre').annotate(
            total_entradas=Sum(
                'monto',
                filter=Q(tipo_movimiento='ENTRADA')
            ),
            total_salidas=Sum(
                'monto',
                filter=Q(tipo_movimiento='SALIDA')
            ),
            balance=Sum(
                Case(
                    When(tipo_movimiento='ENTRADA', then=F('monto')),
                    When(tipo_movimiento='SALIDA', then=F('monto') * -1),
                    default=Value(0),
                    output_field=DecimalField()
                )
            ),
            cantidad_movimientos=Count('id')
        ).order_by('id_sucursal__nombre')
    
    def get_balance_por_categoria(self, fecha_inicio=None, fecha_fin=None):
        """
        Calcula el balance (entradas - salidas) por categoría
        
        Args:
            fecha_inicio: Fecha inicial del período
            fecha_fin: Fecha final del período
        
        Returns:
            QuerySet con balance por categoría
        """
        queryset = self.get_model().objects.all()
        
        # Aplicar filtros de fecha
        filters = self.filter_builder.build_date_filters(
            self.get_date_field(),
            fecha_inicio,
            fecha_fin
        )
        if filters:
            queryset = queryset.filter(filters)
        
        # Calcular totales por tipo de movimiento
        return queryset.values('id_cat_inversion__nombre').annotate(
            total_entradas=Sum(
                'monto',
                filter=Q(tipo_movimiento='ENTRADA')
            ),
            total_salidas=Sum(
                'monto',
                filter=Q(tipo_movimiento='SALIDA')
            ),
            balance=Sum(
                Case(
                    When(tipo_movimiento='ENTRADA', then=F('monto')),
                    When(tipo_movimiento='SALIDA', then=F('monto') * -1),
                    default=Value(0),
                    output_field=DecimalField()
                )
            ),
            cantidad_movimientos=Count('id')
        ).order_by('-balance')
    
    def get_inversiones_con_rendimientos(self, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene inversiones (solo salidas) con sus rendimientos acumulados
        
        Args:
            fecha_inicio: Fecha inicial del período
            fecha_fin: Fecha final del período
        
        Returns:
            QuerySet con inversiones y rendimientos
        """
        from capital_inversiones.models import RendimientoInversion
        from django.db.models import Count, Sum as DjSum
        
        queryset = self.get_model().objects.filter(tipo_movimiento='SALIDA')
        
        # Aplicar filtros de fecha
        filters = self.filter_builder.build_date_filters(
            self.get_date_field(),
            fecha_inicio,
            fecha_fin
        )
        if filters:
            queryset = queryset.filter(filters)
        
        # Anotar con información de rendimientos (sin calcular ROI en la DB)
        return queryset.annotate(
            total_rendimientos=DjSum('rendimientos__monto_rendimiento'),
            cantidad_rendimientos=Count('rendimientos')
        ).order_by('-fecha')
    
    def get_resumen_general(self, fecha_inicio=None, fecha_fin=None):
        """
        Genera un resumen general de inversiones y capital
        
        Args:
            fecha_inicio: Fecha inicial del período
            fecha_fin: Fecha final del período
        
        Returns:
            Diccionario con estadísticas generales
        """
        from django.db.models import Count
        
        queryset = self.get_model().objects.all()
        
        # Aplicar filtros de fecha
        filters = self.filter_builder.build_date_filters(
            self.get_date_field(),
            fecha_inicio,
            fecha_fin
        )
        if filters:
            queryset = queryset.filter(filters)
        
        # Calcular totales
        totales = queryset.aggregate(
            total_entradas=Sum('monto', filter=Q(tipo_movimiento='ENTRADA')),
            total_salidas=Sum('monto', filter=Q(tipo_movimiento='SALIDA')),
            cantidad_entradas=Count('id', filter=Q(tipo_movimiento='ENTRADA')),
            cantidad_salidas=Count('id', filter=Q(tipo_movimiento='SALIDA'))
        )
        
        # Calcular balance
        entrada = totales['total_entradas'] or 0
        salida = totales['total_salidas'] or 0
        
        return {
            'total_entradas': entrada,
            'total_salidas': salida,
            'balance': entrada - salida,
            'cantidad_entradas': totales['cantidad_entradas'],
            'cantidad_salidas': totales['cantidad_salidas'],
            'total_movimientos': totales['cantidad_entradas'] + totales['cantidad_salidas']
        }
