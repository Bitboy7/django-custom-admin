from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('anticipos/', views.lista_anticipos, name='lista_anticipos'),
    path('anticipos/crear/', views.crear_anticipo, name='crear_anticipo'),
    path('balances/', views.ventas_balances, name='ventas_balances'),
    path('reporte-cobranza/', views.reporte_cobranza_global, name='reporte_cobranza'),
]