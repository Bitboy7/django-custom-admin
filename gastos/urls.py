from django.urls import path
from . import views

urlpatterns = [
    path('gastos/', views.registro_gasto, name='gastos'),
    path('balance/<int:cuenta_id>/<int:year>/', views.mostrar_balance_mensual, name='mostrar_balance_mensual'),
]
    