"""URLs para el modulo de WhatsApp / Evolution API."""

from django.urls import path

from .webhook_handler import webhook_receiver, webhook_instance_receiver
from . import views

app_name = "whatsapp"

urlpatterns = [
    path("webhook/", webhook_receiver, name="webhook_receiver"),
    path("webhook/<str:instance_id>/", webhook_instance_receiver, name="webhook_instance_receiver"),
]
