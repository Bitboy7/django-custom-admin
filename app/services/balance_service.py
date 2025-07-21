"""
Servicio para análisis de balances y gastos
"""
import numpy as np
from datetime import datetime
from django.db.models import Sum, Avg, Max, Min
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay

from gastos.models import Gastos, Cuenta


class BalanceAnalysisService:
    """Servicio para análisis de balances y gastos"""
    
    def __init__(self):
        self.months = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
    
    def get_filter_data(self):
        """Obtiene datos para los filtros"""
        available_years = Gastos.objects.dates('fecha', 'year')
        cuentas = Cuenta.objects.all()
        
        return {
            'available_years': available_years,
            'months': self.months,
            'cuentas': cuentas
        }
    
    def build_filters(self, cuenta_id, year, month, periodo, dia, fecha_inicio, fecha_fin):
        """Construye los filtros para la consulta con validación de tipos"""
        filters = {}
        
        # Validar y agregar filtro de año
        if year:
            try:
                year_int = int(year)
                filters['fecha__year'] = year_int
            except (ValueError, TypeError):
                # Si no se puede convertir, usar el año actual
                filters['fecha__year'] = datetime.now().year
        else:
            filters['fecha__year'] = datetime.now().year
        
        # Validar y agregar filtro de cuenta
        if cuenta_id:
            try:
                cuenta_int = int(cuenta_id)
                filters['id_cuenta_banco_id'] = cuenta_int
            except (ValueError, TypeError):
                pass  # No agregar filtro si no es válido
        
        # Validar y agregar filtro de mes
        if month:
            try:
                month_int = int(month)
                if 1 <= month_int <= 12:
                    filters['fecha__month'] = month_int
            except (ValueError, TypeError):
                pass  # No agregar filtro si no es válido
        
        # Filtros específicos por periodo
        if periodo == 'diario':
            if dia:
                filters['fecha'] = dia
            elif fecha_inicio and fecha_fin:
                filters['fecha__range'] = [fecha_inicio, fecha_fin]
        
        return filters
    
    def get_balances_by_period(self, filters, periodo):
        """Obtiene los balances agrupados por período"""
        base_values = [
            'id',
            'id_cuenta_banco__id', 
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_cuenta_banco__id_sucursal__nombre',
            'id_cat_gastos__nombre'
        ]
        
        if periodo == 'diario':
            balances = Gastos.objects.filter(**filters).values(
                *base_values, 'fecha'
            ).annotate(
                total_gastos=Sum('monto')
            ).order_by('id_cuenta_banco__id', 'fecha')
            
        elif periodo == 'semanal':
            balances = Gastos.objects.filter(**filters).annotate(
                semana=TruncWeek('fecha')
            ).values(
                *base_values, 'semana'
            ).annotate(
                total_gastos=Sum('monto')
            ).order_by('id_cuenta_banco__id', 'semana')
            
        elif periodo == 'mensual':
            balances = Gastos.objects.filter(**filters).annotate(
                mes=TruncMonth('fecha')
            ).values(
                *base_values, 'mes'
            ).annotate(
                total_gastos=Sum('monto')
            ).order_by('id_cuenta_banco__id', 'mes')
        else:
            balances = []
        
        return list(balances)
    
    def calculate_accumulated(self, balances):
        """Calcula el acumulado de los balances"""
        acumulado = 0
        for balance in balances:
            acumulado += balance['total_gastos']
            balance['acumulado'] = acumulado
        
        return balances
    
    def calculate_statistics(self, filters):
        """Calcula estadísticas de gastos"""
        queryset = Gastos.objects.filter(**filters)
        
        # Agregaciones básicas
        aggregations = queryset.aggregate(
            total=Sum('monto'),
            promedio=Avg('monto'),
            maximo=Max('monto'),
            minimo=Min('monto'),
            count=Count('id')
        )
        
        # Mediana (requiere numpy)
        gastos_list = list(queryset.values_list('monto', flat=True))
        mediana = np.median(gastos_list) if gastos_list else 0
        
        # Categorías de gasto máximo y mínimo
        categoria_maximo = None
        categoria_minimo = None
        
        if aggregations['maximo']:
            categoria_maximo = queryset.filter(
                monto=aggregations['maximo']
            ).values('id_cat_gastos__nombre').first()
        
        if aggregations['minimo']:
            categoria_minimo = queryset.filter(
                monto=aggregations['minimo']
            ).values('id_cat_gastos__nombre').first()
        
        return {
            'total_gastos': aggregations['total'] or 0,
            'promedio_gastos': aggregations['promedio'],
            'numero_transacciones': aggregations['count'],
            'gasto_maximo': aggregations['maximo'],
            'gasto_minimo': aggregations['minimo'],
            'gasto_mediano': mediana,
            'categoria_gasto_maximo': categoria_maximo['id_cat_gastos__nombre'] if categoria_maximo else None,
            'categoria_gasto_minimo': categoria_minimo['id_cat_gastos__nombre'] if categoria_minimo else None,
        }
    
    def process_request_parameters(self, request):
        """Procesa los parámetros de la request y limpia valores problemáticos"""
        # Obtener el año y limpiarlo de caracteres especiales
        year_param = request.GET.get('year', str(datetime.now().year))
        # Limpiar espacios no rompibles y otros caracteres especiales
        year_param = str(year_param).replace('\xa0', '').replace('\u00A0', '').strip()
        try:
            year = int(year_param)
        except (ValueError, TypeError):
            year = datetime.now().year
        
        # Obtener el mes y limpiarlo
        month_param = request.GET.get('month', '')
        month = ''
        if month_param:
            try:
                month_int = int(str(month_param).strip())
                if 1 <= month_int <= 12:
                    month = month_int
            except (ValueError, TypeError):
                month = ''
        
        # Obtener cuenta_id y limpiarlo
        cuenta_id_param = request.GET.get('cuenta_id', '')
        cuenta_id = ''
        if cuenta_id_param:
            try:
                cuenta_id = int(str(cuenta_id_param).strip())
            except (ValueError, TypeError):
                cuenta_id = ''
        
        return {
            'cuenta_id': cuenta_id,
            'year': year,
            'month': month,
            'periodo': request.GET.get('periodo', 'diario'),
            'dia': request.GET.get('dia', datetime.now().strftime('%Y-%m-%d')),
            'fecha_inicio': request.GET.get('fecha_inicio', ''),
            'fecha_fin': request.GET.get('fecha_fin', '')
        }
    
    def get_full_context(self, request):
        """Obtiene el contexto completo para la vista de balances"""
        # Procesar parámetros
        params = self.process_request_parameters(request)
        
        # Obtener datos de filtros
        filter_data = self.get_filter_data()
        
        # Construir filtros
        filters = self.build_filters(
            params['cuenta_id'], params['year'], params['month'],
            params['periodo'], params['dia'], params['fecha_inicio'], params['fecha_fin']
        )
        
        # Obtener balances
        balances = self.get_balances_by_period(filters, params['periodo'])
        balances = self.calculate_accumulated(balances)
        
        # Calcular estadísticas
        statistics = self.calculate_statistics(filters)
        
        # Combinar todo en el contexto
        context = {
            'balances': balances,
            **filter_data,
            **params,
            **statistics,
            'meses_rango': range(1, 13),
        }
        
        # Renombrar parámetros para mantener compatibilidad
        context.update({
            'selected_cuenta_id': params['cuenta_id'],
            'selected_year': params['year'],
            'selected_month': params['month'],
            'selected_periodo': params['periodo'],
            'selected_dia': params['dia'],
            'selected_fecha_inicio': params['fecha_inicio'],
            'selected_fecha_fin': params['fecha_fin'],
        })
        
        return context


# Agregar import faltante
from django.db.models import Count
