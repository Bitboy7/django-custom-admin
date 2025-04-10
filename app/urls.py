from django.contrib import admin
from django.urls import path, include
from catalogo.views import index, data
from gastos.views import registro_gasto
from .views import balances_view, export_to_excel
from django.conf import settings
from django.conf.urls.static import static
from django_otp.admin import OTPAdminSite
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin

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
# Otp admin site
class OTPAdmin(OTPAdminSite):
    pass

admin_site = OTPAdmin(name='OTPAdmin')
admin_site.register(User)
admin_site.register(TOTPDevice, TOTPDeviceAdmin)

if User not in admin_site._registry:
    admin_site.register(User)
if TOTPDevice not in admin_site._registry:
    admin_site.register(TOTPDevice, TOTPDeviceAdmin)
    
for model_cls, model_admin in admin.site._registry.items():
    if model_cls not in admin_site._registry:
        admin_site.register(model_cls, model_admin.__class__)

# Urls for the app
urlpatterns = [
    #path("admin", admin.site.urls),  # Set /admin as the main URL
    path("admin/", admin_site.urls),  # Set /admin as the main URL
    path('data/', data, name='data'),
    path('gastos/', registro_gasto, name='gastos'),
    path('balances/', balances_view, name='balances'),
    path('exportar_gastos_excel/', export_to_excel, name='exportar_gastos_excel'),
    path('', include('catalogo.urls')),
    path('gastos/', include('gastos.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
