from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .services.excel_service import ExcelReportService
from .services.balance_service import BalanceAnalysisService
from .services.utils import UtilService
from gastos.models import Gastos, Compra
from ventas.models import Ventas
from auditoria.models import LogActividad


@user_passes_test(UtilService.is_admin)
def export_full_report_to_excel(request):
    """
    Exporta un informe completo con gastos, compras, ventas, anticipos y un balance mensual.
    """
    excel_service = ExcelReportService()
    workbook = excel_service.create_full_report()
    
    return UtilService.create_excel_response(
        workbook, 
        filename_prefix="reporte_financiero"
    )


@login_required
def balances_view(request):
    """
    Vista principal para el análisis de balances y gastos
    """
    balance_service = BalanceAnalysisService()
    context = balance_service.get_full_context(request)
    
    return render(request, 'balances.html', context)


def dashboard_callback(request, context):
    """
    Callback para el dashboard personalizado de Django Unfold
    """
    # Obtener fechas para cálculos
    now = timezone.now()
    current_month = now.month
    current_year = now.year
    last_month = current_month - 1 if current_month > 1 else 12
    last_month_year = current_year if current_month > 1 else current_year - 1
    
    # Calcular métricas principales
    try:
        # Total gastos del mes actual
        total_gastos = Gastos.objects.filter(
            fecha__month=current_month,
            fecha__year=current_year
        ).aggregate(total=Sum('monto'))['total'] or 0
        
        # Total gastos del mes anterior
        gastos_mes_anterior = Gastos.objects.filter(
            fecha__month=last_month,
            fecha__year=last_month_year
        ).aggregate(total=Sum('monto'))['total'] or 0
        
        # Calcular tendencia de gastos
        gastos_trend = 0
        if gastos_mes_anterior > 0:
            gastos_trend = ((total_gastos - gastos_mes_anterior) / gastos_mes_anterior) * 100
        
        # Total ventas del mes actual
        total_ventas = Ventas.objects.filter(
            fecha_salida_manifiesto__month=current_month,
            fecha_salida_manifiesto__year=current_year
        ).aggregate(total=Sum('monto'))['total'] or 0
        
        # Total ventas del mes anterior
        ventas_mes_anterior = Ventas.objects.filter(
            fecha_salida_manifiesto__month=last_month,
            fecha_salida_manifiesto__year=last_month_year
        ).aggregate(total=Sum('monto'))['total'] or 0
        
        # Calcular tendencia de ventas
        ventas_trend = 0
        if ventas_mes_anterior > 0:
            ventas_trend = ((total_ventas - ventas_mes_anterior) / ventas_mes_anterior) * 100
        
        # Total compras del mes actual
        total_compras = Compra.objects.filter(
            fecha_compra__month=current_month,
            fecha_compra__year=current_year
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        # Total compras del mes anterior
        compras_mes_anterior = Compra.objects.filter(
            fecha_compra__month=last_month,
            fecha_compra__year=last_month_year
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        # Calcular tendencia de compras
        compras_trend = 0
        if compras_mes_anterior > 0:
            compras_trend = ((total_compras - compras_mes_anterior) / compras_mes_anterior) * 100
        
        # Balance neto
        balance_neto = total_ventas - total_gastos - total_compras
        
        # Gastos por categoría para el gráfico
        gastos_por_categoria = Gastos.objects.filter(
            fecha__month=current_month,
            fecha__year=current_year
        ).values(
            'id_cat_gastos__nombre'
        ).annotate(
            total=Sum('monto')
        ).order_by('-total')[:6]
        
        gastos_categorias_labels = [item['id_cat_gastos__nombre'] for item in gastos_por_categoria]
        gastos_categorias_data = [float(item['total']) for item in gastos_por_categoria]
        
        # Datos mensuales para tendencias (últimos 6 meses)
        meses_labels = []
        gastos_mensuales = []
        ventas_mensuales = []
        
        for i in range(6):
            mes = (current_month - i - 1) % 12 + 1
            año = current_year if current_month - i > 0 else current_year - 1
            
            meses_labels.insert(0, f"{mes:02d}/{año}")
            
            gastos_mes = Gastos.objects.filter(
                fecha__month=mes,
                fecha__year=año
            ).aggregate(total=Sum('monto'))['total'] or 0
            gastos_mensuales.insert(0, float(gastos_mes))
            
            ventas_mes = Ventas.objects.filter(
                fecha_salida_manifiesto__month=mes,
                fecha_salida_manifiesto__year=año
            ).aggregate(total=Sum('monto'))['total'] or 0
            ventas_mensuales.insert(0, float(ventas_mes))
        
        # Actividad reciente
        recent_activities = []
        try:
            activities = LogActividad.objects.order_by('-fecha_evento')[:5]
            for activity in activities:
                recent_activities.append({
                    'description': activity.descripcion_evento,
                    'user': activity.usuario.username if activity.usuario else 'Sistema',
                    'timestamp': activity.fecha_evento,
                    'status': 'success',
                    'icon': 'edit',
                    'color': 'blue'
                })
        except:
            # Si no hay modelo de auditoría o hay errores, crear actividades dummy
            recent_activities = [
                {
                    'description': 'Sistema iniciado correctamente',
                    'user': 'Sistema',
                    'timestamp': now,
                    'status': 'success',
                    'icon': 'check',
                    'color': 'green'
                }
            ]
        
        # Total de usuarios
        total_users = User.objects.count()
        
    except Exception as e:
        # En caso de error, usar valores por defecto
        total_gastos = 0
        total_ventas = 0
        total_compras = 0
        gastos_trend = 0
        ventas_trend = 0
        compras_trend = 0
        balance_neto = 0
        gastos_categorias_labels = []
        gastos_categorias_data = []
        meses_labels = ['01/2025', '02/2025', '03/2025', '04/2025', '05/2025', '06/2025']
        gastos_mensuales = [0, 0, 0, 0, 0, 0]
        ventas_mensuales = [0, 0, 0, 0, 0, 0]
        recent_activities = []
        total_users = User.objects.count()
    
    # Actualizar el contexto con los datos del dashboard
    context.update({
        'total_gastos': total_gastos,
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'gastos_trend': gastos_trend,
        'ventas_trend': ventas_trend,
        'compras_trend': compras_trend,
        'balance_neto': balance_neto,
        'gastos_categorias_labels': json.dumps(gastos_categorias_labels),
        'gastos_categorias_data': json.dumps(gastos_categorias_data),
        'meses_labels': json.dumps(meses_labels),
        'gastos_mensuales': json.dumps(gastos_mensuales),
        'ventas_mensuales': json.dumps(ventas_mensuales),
        'recent_activities': recent_activities,
        'total_users': total_users,
        'last_login': request.user.last_login,
        'last_update': now.date(),
    })
    
    return context


