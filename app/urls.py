from django.contrib import admin
from django.urls import path, include
from catalogo.views import index, data
from gastos import views as gastos_views
from ventas import views as ventas_views
from . import views
"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
urlpatterns = [
    path("", admin.site.urls),  # Set /admin as the main URL
    path('reportes/', views.reportes, name='reportes'),  # Nueva ruta para reportes
    path('', include('catalogo.urls')),
    path('', include('gastos.urls')),
    path('', include('ventas.urls')),
]

   
