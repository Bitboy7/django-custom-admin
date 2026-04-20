"""
Servicio de IA para la generación de reportes ejecutivos financieros.

Usa LangChain (cadena simple: prompt | model | StrOutputParser) con los mismos
modelos LLM configurados en la variable de entorno GOOGLE_API_MODEL / OPENROUTER_API_MODEL.
Consulta los datos financieros directamente via ORM (siguiendo el patrón de app/views.py)
ya que VentasAnalysisService no está implementado aún.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from gastos.models import Gastos
from ventas.models import Ventas, Cliente
from gastos.models import Compra

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# System prompt                                                                 #
# --------------------------------------------------------------------------- #

EXECUTIVE_SUMMARY_SYSTEM_PROMPT = """\
Eres un CFO virtual especializado en empresas agrícolas y comerciales de México.
Redactas reportes ejecutivos financieros concisos, profesionales y orientados a decisiones.
SIEMPRE respondes en español.

Usa el siguiente contexto financiero del período para generar el reporte:

────────────────────────────────────────────────────────────
DATOS DEL PERÍODO
────────────────────────────────────────────────────────────
Empresa: {empresa_nombre}
Período: {periodo} ({fecha_inicio} → {fecha_fin})
Moneda: MXN

ESTADO DE RESULTADOS
  Ingresos por ventas :  ${total_ventas:,.2f}
  Gastos operativos   :  ${total_gastos:,.2f}
  Compras             :  ${total_compras:,.2f}
  ─────────────────────────────────────────────
  Balance neto        :  ${balance_neto:,.2f}
  Margen bruto        :  {margen_bruto_pct:.1f}%

TENDENCIAS (vs período anterior)
  Ventas   : {tendencia_ventas_pct:+.1f}%
  Gastos   : {tendencia_gastos_pct:+.1f}%
  Compras  : {tendencia_compras_pct:+.1f}%

TOP CATEGORÍAS DE GASTOS
{top_categorias_gastos}

CUENTAS POR COBRAR
  Saldo vigente + parcial : ${cuentas_por_cobrar:,.2f}  ({ventas_pendientes_count} ventas)
  Saldo vencido           : ${ventas_vencidas:,.2f}  ({ventas_vencidas_count} ventas)

CLIENTES
  Clientes nuevos este período : {clientes_nuevos}
  Clientes nuevos período ant. : {clientes_previos}
────────────────────────────────────────────────────────────

INSTRUCCIONES DE FORMATO
Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura, sin texto extra:
{{
  "resumen_ejecutivo": "<párrafo de 3-5 oraciones en español con el análisis narrativo del período>",
  "alertas": [
    "<alerta 1 breve>",
    "<alerta 2 breve>"
  ],
  "recomendaciones": [
    "<recomendación 1 accionable>",
    "<recomendación 2 accionable>"
  ],
  "kpis": {{
    "semaforo_financiero": "verde|amarillo|rojo",
    "razon_liquidez_comentario": "<comentario corto>",
    "prioridad": "<la acción más urgente en una frase>"
  }}
}}

Criterios para semaforo_financiero:
  verde   → balance_neto > 0 y cuentas vencidas < 10% del total cobrar
  amarillo→ balance_neto > 0 pero alertas moderadas, o cuentas vencidas entre 10%-25%
  rojo    → balance_neto < 0, o cuentas vencidas > 25% del total cobrar
