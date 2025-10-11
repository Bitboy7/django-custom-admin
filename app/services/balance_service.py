"""
Servicio para análisis de balances y gastos

REFACTORIZADO: Ahora usa la arquitectura modular de servicios base.
La mayoría de la lógica común está en BaseReportServiceWithCategories.
"""
from datetime import datetime
from django.db.models import Count
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.db.models import Sum

from gastos.models import Gastos, Cuenta
from .base_report_service import BaseReportServiceWithCategories


class BalanceAnalysisService(BaseReportServiceWithCategories):
    """
    Servicio para análisis de balances y gastos
    
    Hereda de BaseReportServiceWithCategories para reutilizar:
    - Construcción de filtros
    - Agregación por períodos
    - Cálculo de estadísticas
    - Formateo de períodos
    - Y más funcionalidad común
    
    Solo necesita implementar los métodos específicos de Gastos.
    """
    
    # ==================== IMPLEMENTACIÓN DE MÉTODOS ABSTRACTOS ====================
    
    def get_model(self):
        """Retorna el modelo Gastos"""
        return Gastos
    
    def get_date_field(self) -> str:
        """Campo de fecha en Gastos"""
        return 'fecha'
    
    def get_amount_field(self) -> str:
        """Campo de monto en Gastos"""
        return 'monto'
    
    def get_category_field(self) -> str:
        """Campo de categoría en Gastos"""
        return 'id_cat_gastos__nombre'
    
    def get_group_fields(self, periodo: str):
        """
        Campos de agrupación según el período
        
        Para Gastos, agrupamos por:
        - Categoría del gasto
        - Cuenta bancaria (ID, número, banco)
        - Sucursal del gasto
        - Período (si aplica)
        """
        base_fields = [
            'id_cat_gastos__nombre',
            'id_cuenta_banco__id',
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_sucursal__nombre'
        ]
        
        # Los períodos diario y semanal necesitan campos adicionales
        if periodo == 'diario':
            return base_fields + ['fecha']
        elif periodo == 'semanal':
            # Para semanal, anotamos con 'semana' en get_balances_by_period_custom
            return base_fields + ['semana']
        else:  # mensual
            return base_fields
    
    # ==================== PERSONALIZACIÓN ESPECÍFICA DE GASTOS ====================
    
    def get_balances_by_period(self, filters, periodo='mensual'):
        """
        Override del método base para añadir lógica específica de Gastos
        
        Añade:
        - Campo 'mes' para período mensual
        - Información adicional (número secuencial, cuenta_info)
        """
        balances = self._get_balances_queryset(filters, periodo)
        balances_list = list(balances)
        
        # Añadir información adicional específica de Gastos
        self._enrich_balance_data(balances_list, filters)
        
        return balances_list
    
    def _get_balances_queryset(self, filters, periodo):
        """Obtiene el queryset base según el período"""
        queryset = Gastos.objects.filter(**filters)
        group_fields = self.get_group_fields(periodo)
        
        if periodo == 'diario':
            return queryset.values(*group_fields).annotate(
                total_gastos=Sum('monto')
            ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta', 'fecha')
            
        elif periodo == 'semanal':
            return queryset.annotate(
                semana=TruncWeek('fecha')
            ).values(*group_fields).annotate(
                total_gastos=Sum('monto')
            ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta', 'semana')
            
        else:  # mensual
            base_fields = [f for f in group_fields if f != 'mes']
            return queryset.values(*base_fields).annotate(
                total_gastos=Sum('monto'),
                mes=TruncMonth('fecha')
            ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta')
    
    def _enrich_balance_data(self, balances_list, filters):
        """Añade información adicional a cada balance"""
        for i, balance in enumerate(balances_list, 1):
            balance['numero_secuencial'] = i
            
            # Información sobre múltiples cuentas para la categoría
            categoria_nombre = balance.get('id_cat_gastos__nombre')
            if categoria_nombre:
                cuentas_count = Gastos.objects.filter(
                    **filters, 
                    id_cat_gastos__nombre=categoria_nombre
                ).values('id_cuenta_banco').distinct().count()
                
                if cuentas_count > 1:
                    balance['cuenta_info'] = f"Cuenta {balance['id_cuenta_banco__numero_cuenta']} de {cuentas_count} total"
                else:
                    balance['cuenta_info'] = "Única cuenta para esta categoría"
    
    def calculate_statistics(self, filters):
        """
        Override para añadir estadísticas específicas de Gastos
        
        Añade información sobre categorías con gasto máximo y mínimo
        """
        # Usar estadísticas base
        stats = super().calculate_statistics(filters)
        
        # Añadir estadísticas específicas de categorías
        queryset = Gastos.objects.filter(**filters)
        
        categoria_maximo = None
        categoria_minimo = None
        
        if stats['maximo'] > 0:
            gasto_max = queryset.filter(monto=stats['maximo']).first()
            if gasto_max:
                categoria_maximo = gasto_max.id_cat_gastos.nombre
        
        if stats['minimo'] > 0:
            gasto_min = queryset.filter(monto=stats['minimo']).first()
            if gasto_min:
                categoria_minimo = gasto_min.id_cat_gastos.nombre
        
        # Renombrar para mantener compatibilidad con código existente
        return {
            'total_gastos': stats['total'],
            'promedio_gastos': stats['promedio'],
            'numero_transacciones': stats['cantidad'],
            'gasto_maximo': stats['maximo'],
            'gasto_minimo': stats['minimo'],
            'gasto_mediano': stats.get('mediana', 0),
            'categoria_gasto_maximo': categoria_maximo,
            'categoria_gasto_minimo': categoria_minimo,
        }
    
    # ==================== MÉTODOS DE COMPATIBILIDAD ====================
    # Mantienen la interfaz existente para evitar romper código dependiente
    
    def process_request_parameters(self, request):
        """
        Procesa parámetros del request (mantiene compatibilidad)
        
        NOTA: Usa extract_filters_from_request del servicio base, pero
        añade limpieza adicional de caracteres especiales específica de este proyecto.
        """
        # Obtener el año y limpiarlo de caracteres especiales
        year_param = request.GET.get('year', str(datetime.now().year))
        year_param = str(year_param).replace('\xa0', '').replace('\u00A0', '').strip()
        try:
            year = int(year_param)
        except (ValueError, TypeError):
            year = datetime.now().year
        
        # Extraer otros parámetros usando la funcionalidad base
        params = {
            'year': year,
            'month': request.GET.get('month', ''),
            'cuenta_id': request.GET.get('cuenta_id', ''),
            'sucursal_id': request.GET.get('sucursal_id', ''),
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
        Obtiene el contexto completo para la vista (mantiene compatibilidad)
        
        Combina toda la funcionalidad heredada del servicio base
        con el procesamiento específico de parámetros.
        """
        # Procesar parámetros
        params = self.process_request_parameters(request)
        
        # Obtener datos de filtros (usa método heredado)
        filter_data = self.get_filter_data()
        
        # Construir filtros (usa método heredado)
        filters = self.build_filters(
            cuenta_id=params['cuenta_id'],
            year=params['year'],
            month=params['month'],
            selected_months=params.get('selected_months', []),
            periodo=params['periodo'],
            dia=params['dia'],
            fecha_inicio=params['fecha_inicio'],
            fecha_fin=params['fecha_fin'],
            sucursal_id=params['sucursal_id']
        )
        
        # Obtener balances (usa método personalizado)
        balances = self.get_balances_by_period(filters, params['periodo'])
        
        # Calcular acumulados (usa método heredado)
        balances = self.calculate_accumulated(balances)
        
        # Calcular estadísticas (usa método personalizado)
        statistics = self.calculate_statistics(filters)
        
        # Combinar contexto
        context = {
            'balances': balances,
            **filter_data,
            **params,
            **statistics,
            'meses_rango': range(1, 13),
        }
        
        # Renombrar para mantener compatibilidad con templates
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



