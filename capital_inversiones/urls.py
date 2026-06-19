from django.urls import path
from . import views

app_name = 'capital_inversiones'

urlpatterns = [
    # Dashboard principal
    path('dashboard/', views.dashboard_inversiones, name='dashboard'),
    
    # Reportes acumulados
    path('reporte/sucursal/', views.reporte_acumulado_sucursal, name='reporte_sucursal'),
    path('reporte/categoria/', views.reporte_acumulado_categoria, name='reporte_categoria'),
    path('reporte/rendimientos/', views.reporte_rendimientos, name='reporte_rendimientos'),
    
    # APIs para gráficos
    path('api/balance-mensual/', views.api_balance_mensual, name='api_balance_mensual'),
    path('api/distribucion-categorias/', views.api_distribucion_categorias, name='api_distribucion_categorias'),
]
