from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path
from .views import compras_balances_view, ingresar_gasto_factura, guardar_gasto_factura, guardar_gastos_estado_cuenta

app_name = 'gastos'

urlpatterns = [
    path('compras/', compras_balances_view, name='compras_balances'),
    path('ingresar-factura/', ingresar_gasto_factura, name='ingresar_gasto_factura'),
    path('guardar-gasto-factura/', guardar_gasto_factura, name='guardar_gasto_factura'),
    path('guardar-gastos-estado-cuenta/', guardar_gastos_estado_cuenta, name='guardar_gastos_estado_cuenta'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



