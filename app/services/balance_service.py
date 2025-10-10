"""
Servicio para análisis de balances y gastos
"""
import numpy as np
from datetime import datetime
from django.db.models import Sum, Avg, Max, Min
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay

from gastos.models import Gastos, Cuenta
from catalogo.models import Sucursal


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
        sucursales = Sucursal.objects.all()
        
        return {
            'available_years': available_years,
            'months': self.months,
            'cuentas': cuentas,
            'sucursales': sucursales
        }
    
    def build_filters(self, cuenta_id, year, month, selected_months, periodo, dia, fecha_inicio, fecha_fin, sucursal_id):
        """Construye los filtros para la consulta con validación de tipos"""
        filters = {}
        # Validar y agregar filtro de año
        if year:
            try:
                year_int = int(year)
                filters['fecha__year'] = year_int
            except (ValueError, TypeError):
                filters['fecha__year'] = datetime.now().year
        else:
            filters['fecha__year'] = datetime.now().year

        # Validar y agregar filtro de cuenta
        if cuenta_id:
            try:
                cuenta_int = int(cuenta_id)
                filters['id_cuenta_banco_id'] = cuenta_int
            except (ValueError, TypeError):
                pass

        # Validar y agregar filtro de sucursal
        if sucursal_id:
            try:
                sucursal_int = int(sucursal_id)
                filters['id_sucursal_id'] = sucursal_int
            except (ValueError, TypeError):
                pass

        # Filtrar por múltiples meses si existen, si no por uno solo
        if selected_months and isinstance(selected_months, list) and len(selected_months) > 0:
            filters['fecha__month__in'] = selected_months
        elif month:
            try:
                month_int = int(month)
                if 1 <= month_int <= 12:
                    filters['fecha__month'] = month_int
            except (ValueError, TypeError):
                pass

        # Filtros específicos por periodo
        if periodo == 'diario':
            if dia:
                filters['fecha'] = dia
            elif fecha_inicio and fecha_fin:
                filters['fecha__range'] = [fecha_inicio, fecha_fin]

        return filters
    
    def get_balances_by_period(self, filters, periodo):
        """Obtiene los balances agrupados por período, categoría y cuenta"""
        
        if periodo == 'diario':
            # Para período diario, agrupamos por categoría, cuenta y fecha
            balances = Gastos.objects.filter(**filters).values(
                'id_cat_gastos__nombre', 
                'id_cuenta_banco__id',
                'id_cuenta_banco__numero_cuenta',
                'id_cuenta_banco__id_banco__nombre',
                'id_sucursal__nombre',  # Sucursal del GASTO, no de la cuenta
                'fecha'
            ).annotate(
                total_gastos=Sum('monto')
            ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta', 'fecha')
            
        elif periodo == 'semanal':
            balances = Gastos.objects.filter(**filters).annotate(
                semana=TruncWeek('fecha')
            ).values(
                'id_cat_gastos__nombre',
                'id_cuenta_banco__id',
                'id_cuenta_banco__numero_cuenta',
                'id_cuenta_banco__id_banco__nombre',
                'id_sucursal__nombre',  # Sucursal del GASTO, no de la cuenta
                'semana'
            ).annotate(
                total_gastos=Sum('monto')
            ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta', 'semana')
            
        elif periodo == 'mensual':
            # Para mensual, agrupamos por categoría y cuenta
            balances = Gastos.objects.filter(**filters).values(
                'id_cat_gastos__nombre',
                'id_cuenta_banco__id',
                'id_cuenta_banco__numero_cuenta',
                'id_cuenta_banco__id_banco__nombre',
                'id_sucursal__nombre'  # Sucursal del GASTO, no de la cuenta
            ).annotate(
                total_gastos=Sum('monto'),
                mes=TruncMonth('fecha')  # Tomamos el primer mes para referencia
            ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta')
        else:
            balances = []
        
        # Convertir a lista y agregar datos adicionales
        balances_list = list(balances)
        
        # Agregar información adicional a cada balance
        for i, balance in enumerate(balances_list, 1):
            balance['numero_secuencial'] = i
            
            # Agregar información sobre múltiples categorías (para información)
            categoria_nombre = balance['id_cat_gastos__nombre']
            cuentas_count = Gastos.objects.filter(
                **filters, 
                id_cat_gastos__nombre=categoria_nombre
            ).values('id_cuenta_banco').distinct().count()
            
            if cuentas_count > 1:
                balance['cuenta_info'] = f"Cuenta {balance['id_cuenta_banco__numero_cuenta']} de {cuentas_count} total"
            else:
                balance['cuenta_info'] = "Única cuenta para esta categoría"
        
        return balances_list
    
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
        
        # Obtener múltiples meses (para selector múltiple)
        months_param = request.GET.get('months', '')
        selected_months = []
        if months_param and months_param.strip():
            try:
                # Dividir por comas y limpiar cada valor
                month_values = months_param.split(',')
                for m in month_values:
                    m_clean = m.strip()
                    if m_clean:
                        month_int = int(m_clean)
                        if 1 <= month_int <= 12:
                            selected_months.append(month_int)
            except (ValueError, TypeError):
                selected_months = []
        
        # Obtener cuenta_id y limpiarlo
        cuenta_id_param = request.GET.get('cuenta_id', '')
        cuenta_id = ''
        if cuenta_id_param:
            try:
                cuenta_id = int(str(cuenta_id_param).strip())
            except (ValueError, TypeError):
                cuenta_id = ''
        
        # Obtener sucursal_id y limpiarlo
        sucursal_id_param = request.GET.get('sucursal_id', '')
        sucursal_id = ''
        if sucursal_id_param:
            try:
                sucursal_id = int(str(sucursal_id_param).strip())
            except (ValueError, TypeError):
                sucursal_id = ''
        
        return {
            'cuenta_id': cuenta_id,
            'sucursal_id': sucursal_id,
            'year': year,
            'month': month,
            'selected_months': selected_months,
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
            params['cuenta_id'], params['year'], params['month'], params.get('selected_months', []),
            params['periodo'], params['dia'], params['fecha_inicio'], params['fecha_fin'], params['sucursal_id']
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
            'selected_sucursal_id': params['sucursal_id'],
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