"""

# --------------------------------------------------------------------------- #
# Data gathering                                                                #
# --------------------------------------------------------------------------- #


def _get_financial_data(fecha_inicio: date, fecha_fin: date) -> dict:
    """
    Reúne todos los KPIs financieros del período indicado.
    Sigue el mismo patrón de consultas que app/views.py.
    """
    # ── Helper para período anterior ──────────────────────────────────────── #
    delta = fecha_fin - fecha_inicio + timedelta(days=1)
    prev_inicio = fecha_inicio - delta
    prev_fin = fecha_inicio - timedelta(days=1)

    def _sum_gastos(fi, ff):
        return (
            Gastos.objects.filter(fecha__range=(fi, ff))
            .aggregate(total=Sum("monto"))["total"]
            or Decimal("0")
        )

    def _sum_ventas(fi, ff):
        return (
            Ventas.objects.filter(fecha_salida_manifiesto__range=(fi, ff))
            .aggregate(total=Sum("monto"))["total"]
            or Decimal("0")
        )

    def _sum_compras(fi, ff):
        return (
            Compra.objects.filter(fecha_compra__range=(fi, ff))
            .aggregate(total=Sum("monto_total"))["total"]
            or Decimal("0")
        )

    # Período actual
    total_ventas = _sum_ventas(fecha_inicio, fecha_fin)
    total_gastos = _sum_gastos(fecha_inicio, fecha_fin)
    total_compras = _sum_compras(fecha_inicio, fecha_fin)
    balance_neto = total_ventas - total_gastos - total_compras

    margen_bruto_pct = (
        float(balance_neto / total_ventas * 100) if total_ventas else 0.0
    )

    # Período anterior (para tendencias)
    prev_ventas = _sum_ventas(prev_inicio, prev_fin)
    prev_gastos = _sum_gastos(prev_inicio, prev_fin)
    prev_compras = _sum_compras(prev_inicio, prev_fin)

    def _trend(current, previous):
        if previous == 0:
            return 0.0
        return float((current - previous) / previous * 100)

    tendencia_ventas = _trend(total_ventas, prev_ventas)
    tendencia_gastos = _trend(total_gastos, prev_gastos)
    tendencia_compras = _trend(total_compras, prev_compras)

    # Top categorías de gastos
    top_cats = (
        Gastos.objects.filter(fecha__range=(fecha_inicio, fecha_fin))
        .values("id_cat_gastos__nombre")
        .annotate(total=Sum("monto"))
        .order_by("-total")[:5]
    )
    top_cats_text = "\n".join(
        f"  {i+1}. {item['id_cat_gastos__nombre'] or 'Sin categoría'}: ${float(item['total']):,.2f}"
        for i, item in enumerate(top_cats)
    )

    # Cuentas por cobrar
    qs_vigentes = Ventas.objects.filter(
        estado_cobranza__in=["Pendiente", "Parcial"]
    ).aggregate(total=Sum("monto"), count=Count("id"))
    cuentas_por_cobrar = qs_vigentes["total"] or Decimal("0")
    ventas_pendientes_count = qs_vigentes["count"] or 0

    qs_vencidas = Ventas.objects.filter(estado_cobranza="Vencido").aggregate(
        total=Sum("monto"), count=Count("id")
    )
    ventas_vencidas = qs_vencidas["total"] or Decimal("0")
    ventas_vencidas_count = qs_vencidas["count"] or 0

    # Clientes nuevos — usar datetimes aware para DateTimeField con USE_TZ=True
    from datetime import datetime as dt
    from django.utils.timezone import make_aware

    fi_aware = make_aware(dt.combine(fecha_inicio, dt.min.time()))
    ff_aware = make_aware(dt.combine(fecha_fin, dt.max.time().replace(microsecond=0)))
    pi_aware = make_aware(dt.combine(prev_inicio, dt.min.time()))
    pf_aware = make_aware(dt.combine(prev_fin, dt.max.time().replace(microsecond=0)))

    clientes_nuevos = Cliente.objects.filter(
        fecha_registro__range=(fi_aware, ff_aware)
    ).count()
    clientes_previos = Cliente.objects.filter(
        fecha_registro__range=(pi_aware, pf_aware)
    ).count()

    return {
        "total_ventas": float(total_ventas),
        "total_gastos": float(total_gastos),
        "total_compras": float(total_compras),
        "balance_neto": float(balance_neto),
        "margen_bruto_pct": margen_bruto_pct,
        "tendencia_ventas_pct": tendencia_ventas,
        "tendencia_gastos_pct": tendencia_gastos,
        "tendencia_compras_pct": tendencia_compras,
        "top_categorias_gastos": top_cats_text or "  (sin datos)",
        "cuentas_por_cobrar": float(cuentas_por_cobrar),
        "ventas_pendientes_count": ventas_pendientes_count,
        "ventas_vencidas": float(ventas_vencidas),
        "ventas_vencidas_count": ventas_vencidas_count,
        "clientes_nuevos": clientes_nuevos,
        "clientes_previos": clientes_previos,
    }


# --------------------------------------------------------------------------- #
# LLM chain                                                                     #
# --------------------------------------------------------------------------- #


def _build_chain(model_id: str | None):
    """
    Construye la cadena LangChain: ChatPromptTemplate | LLM | StrOutputParser.
    Reutiliza get_llm_model() del módulo de facturas para consistencia.
    """
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from gastos.services.invoice_recognition_service import get_llm_model

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "Genera el reporte ejecutivo con los datos provistos en el system prompt."),
        ]
    )
    llm = get_llm_model(model_id)
    return prompt | llm | StrOutputParser()


# --------------------------------------------------------------------------- #
# Public API                                                                    #
# --------------------------------------------------------------------------- #


def generar_resumen_ejecutivo(
    fecha_inicio: date,
    fecha_fin: date,
    modelo_ia: str | None = None,
    empresa_nombre: str = "Empresa",
) -> dict:
    """
    Genera un resumen ejecutivo financiero usando IA para el rango de fechas dado.

    Retorna un dict con claves:
      - resumen_ejecutivo (str)
      - alertas (list[str])
      - recomendaciones (list[str])
      - kpis (dict)
      - datos_financieros (dict)  ← KPIs numéricos crudos
      - modelo_usado (str)

    Lanza RuntimeError si la generación falla.
    """
    import os

    # Determinar modelo a usar
    effective_model = modelo_ia or os.getenv("GOOGLE_API_MODEL", "gemini-2.5-flash")

    logger.info(
        "Generando resumen ejecutivo: %s → %s con modelo %s",
        fecha_inicio,
        fecha_fin,
        effective_model,
    )

    # Reunir datos financieros
    datos = _get_financial_data(fecha_inicio, fecha_fin)

    # Nombre legible del período
    periodo_str = f"{fecha_inicio.strftime('%d/%m/%Y')} – {fecha_fin.strftime('%d/%m/%Y')}"

    # Construir prompt completo
    system_prompt = EXECUTIVE_SUMMARY_SYSTEM_PROMPT.format(
        empresa_nombre=empresa_nombre,
        periodo=periodo_str,
        fecha_inicio=fecha_inicio.strftime("%d/%m/%Y"),
        fecha_fin=fecha_fin.strftime("%d/%m/%Y"),
        **datos,
    )

    # Llamar al LLM
    try:
        chain = _build_chain(effective_model)
        raw_output = chain.invoke({"system_prompt": system_prompt})
    except Exception as exc:
        logger.error("Error al llamar al LLM: %s", exc, exc_info=True)
        # Detectar error de cuota agotada (429) para mostrar mensaje claro al usuario
        exc_str = str(exc)
        if "ResourceExhausted" in type(exc).__name__ or "429" in exc_str or "quota" in exc_str.lower():
            raise RuntimeError(
                "Cuota de la API de IA agotada (error 429). "
                "Verifica tu plan y facturación en https://ai.dev/rate-limit. "
                f"Modelo usado: {effective_model}."
            ) from exc
        raise RuntimeError(f"Error al generar resumen con IA: {exc}") from exc

    # Parsear JSON de la respuesta
    try:
        # El modelo puede devolver markdown fences; los removemos
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            )
        resultado = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Respuesta del LLM no es JSON válido, usando texto plano.")
        resultado = {
            "resumen_ejecutivo": raw_output,
            "alertas": [],
            "recomendaciones": [],
            "kpis": {"semaforo_financiero": "amarillo", "razon_liquidez_comentario": "", "prioridad": ""},
        }

    resultado["datos_financieros"] = datos
    resultado["modelo_usado"] = effective_model
    return resultado


def get_periodo_mensual_actual() -> tuple[date, date]:
    """Retorna (primer_dia, ultimo_dia) del mes en curso."""
    hoy = timezone.now().date()
    primer_dia = hoy.replace(day=1)
    # Último día: primer día del mes siguiente − 1
    if hoy.month == 12:
        ultimo_dia = date(hoy.year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(hoy.year, hoy.month + 1, 1) - timedelta(days=1)
    return primer_dia, ultimo_dia


def get_periodo_trimestral_actual() -> tuple[date, date]:
    """Retorna (primer_dia, ultimo_dia) del trimestre en curso."""
    hoy = timezone.now().date()
    trimestre_mes_inicio = ((hoy.month - 1) // 3) * 3 + 1
    primer_dia = date(hoy.year, trimestre_mes_inicio, 1)
    ultimo_mes = trimestre_mes_inicio + 2
    if ultimo_mes == 12:
        ultimo_dia = date(hoy.year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(hoy.year, ultimo_mes + 1, 1) - timedelta(days=1)
    return primer_dia, ultimo_dia


def get_periodo_anual_actual() -> tuple[date, date]:
    """Retorna (primer_dia, ultimo_dia) del año en curso."""
    hoy = timezone.now().date()
    return date(hoy.year, 1, 1), date(hoy.year, 12, 31)
