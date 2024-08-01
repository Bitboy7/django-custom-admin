from django.urls import path
from . import views

urlpatterns = [
    path('gastos/', views.registro_gasto, name='gastos'),
]
