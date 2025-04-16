from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path
from .views import compras_balances_view

urlpatterns = [
    path('compras/', compras_balances_view, name='compras_productores'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



