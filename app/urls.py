from django.contrib import admin
from django.urls import path, include
from catalogo.views import index, data
from .views import balances_view, export_full_report_to_excel
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Función para redireccionar a admin
def redirect_to_admin(request):
    return redirect('admin:index')

urlpatterns = [
    path("admin/", admin.site.urls),  # Added trailing slash
    path('balances/', balances_view, name='balances'),
    path('export-full-report/', export_full_report_to_excel, name='export_full_report'),
    path('', include('catalogo.urls')),
    path('', include('gastos.urls')),
    path('', redirect_to_admin, name='redirect_to_admin'),  # Redirige la raíz a admin
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
