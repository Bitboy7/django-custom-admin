from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from catalogo.views import index, data
from .views import balances_view, export_full_report_to_excel, currency_conversion_api, currency_test_view, user_manual_view
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Función para redireccionar a admin
def redirect_to_admin(request):
    return redirect('admin:index')

# URLs que no necesitan prefijo de idioma
urlpatterns = [
    # URL para cambiar idioma (debe estar fuera de i18n_patterns)
    path("i18n/", include("django.conf.urls.i18n")),
    # API de conversión de moneda (sin prefijo de idioma)
    path('api/currency-conversion/', currency_conversion_api, name='currency_conversion_api'),
]

# Agregar archivos media tanto en desarrollo como en producción
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# En producción, también agregamos archivos estáticos por si acaso
if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# URLs con prefijo de idioma
urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path('balances/', balances_view, name='balances'),
    path('manual/', user_manual_view, name='user_manual'),
    path('export-full-report/', export_full_report_to_excel, name='export_full_report'),
    path('', include('catalogo.urls')),
    path('', include('gastos.urls')),
    path('', redirect_to_admin, name='redirect_to_admin'),  # Redirige la raíz a admin
    prefix_default_language=True,  # Incluir idioma por defecto en la URL
)
