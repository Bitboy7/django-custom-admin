from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path
from .views import registro_gasto, compras_productores, detalle_productor_compras, guardar_compra, estadisticas_compras

urlpatterns = [
    path('registro/', registro_gasto, name='registro_gasto'),
    path('compras/', compras_productores, name='compras_productores'),
    path('compras/productor/<int:productor_id>/', detalle_productor_compras, name='detalle_productor_compras'),
    path('compras/guardar/', guardar_compra, name='guardar_compra'),
    path('compras/estadisticas/', estadisticas_compras, name='estadisticas_compras'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



