from django.contrib import admin
from django.urls import path, include
from catalogo.views import index, data
from gastos.views import registro_gasto
from .views import balances_view, reportes, export_to_excel
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
    path("admin", admin.site.urls),  # Set /admin as the main URL
    path('data/', data, name='data'),
    path('gastos/', registro_gasto, name='gastos'),
    path('balances/', balances_view, name='balances'),
    path('reportes/', reportes, name='reportes'),
    path('excel/', export_to_excel, name='excel'),
    path('', include('catalogo.urls')),
    path('', include('gastos.urls')),
]
