"""
Cliente HTTP para interactuar con Evolution API (WhatsApp).
Proporciona metodos para enviar mensajes, configurar webhooks,
verificar conexion y gestionar instancias.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class EvolutionAPIError(Exception):
    pass


class EvolutionAPIService:
    """Cliente REST para Evolution API (WhatsApp)."""

    def __init__(self, instance_id: str, api_url: str, apikey: str):
        self.instance_id = instance_id
        self.api_url = api_url.rstrip("/")
        self.apikey = apikey
        self._session = requests.Session()
        self._session.headers.update({
            "apikey": apikey,
            "Content-Type": "application/json",
        })
        self._timeout = 30

    # ── Mensajeria ────────────────────────────────────────────────────── #

    def send_text(self, number: str, text: str, delay: int | None = None) -> dict:
        """
        Envia un mensaje de texto a un numero de WhatsApp.

        Args:
            number: Numero con codigo de pais sin '+' (ej: 5216671234567).
            text: Contenido del mensaje.
            delay: Milisegundos de retraso entre mensajes.

        Returns:
            Respuesta JSON de Evolution API.
        """
        endpoint = f"{self.api_url}/message/sendText/{self.instance_id}"
        payload: dict[str, Any] = {
            "number": number,
            "text": text,
        }
        if delay is not None:
            payload["options"] = {"delay": delay}

        try:
            response = self._session.post(endpoint, json=payload, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, str):
                try:
                    import json as _json
                    data = _json.loads(data)
                except Exception:
                    pass
            return data
        except requests.exceptions.Timeout:
            raise EvolutionAPIError(f"Timeout al enviar mensaje a {number}: el servidor no respondio en {self._timeout}s.")
        except requests.exceptions.ConnectionError:
            raise EvolutionAPIError(f"No se pudo conectar al servidor Evolution en {self.api_url}.")
        except requests.exceptions.HTTPError as exc:
            detail = ""
            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text[:500] if exc.response else ""
            raise EvolutionAPIError(f"Error HTTP {exc.response.status_code if exc.response else '?'} al enviar mensaje: {detail}")

    def send_image(
        self,
        number: str,
        image_url: str,
        caption: str = "",
    ) -> dict:
        """Envia una imagen via WhatsApp."""
        endpoint = f"{self.api_url}/message/sendMedia/{self.instance_id}"
        payload = {
            "number": number,
            "mediatype": "image",
            "media": image_url,
            "caption": caption,
        }
        try:
            response = self._session.post(endpoint, json=payload, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise EvolutionAPIError(f"Error al enviar imagen: {exc}")

    def send_document(
        self,
        number: str,
        document_url: str,
        filename: str = "reporte.pdf",
        caption: str = "",
    ) -> dict:
        """Envia un documento (PDF, Excel, etc.) via WhatsApp."""
        endpoint = f"{self.api_url}/message/sendMedia/{self.instance_id}"
        payload = {
            "number": number,
            "mediatype": "document",
            "media": document_url,
            "fileName": filename,
            "caption": caption,
        }
        try:
            response = self._session.post(endpoint, json=payload, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise EvolutionAPIError(f"Error al enviar documento: {exc}")

    # ── Webhooks ──────────────────────────────────────────────────────── #

    def set_webhook(self, webhook_url: str, events: list[str] | None = None) -> dict:
        """
        Configura el webhook de la instancia para recibir eventos entrantes.

        Args:
            webhook_url: URL de tu servidor Django que recibira los eventos.
            events: Lista de eventos a escuchar. Si es None, se usa ["MESSAGES_UPSERT"].

        Returns:
            Respuesta JSON de Evolution API.
        """
        if events is None:
            events = ["MESSAGES_UPSERT"]

        endpoint = f"{self.api_url}/webhook/set/{self.instance_id}"
        payload = {
            "enabled": True,
            "url": webhook_url,
            "webhook_by_events": True,
            "events": events,
        }
        try:
            response = self._session.post(endpoint, json=payload, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise EvolutionAPIError(f"Error al configurar webhook: {exc}")

    def find_webhook(self) -> dict:
        """Obtiene la configuracion actual del webhook."""
        endpoint = f"{self.api_url}/webhook/find/{self.instance_id}"
        try:
            response = self._session.get(endpoint, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise EvolutionAPIError(f"Error al consultar webhook: {exc}")

    # ── Estado de conexion ────────────────────────────────────────────── #

    def check_connection(self) -> dict:
        """
        Verifica el estado de conexion de la instancia.

        Usa /instance/fetchInstances para obtener el estado real,
        ya que /instance/connectionState no siempre devuelve el campo state.

        Returns:
            {
                "state": "OPEN" | "CONNECTING" | "CLOSE",
                "instanceName": "...",
                "ownerJid": "...",
            }
        """
        endpoint = f"{self.api_url}/instance/fetchInstances"
        try:
            response = self._session.get(endpoint, timeout=self._timeout)
            response.raise_for_status()
            instances = response.json()

            if isinstance(instances, list):
                for inst in instances:
                    if inst.get("id") == self.instance_id or inst.get("name") == self.instance_id:
                        return {
                            "state": inst.get("connectionStatus", "close").upper(),
                            "instanceName": inst.get("name", self.instance_id),
                            "ownerJid": inst.get("ownerJid", ""),
                            "profileName": inst.get("profileName", ""),
                            "number": inst.get("number", ""),
                        }

            raise EvolutionAPIError(
                f"Instancia '{self.instance_id}' no encontrada en fetchInstances. "
                f"Verifica que el ID de instancia sea correcto."
            )
        except requests.exceptions.RequestException as exc:
            raise EvolutionAPIError(f"Error al verificar conexion: {exc}")

    def get_qr_code(self) -> dict:
        """Obtiene el QR code para conectar la instancia."""
        endpoint = f"{self.api_url}/instance/connect/{self.instance_id}"
        try:
            response = self._session.get(endpoint, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise EvolutionAPIError(f"Error al obtener QR code: {exc}")

    def logout_instance(self) -> dict:
        """Desconecta la instancia de WhatsApp."""
        endpoint = f"{self.api_url}/instance/logout/{self.instance_id}"
        try:
            response = self._session.delete(endpoint, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise EvolutionAPIError(f"Error al desconectar instancia: {exc}")


def get_evolution_service(instance: "whatsapp.models.EvolutionInstance") -> EvolutionAPIService:
    """Factory: crea un servicio EvolutionAPIService a partir de una instancia del modelo."""
    return EvolutionAPIService(
        instance_id=instance.instance_id,
        api_url=instance.api_url,
        apikey=instance.apikey,
    )


def verificar_y_actualizar_estado(instance: "whatsapp.models.EvolutionInstance") -> str:
    """
    Verifica el estado de conexion de una instancia y actualiza el modelo.

    Returns:
        El estado resultante: 'conectado', 'desconectado' o 'error'.
    """
    try:
        service = get_evolution_service(instance)
        result = service.check_connection()
        state = result.get("state", "").upper()

        if state == "OPEN":
            instance.estado = "conectado"
        else:
            instance.estado = "desconectado"

        instance.ultima_verificacion = timezone.now()
        instance.save(update_fields=["estado", "ultima_verificacion"])
        return instance.estado

    except EvolutionAPIError:
        instance.estado = "error"
        instance.ultima_verificacion = timezone.now()
        instance.save(update_fields=["estado", "ultima_verificacion"])
        return "error"


def configurar_webhook_instancia(instance: "whatsapp.models.EvolutionInstance") -> dict:
    """
    Configura el webhook en Evolution API para una instancia activa.

    Si la instancia no tiene webhook_url definido, construye uno usando
    la URL publica del sitio (dominio de Railway, VPS, etc.).
    """
    if not instance.webhook_url:
        domain = _obtener_dominio_publico()
        es_local = domain in ("localhost", "127.0.0.1", "0.0.0.0")
        protocol = "http" if es_local else "https"
        instance.webhook_url = f"{protocol}://{domain}/whatsapp/webhook/{instance.instance_id}/"
        instance.save(update_fields=["webhook_url"])

    service = get_evolution_service(instance)
    return service.set_webhook(instance.webhook_url)


def _obtener_dominio_publico() -> str:
    """Obtiene el dominio publico del servidor Django, evitando localhost."""
    from django.conf import settings

    # 1. Variable de entorno explicita
    domain = os.environ.get("SITE_DOMAIN", "")
    if domain:
        return domain

    # 2. ALLOWED_HOSTS que no sean locales
    for host in settings.ALLOWED_HOSTS:
        host_clean = host.replace(":8000", "").replace(":80", "").replace(":443", "")
        if host_clean not in ("localhost", "127.0.0.1", "0.0.0.0", "::1", ".sslip.io"):
            if not host_clean.startswith("."):
                return host_clean
        elif host_clean.endswith(".sslip.io"):
            return host_clean

    # 3. Sites framework
    try:
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        if site.domain and site.domain not in ("localhost", "127.0.0.1", "example.com"):
            return site.domain
    except Exception:
        pass

    # 4. Fallback a ALLOWED_HOSTS[0]
    return settings.ALLOWED_HOSTS[0].replace(":8000", "") if settings.ALLOWED_HOSTS else "localhost"
