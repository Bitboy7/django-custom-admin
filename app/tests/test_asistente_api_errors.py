"""Error payloads of the assistant chat API.

The UI relies on ``codigo`` / ``reintentable`` / ``accion`` / ``reintentar_en``
to offer only the recovery that can work, and on ``error`` being plain language
(technical causes go to ``detalle``).
"""

import json
from types import SimpleNamespace
from unittest import mock

import pytest
from django.test import RequestFactory

from app import assistant_views as views
from app.services.mcp_chat_service import (
    ChatConfigurationError,
    ChatConnectionError,
    ChatModelError,
)


def _user(**overrides):
    data = {
        "is_authenticated": True,
        "is_staff": True,
        "pk": 7,
        "is_verified": lambda: True,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _post(user, body=None):
    request = RequestFactory().post(
        "/es/asistente/api/chat/",
        data=json.dumps(body if body is not None else {"mensaje": "ventas de enero"}),
        content_type="application/json",
    )
    request.user = user
    request._dont_enforce_csrf_checks = True
    return request


def _call(user, body=None):
    response = views.asistente_chat_api(_post(user, body))
    return response, json.loads(response.content)


@pytest.fixture(autouse=True)
def _no_rate_limit():
    with mock.patch.object(views, "_rate_limited", return_value=False):
        yield


def test_expired_session_offers_login_link_and_no_retry():
    response, data = _call(_user(is_authenticated=False))
    assert response.status_code == 401
    assert data["codigo"] == "sesion_expirada"
    assert data["reintentable"] is False
    assert data["accion"]["etiqueta"] == "Iniciar sesión"
    assert data["accion"]["url"]
    assert data["accion"]["nueva_pestana"] is True


def test_missing_2fa_links_to_setup():
    response, data = _call(_user(is_verified=lambda: False))
    assert response.status_code == 403
    assert data["codigo"] == "requiere_2fa"
    assert data["reintentable"] is False
    assert data["accion"]["url"]


def test_non_staff_has_no_retry_and_no_action():
    response, data = _call(_user(is_staff=False))
    assert response.status_code == 403
    assert data["codigo"] == "sin_permiso"
    assert data["reintentable"] is False
    assert "accion" not in data


def test_rate_limit_reports_wait_time():
    with mock.patch.object(views, "_rate_limited", return_value=True), mock.patch.object(
        views, "_retry_after_seconds", return_value=125
    ):
        response, data = _call(_user())
    assert response.status_code == 429
    assert data["codigo"] == "limite_consultas"
    assert data["reintentable"] is True
    assert data["reintentar_en"] == 125
    assert response["Retry-After"] == "125"


def test_empty_message_is_not_retryable():
    response, data = _call(_user(), {"mensaje": "   "})
    assert response.status_code == 400
    assert data["codigo"] == "consulta_vacia"
    assert data["reintentable"] is False


@pytest.mark.parametrize(
    "exc, status, codigo, reintentable",
    [
        (ChatConfigurationError("Falta MCP_HTTP_TOKEN. Configúralo en el .env"), 503, "no_configurado", False),
        (ChatConnectionError("No se pudo conectar al servidor MCP en 127.0.0.1"), 502, "sin_conexion_datos", True),
        (ChatModelError("Revisa OPENAI_API_KEY"), 502, "ia_no_disponible", True),
    ],
)
def test_service_errors_keep_technical_cause_out_of_the_message(exc, status, codigo, reintentable):
    with mock.patch.object(views, "resolve_conversation", return_value=object()), mock.patch.object(
        views, "load_history", return_value=[]
    ), mock.patch.object(views, "save_user_message"), mock.patch.object(
        views, "save_error_message"
    ), mock.patch.object(views, "preguntar", side_effect=exc):
        response, data = _call(_user())

    assert response.status_code == status
    assert data["codigo"] == codigo
    assert data["reintentable"] is reintentable
    assert data["detalle"] == str(exc)
    for jargon in ("MCP", "OPENAI", ".env", "127.0.0.1"):
        assert jargon not in data["error"]


def test_unexpected_error_is_retryable_without_detail():
    with mock.patch.object(views, "resolve_conversation", return_value=object()), mock.patch.object(
        views, "load_history", return_value=[]
    ), mock.patch.object(views, "save_user_message"), mock.patch.object(
        views, "save_error_message"
    ), mock.patch.object(views, "preguntar", side_effect=RuntimeError("stack interno")):
        response, data = _call(_user())

    assert response.status_code == 500
    assert data["codigo"] == "error_inesperado"
    assert data["reintentable"] is True
    assert "detalle" not in data
    assert "stack interno" not in json.dumps(data)


def test_success_reports_server_cutoff_date():
    conversation = SimpleNamespace(pk=42, titulo="Cartera")
    with mock.patch.object(views, "resolve_conversation", return_value=conversation), mock.patch.object(
        views, "load_history", return_value=[]
    ), mock.patch.object(views, "save_user_message"), mock.patch.object(
        views, "save_assistant_message"
    ), mock.patch.object(
        views, "preguntar", return_value={"respuesta": "ok", "traza": [], "meta": {}}
    ), mock.patch.object(
        views.timezone, "localdate", return_value=__import__("datetime").date(2026, 11, 20)
    ):
        response, data = _call(_user())

    assert response.status_code == 200
    assert data["meta"]["consultado_en"] == "2026-11-20"
    assert data["conversacion_id"] == "42"
