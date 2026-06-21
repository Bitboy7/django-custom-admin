from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from catalogo.views import index, data
from .views import export_full_report_to_excel, currency_conversion_api, currency_test_view, user_manual_view, custom_admin_index, profile_settings_view
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import RedirectView
from two_factor.urls import urlpatterns as tf_urls

# Función para redireccionar a admin
def redirect_to_admin(request):
    return redirect('admin:index')

# URLs que no necesitan prefijo de idioma
urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=f'{settings.STATIC_URL}favicon.ico', permanent=True)),
    # URL para cambiar idioma (debe estar fuera de i18n_patterns)
    path("i18n/", include("django.conf.urls.i18n")),
    # API de conversión de moneda (sin prefijo de idioma)
    path('api/currency-conversion/', currency_conversion_api, name='currency_conversion_api'),
    # 2FA: login, setup, QR, backup tokens (sin prefijo de idioma para simplificar)
    path('', include(tf_urls)),
    # Webhooks de WhatsApp (sin prefijo de idioma: Evolution API llama directamente)
    path('whatsapp/', include('whatsapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# URLs con prefijo de idioma
urlpatterns += i18n_patterns(
    path('admin/mi-perfil/', profile_settings_view, name='profile_settings'),
    path("admin/", admin.site.urls),
    path("admin/dashboard/", custom_admin_index, name='custom_admin_index'),
    path('manual/', user_manual_view, name='user_manual'),
    path('export-full-report/', export_full_report_to_excel, name='export_full_report'),
    path('', include('catalogo.urls')),
    path('', include('gastos.urls')),
    path('capital-inversiones/', include('capital_inversiones.urls')),  # URLs del módulo de capital
    path('ventas/', include('ventas.urls')),  # URLs del módulo de ventas
    path('', redirect_to_admin, name='redirect_to_admin'),  # Redirige la raíz a admin
    prefix_default_language=True,  # Incluir idioma por defecto en la URL
)
