from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from .views import (
    archivo_comprobante,
    capturar_comprobante,
    estado_comprobante,
    guardar_gasto_factura,
    guardar_gastos_estado_cuenta,
    ingresar_gasto_factura,
    reintentar_comprobante,
    revisar_comprobante,
)

app_name = 'gastos'
urlpatterns = [
    path('ingresar-factura/', ingresar_gasto_factura, name='ingresar_gasto_factura'),
    path('guardar-gasto-factura/', guardar_gasto_factura, name='guardar_gasto_factura'),
    path('guardar-gastos-estado-cuenta/', guardar_gastos_estado_cuenta, name='guardar_gastos_estado_cuenta'),
    path('comprobantes/capturar/', capturar_comprobante, name='capturar_comprobante'),
    path('comprobantes/<int:pk>/', revisar_comprobante, name='revisar_comprobante'),
    path('comprobantes/<int:pk>/estado/', estado_comprobante, name='estado_comprobante'),
    path('comprobantes/<int:pk>/reintentar/', reintentar_comprobante, name='reintentar_comprobante'),
    path('comprobantes/<int:pk>/archivo/', archivo_comprobante, name='archivo_comprobante'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
