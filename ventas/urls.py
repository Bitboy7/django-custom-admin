from django.urls import path
from . import views

urlpatterns = [
    path('anticipos/', views.lista_anticipos, name='lista_anticipos'),
    path('anticipos/crear/', views.crear_anticipo, name='crear_anticipo'),
]