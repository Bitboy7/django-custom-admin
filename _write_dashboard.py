"""Script that writes the Tailwind-based teal-navy dashboard to templates/admin/index.html"""
import os

DEST = os.path.join(os.path.dirname(__file__), "templates", "admin", "index.html")

TEMPLATE = """\
{% extends 'admin/base.html' %}
{% load i18n %}
{% load humanize %}
{% load static %}
{% load gastos_tags %}
{% block breadcrumbs %}{% endblock %}

{% block title %}
  {% if subtitle %}{{ subtitle }} | {% endif %}{{ title }} | {{ site_title|default:_('Django site admin') }}
{% endblock %}

{% block extrahead %}{{ block.super }}{% endblock %}

{% block styles %}
{{ block.super }}
<style>
  /* ════════════════════════════════════════════════════════
     DASHBOARD  ·  Teal-Navy Financial Theme
     ════════════════════════════════════════════════════════ */
  :root {
    --tl:  #1aadbc;
    --tl2: #0d8fa2;
    --tl3: #c4f0f5;
    --nv:  #1e3a5f;
    --nv2: #2d5282;
    --gr:  #22c55e;
    --rd:  #ef4444;
    --am:  #f59e0b;
    --bg:  #f2f4f7;
    --card:#ffffff;
    --bdr: #dde3ec;
    --txt: #1a2332;
    --mut: #7a8899;
    --sh:  0 1px 5px rgba(0,0,0,.07);
  }
  body { background: var(--bg) !important; }
  #content-main { padding: 18px 22px 40px; max-width: 100% !important; width: 100% !important; box-sizing: border-box; }
  #content { max-width: 100% !important; }
  canvas { max-width: 100%; }

  /* ── Welcome Strip ───────────────────────────────────── */
  .ws { background: linear-gradient(135deg, var(--nv) 0%, var(--tl2) 100%); border-radius: 12px; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; color: #fff; }
  .ws-greet { font-size: 15px; font-weight: 700; letter-spacing: .3px; }
  .ws-sub { font-size: 12px; opacity: .80; margin-top: 2px; }
  .ws-meta { text-align: right; font-size: 11.5px; opacity: .75; }
  .ws-btn { background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.4); color: #fff; border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; text-decoration: none; transition: background .2s; }
  .ws-btn:hover { background: rgba(255,255,255,.30); color: #fff; }

  /* ── KPI Strip ───────────────────────────────────────── */
  .kpi-strip { display: grid; grid-template-columns: repeat(7, 1fr); background: var(--card); border: 1px solid var(--bdr); border-radius: 12px; box-shadow: var(--sh); margin-bottom: 18px; overflow: hidden; }
  .ks-item { padding: 16px 14px; border-right: 1px solid var(--bdr); position: relative; }
  .ks-item:last-child { border-right: none; }
  .ks-lbl { font-size: 11px; color: var(--mut); text-transform: uppercase; letter-spacing: .5px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ks-val { font-size: 19px; font-weight: 700; color: var(--txt); margin: 4px 0 6px; line-height: 1; }
  .ks-bdg { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 20px; white-space: nowrap; }
  .ks-up  { background: #dcfce7; color: #15803d; }
  .ks-dn  { background: #fee2e2; color: #b91c1c; }
  .ks-neu { background: #f1f5f9; color: var(--mut); }
  .ks-tl-bar { position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--tl); }

  /* ── Cards ───────────────────────────────────────────── */
  .card { background: var(--card); border: 1px solid var(--bdr); border-radius: 12px; box-shadow: var(--sh); overflow: hidden; }
  .c-hdr { display: flex; align-items: flex-start; justify-content: space-between; padding: 14px 18px 10px; border-bottom: 1px solid var(--bdr); }
  .c-ttl { font-size: 13.5px; font-weight: 700; color: var(--txt); }
  .c-sub { font-size: 11.5px; color: var(--mut); margin-top: 2px; }
  .c-lnk { font-size: 11px; color: var(--tl); text-decoration: none; font-weight: 600; white-space: nowrap; }
  .c-lnk:hover { color: var(--tl2); }
  .c-body { padding: 14px 18px; }
  .c-lgnd { display: flex; flex-wrap: wrap; gap: 10px; padding: 10px 18px; border-top: 1px solid var(--bdr); font-size: 11px; color: var(--mut); align-items: center; }
  .c-lgnd-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 4px; vertical-align: middle; }

  /* ── Grids ───────────────────────────────────────────── */
  .g3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }
  .g2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px; }
  .g4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }

  /* ── Pills ───────────────────────────────────────────── */
  .pill { display: inline-flex; align-items: center; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px; }
  .pill-gr  { background: #dcfce7; color: #15803d; }
  .pill-rd  { background: #fee2e2; color: #b91c1c; }
  .pill-am  { background: #fef9c3; color: #92400e; }
  .pill-bl  { background: #dbeafe; color: #1d4ed8; }
  .pill-mut { background: #f1f5f9; color: var(--mut); }

  /* ── Stat Cards (footer) ─────────────────────────────── */
  .stat-card { display: flex; align-items: center; gap: 12px; background: var(--card); border: 1px solid var(--bdr); border-radius: 10px; padding: 14px 16px; box-shadow: var(--sh); }
  .stat-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }

  /* ── Quick Access ────────────────────────────────────── */
  .q-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .q-btn { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 7px; padding: 14px 10px; border-radius: 10px; text-decoration: none; background: var(--bg); border: 1px solid var(--bdr); transition: all .2s; }
  .q-btn:hover { background: var(--tl3); border-color: var(--tl); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(26,173,188,.15); }
  .q-icon { width: 36px; height: 36px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 17px; }
  .q-label { font-size: 11.5px; font-weight: 600; color: var(--txt); text-align: center; line-height: 1.3; }

  /* ── Activity Feed ───────────────────────────────────── */
  .act-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--bdr); }
  .act-item:last-child { border-bottom: none; padding-bottom: 0; }
  .act-dot { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }
  .act-desc { font-size: 12.5px; color: var(--txt); line-height: 1.4; }
  .act-meta { font-size: 11px; color: var(--mut); margin-top: 2px; }

  /* ── Toast ───────────────────────────────────────────── */
  .toast-wrap { position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 8px; pointer-events: none; }
  .toast-el { background: #fff; border: 1px solid var(--bdr); border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,.12); padding: 12px 14px; min-width: 240px; max-width: 320px; display: flex; align-items: flex-start; gap: 10px; pointer-events: all; transform: translateX(120%); transition: transform .3s ease; position: relative; overflow: hidden; }
  .toast-el.show { transform: translateX(0); }
  .toast-ico { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }
  .toast-body { flex: 1; min-width: 0; }
  .toast-ttl { font-size: 12.5px; font-weight: 700; color: var(--txt); }
  .toast-msg { font-size: 11.5px; color: var(--mut); margin-top: 2px; line-height: 1.4; }
  .toast-cls { font-size: 14px; color: var(--mut); cursor: pointer; background: none; border: none; padding: 0; line-height: 1; }
  .toast-prog { position: absolute; bottom: 0; left: 0; height: 3px; background: var(--tl); border-radius: 0 0 10px 10px; animation: toastProg 4.2s linear forwards; }
  @keyframes toastProg { from { width: 100%; } to { width: 0%; } }

  /* ── Responsive ──────────────────────────────────────── */
  @media (max-width: 1200px) {
    .kpi-strip { grid-template-columns: repeat(4, 1fr); }
    .ks-item:nth-child(4) { border-right: none; }
    .ks-item:nth-child(n+5) { border-top: 1px solid var(--bdr); }
  }
  @media (max-width: 900px) {
    .g3, .g2 { grid-template-columns: 1fr; }
    .g4 { grid-template-columns: repeat(2, 1fr); }
  }
  @media (max-width: 600px) {
    .kpi-strip { grid-template-columns: repeat(2, 1fr); }
    .ks-item:nth-child(even) { border-right: none; }
    .ks-item:nth-child(n+3) { border-top: 1px solid var(--bdr); }
    .g4 { grid-template-columns: 1fr; }
    .ws { flex-direction: column; gap: 12px; align-items: flex-start; }
  }
</style>
{% endblock %}

{% block content %}
<div id="dashMain">

  <!-- ═══ Welcome Strip ═══════════════════════════════════ -->
  <div class="ws">
    <div>
      <div class="ws-greet">
        &#128075; ¡Bienvenido,
        {% if request.user.get_full_name %}{{ request.user.get_full_name }}{% else %}{{ request.user.username }}{% endif %}!
      </div>
      <div class="ws-sub">{{ current_month_name }} {{ current_year }} &mdash; Panel de Control Ejecutivo</div>
    </div>
    <div style="display:flex;align-items:center;gap:14px;flex-shrink:0">
      <div class="ws-meta">
        <div>Última actualización</div>
        <div style="font-weight:700;font-size:12.5px">{{ last_update }}</div>
      </div>
      <a href="javascript:location.reload()" class="ws-btn">&#8635; Actualizar</a>
    </div>
  </div>

  <!-- ═══ KPI Strip ═══════════════════════════════════════ -->
  <div class="kpi-strip">

    <!-- 1: Ventas del Mes -->
    <div class="ks-item">
      <div class="ks-tl-bar"></div>
      <div class="ks-lbl">Ventas del Mes</div>
      <div class="ks-val">{{ total_ventas|us_currency:0 }}</div>
      <span class="ks-bdg {% if ventas_trend >= 0 %}ks-up{% else %}ks-dn{% endif %}">
        {% if ventas_trend >= 0 %}&#9650;{% else %}&#9660;{% endif %} {{ ventas_trend|floatformat:1 }}%
      </span>
    </div>

    <!-- 2: Gastos del Mes -->
    <div class="ks-item">
      <div class="ks-tl-bar" style="background:var(--nv)"></div>
      <div class="ks-lbl">Gastos del Mes</div>
      <div class="ks-val">{{ total_gastos|us_currency:0 }}</div>
      <span class="ks-bdg {% if gastos_trend <= 0 %}ks-up{% else %}ks-dn{% endif %}">
        {% if gastos_trend <= 0 %}&#9660;{% else %}&#9650;{% endif %} {{ gastos_trend|floatformat:1 }}%
      </span>
    </div>

    <!-- 3: Balance Neto -->
    <div class="ks-item">
      <div class="ks-tl-bar" style="background:{% if balance_neto >= 0 %}var(--gr){% else %}var(--rd){% endif %}"></div>
      <div class="ks-lbl">Balance Neto</div>
      <div class="ks-val" style="color:{% if balance_neto >= 0 %}var(--gr){% else %}var(--rd){% endif %}">{{ balance_neto|us_currency:0 }}</div>
      <span class="ks-bdg {% if balance_trend >= 0 %}ks-up{% else %}ks-dn{% endif %}">
        {% if balance_trend >= 0 %}&#9650;{% else %}&#9660;{% endif %} {{ balance_trend|floatformat:1 }}%
      </span>
    </div>

    <!-- 4: Margen Neto % (JS computed) -->
    <div class="ks-item">
      <div class="ks-tl-bar" style="background:var(--tl2)"></div>
      <div class="ks-lbl">Margen Neto</div>
      <div class="ks-val" id="kpiMargen">—</div>
      <span class="ks-bdg ks-neu" id="kpiMargenBdg">calculando</span>
    </div>

    <!-- 5: CxC Vigentes -->
    <div class="ks-item">
      <div class="ks-tl-bar" style="background:var(--am)"></div>
      <div class="ks-lbl">CxC Vigentes</div>
      <div class="ks-val">{{ ventas_vigentes|us_currency:0 }}</div>
      <span class="ks-bdg ks-neu">{{ ventas_vigentes_count }} fact.</span>
    </div>

    <!-- 6: CxC Vencidas -->
    <div class="ks-item">
      <div class="ks-tl-bar" style="background:var(--rd)"></div>
      <div class="ks-lbl">CxC Vencidas</div>
      <div class="ks-val" style="color:var(--rd)">{{ ventas_vencidas|us_currency:0 }}</div>
      <span class="ks-bdg ks-dn">{{ ventas_vencidas_count }} fact.</span>
    </div>

    <!-- 7: Clientes Activos -->
    <div class="ks-item">
      <div class="ks-tl-bar" style="background:var(--nv2)"></div>
      <div class="ks-lbl">Clientes Activos</div>
      <div class="ks-val">{{ total_clientes }}</div>
      <span class="ks-bdg {% if clientes_trend >= 0 %}ks-up{% else %}ks-dn{% endif %}">
        {% if clientes_trend >= 0 %}+{% endif %}{{ clientes_nuevos }} nuevos
      </span>
    </div>

  </div><!-- /kpi-strip -->

  <!-- ═══ Row 1 · 3 Charts ════════════════════════════════ -->
  <div class="g3">

    <!-- Chart 1: Ventas por Mes -->
    <div class="card">
      <div class="c-hdr">
        <div>
          <div class="c-ttl">Ventas por Mes</div>
          <div class="c-sub">Facturación mensual</div>
        </div>
        <a href="/admin/ventas/ventas/" class="c-lnk">Ver todo &#8250;</a>
      </div>
      <div class="c-body" style="height:200px;position:relative">
        <canvas id="ventasBarChart"></canvas>
      </div>
    </div>

    <!-- Chart 2: Cartera CxC Donut -->
    <div class="card">
      <div class="c-hdr">
        <div>
          <div class="c-ttl">Cartera de Cobro</div>
          <div class="c-sub">Vigente vs Vencida</div>
        </div>
      </div>
      <div class="c-body" style="height:180px;position:relative;display:flex;align-items:center;justify-content:center">
        <canvas id="carteraDonut" style="max-height:180px"></canvas>
      </div>
      <div class="c-lgnd">
        <span><span class="c-lgnd-dot" style="background:#1aadbc"></span>Vigente</span>
        <span><span class="c-lgnd-dot" style="background:#1e3a5f"></span>Vencida</span>
        <span style="margin-left:auto;font-weight:700;color:var(--txt)" id="kpiMorosidad">—</span>&nbsp;morosidad
      </div>
    </div>

    <!-- Chart 3: Gastos por Categoría Donut -->
    <div class="card">
      <div class="c-hdr">
        <div>
          <div class="c-ttl">Gastos por Categoría</div>
          <div class="c-sub">Distribución actual</div>
        </div>
        <a href="/admin/gastos/gasto/" class="c-lnk">Ver todo &#8250;</a>
      </div>
      <div class="c-body" style="height:180px;position:relative;display:flex;align-items:center;justify-content:center">
        <canvas id="gastosDonut" style="max-height:180px"></canvas>
      </div>
      <div class="c-lgnd" id="gastosLgnd"></div>
    </div>

  </div><!-- /g3 -->

  <!-- ═══ Row 2 · 2 Charts ════════════════════════════════ -->
  <div class="g2">

    <!-- Chart 4: Tendencias Ventas vs Gastos -->
    <div class="card">
      <div class="c-hdr">
        <div>
          <div class="c-ttl">Tendencias</div>
          <div class="c-sub">Ventas vs Gastos &mdash; últimos 6 meses</div>
        </div>
      </div>
      <div class="c-body" style="height:230px;position:relative">
        <canvas id="tendenciasChart"></canvas>
      </div>
    </div>

    <!-- Chart 5: Balance Mensual -->
    <div class="card">
      <div class="c-hdr">
        <div>
          <div class="c-ttl">Balance Mensual</div>
          <div class="c-sub">Resultado neto por mes</div>
        </div>
      </div>
      <div class="c-body" style="height:230px;position:relative">
        <canvas id="balanceBarChart"></canvas>
      </div>
    </div>

  </div><!-- /g2 -->

  <!-- ═══ Row 3 · Activity + Quick Access ════════════════ -->
  <div class="g2">

    <!-- Activity Feed -->
    <div class="card">
      <div class="c-hdr">
        <div>
          <div class="c-ttl">Actividad Reciente</div>
          <div class="c-sub">Últimas acciones en el sistema</div>
        </div>
      </div>
      <div class="c-body">
        {% for act in recent_activities %}
        <div class="act-item">
          <div class="act-dot" style="background:{{ act.color }}20;color:{{ act.color }}">{{ act.icon }}</div>
          <div style="flex:1;min-width:0">
            <div class="act-desc">{{ act.description }}</div>
            <div class="act-meta">{{ act.user }} &middot; {{ act.timestamp }}</div>
          </div>
          <span class="pill pill-{% if act.status == 'success' %}gr{% elif act.status == 'warning' %}am{% elif act.status == 'error' %}rd{% else %}mut{% endif %}" style="flex-shrink:0">
            {{ act.status }}
          </span>
        </div>
        {% empty %}
        <p style="color:var(--mut);font-size:13px;text-align:center;padding:20px 0">Sin actividad reciente</p>
        {% endfor %}
      </div>
    </div>

    <!-- Quick Access -->
    <div class="card">
      <div class="c-hdr">
        <div>
          <div class="c-ttl">Acceso Rápido</div>
          <div class="c-sub">Módulos principales</div>
        </div>
      </div>
      <div class="c-body">
        <div class="q-grid">
          <a href="/admin/ventas/ventas/add/" class="q-btn">
            <div class="q-icon" style="background:#dcfce7;color:#15803d">&#128196;</div>
            <div class="q-label">Nueva Venta</div>
          </a>
          <a href="/admin/gastos/gasto/add/" class="q-btn">
            <div class="q-icon" style="background:#fee2e2;color:#b91c1c">&#128184;</div>
            <div class="q-label">Nuevo Gasto</div>
          </a>
          <a href="/admin/ventas/ventas/?estado_cobranza__in=Vencida" class="q-btn">
            <div class="q-icon" style="background:#fef9c3;color:#92400e">&#9888;&#65039;</div>
            <div class="q-label">CxC Vencidas</div>
          </a>
          <a href="/admin/catalogo/" class="q-btn">
            <div class="q-icon" style="background:#dbeafe;color:#1d4ed8">&#128230;</div>
            <div class="q-label">Catálogo</div>
          </a>
          <a href="/admin/compras/compra/add/" class="q-btn">
            <div class="q-icon" style="background:#ede9fe;color:#7c3aed">&#128722;</div>
            <div class="q-label">Nueva Compra</div>
          </a>
          <a href="/admin/auditoria/" class="q-btn">
            <div class="q-icon" style="background:#f0fdf4;color:#15803d">&#128269;</div>
            <div class="q-label">Auditoría</div>
          </a>
        </div>
      </div>
    </div>

  </div><!-- /g2 row3 -->

  <!-- ═══ Footer Stats ════════════════════════════════════ -->
  <div class="g4">
    <div class="stat-card">
      <div class="stat-icon" style="background:#dbeafe;color:#1d4ed8">&#128100;</div>
      <div>
        <div style="font-size:22px;font-weight:700;color:var(--txt)">{{ total_users }}</div>
        <div style="font-size:11.5px;color:var(--mut)">Usuarios activos</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background:#dcfce7;color:#15803d">&#128230;</div>
      <div>
        <div style="font-size:22px;font-weight:700;color:var(--txt)">{{ productos_vendidos }}</div>
        <div style="font-size:11.5px;color:var(--mut)">Productos vendidos</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background:#fef9c3;color:#92400e">&#127991;&#65039;</div>
      <div>
        <div style="font-size:22px;font-weight:700;color:var(--txt)">{{ total_categorias }}</div>
        <div style="font-size:11.5px;color:var(--mut)">Categorías activas</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background:var(--tl3);color:var(--tl2)">&#128197;</div>
      <div>
        <div style="font-size:13px;font-weight:700;color:var(--txt);line-height:1.3">{{ last_update }}</div>
        <div style="font-size:11.5px;color:var(--mut)">Última actualización</div>
      </div>
    </div>
  </div><!-- /g4 footer -->

</div><!-- /dashMain -->

<!-- ════ Toast container ════════════════════════════════════ -->
<div class="toast-wrap" id="toastWrap"></div>

<!-- ════ Chart.js ════════════════════════════════════════════ -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<script>
(function () {
  'use strict';

  /* ── Paleta ────────────────────────────────────────────── */
  const TEAL = '#1aadbc', NAVY = '#1e3a5f';
  const PAL  = ['#1aadbc','#1e3a5f','#5dd0d7','#2d6a9f','#82dce0','#4e8bc4','#b3edf2','#35435a'];

  /* ── Datos desde Django ─────────────────────────────────── */
  const meses   = {{ meses_labels|safe }};
  const ventas  = {{ ventas_mensuales|safe }};
  const gastos  = {{ gastos_mensuales|safe }};
  const catLbls = {{ gastos_categorias_labels|safe }};
  const catData = {{ gastos_categorias_data|safe }};
  const cxcVig  = parseFloat('{{ ventas_vigentes }}')  || 0;
  const cxcVen  = parseFloat('{{ ventas_vencidas }}')  || 0;
  const tvTotal = parseFloat('{{ total_ventas }}')     || 0;
  const tvBal   = parseFloat('{{ balance_neto }}')     || 0;

  /* ── KPIs calculados ────────────────────────────────────── */
  const margenPct    = tvTotal > 0 ? (tvBal / tvTotal * 100) : 0;
  const morosPct     = (cxcVig + cxcVen) > 0 ? (cxcVen / (cxcVig + cxcVen) * 100) : 0;

  const elMargen  = document.getElementById('kpiMargen');
  const elMBdg    = document.getElementById('kpiMargenBdg');
  const elMoros   = document.getElementById('kpiMorosidad');

  if (elMargen) {
    elMargen.textContent = margenPct.toFixed(1) + '%';
    elMBdg.className = 'ks-bdg ' + (margenPct >= 0 ? 'ks-up' : 'ks-dn');
    elMBdg.textContent = (margenPct >= 0 ? '▲ ' : '▼ ') + Math.abs(margenPct).toFixed(1) + '%';
  }
  if (elMoros) elMoros.textContent = morosPct.toFixed(1) + '%';

  /* ── Chart defaults ─────────────────────────────────────── */
  Chart.defaults.font.family = "'Inter','Segoe UI',system-ui,sans-serif";
  Chart.defaults.font.size   = 11;
  Chart.defaults.color       = '#7a8899';

  const baseOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } }
  };

  /* ── 1. Ventas por Mes (Bar) ────────────────────────────── */
  new Chart('ventasBarChart', {
    type: 'bar',
    data: {
      labels: meses,
      datasets: [{
        label: 'Ventas',
        data: ventas,
        backgroundColor: ventas.map((_v, i) => i === ventas.length - 1 ? TEAL : TEAL + '70'),
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      ...baseOpts,
      scales: {
        y: { grid: { color: '#eef1f5' }, ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k' } },
        x: { grid: { display: false } }
      }
    }
  });

  /* ── 2. Cartera Donut ───────────────────────────────────── */
  new Chart('carteraDonut', {
    type: 'doughnut',
    data: {
      labels: ['Vigente', 'Vencida'],
      datasets: [{
        data: [cxcVig, cxcVen],
        backgroundColor: [TEAL, NAVY],
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 8
      }]
    },
    options: {
      ...baseOpts,
      cutout: '65%',
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ' ' + ctx.label + ': $' + ctx.raw.toLocaleString() } }
      }
    }
  });

  /* ── 3. Gastos por Categoría Donut ─────────────────────── */
  new Chart('gastosDonut', {
    type: 'doughnut',
    data: {
      labels: catLbls,
      datasets: [{
        data: catData,
        backgroundColor: PAL.slice(0, catData.length),
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 8
      }]
    },
    options: { ...baseOpts, cutout: '60%' }
  });

  /* Leyenda dinámica para donut de gastos */
  const lgndEl = document.getElementById('gastosLgnd');
  if (lgndEl && catLbls.length) {
    lgndEl.innerHTML = catLbls
      .map((l, i) => '<span><span class="c-lgnd-dot" style="background:' + PAL[i % PAL.length] + '"></span>' + l + '</span>')
      .join('');
  }

  /* ── 4. Tendencias V vs G (Line) ────────────────────────── */
  new Chart('tendenciasChart', {
    type: 'line',
    data: {
      labels: meses,
      datasets: [
        {
          label: 'Ventas',
          data: ventas,
          borderColor: TEAL,
          backgroundColor: TEAL + '18',
          borderWidth: 2.5,
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: TEAL
        },
        {
          label: 'Gastos',
          data: gastos,
          borderColor: NAVY,
          backgroundColor: NAVY + '12',
          borderWidth: 2.5,
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: NAVY
        }
      ]
    },
    options: {
      ...baseOpts,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { usePointStyle: true, boxWidth: 8, padding: 16 }
        }
      },
      scales: {
        y: { grid: { color: '#eef1f5' }, ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k' } },
        x: { grid: { display: false } }
      }
    }
  });

  /* ── 5. Balance Mensual (Bar, verde/rojo por signo) ─────── */
  const balance = ventas.map((v, i) => v - (gastos[i] || 0));
  new Chart('balanceBarChart', {
    type: 'bar',
    data: {
      labels: meses,
      datasets: [{
        label: 'Balance',
        data: balance,
        backgroundColor: balance.map(v => v >= 0 ? '#22c55e70' : '#ef444470'),
        borderColor:      balance.map(v => v >= 0 ? '#22c55e'   : '#ef4444'),
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      ...baseOpts,
      scales: {
        y: { grid: { color: '#eef1f5' }, ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k' } },
        x: { grid: { display: false } }
      }
    }
  });

  /* ── Toast helper ───────────────────────────────────────── */
  function showToast(title, msg, type) {
    const icons  = { success: '&#9989;', warning: '&#9888;&#65039;', error: '&#10060;', info: '&#8505;&#65039;' };
    const colors = { success: '#22c55e', warning: '#f59e0b', error: '#ef4444', info: '#1aadbc' };
    const t = type || 'info';
    const el = document.createElement('div');
    el.className = 'toast-el';
    el.innerHTML =
      '<div class="toast-ico" style="background:' + colors[t] + '20;color:' + colors[t] + '">' + (icons[t] || icons.info) + '</div>' +
      '<div class="toast-body">' +
        '<div class="toast-ttl">' + title + '</div>' +
        '<div class="toast-msg">'  + msg   + '</div>' +
      '</div>' +
      '<button class="toast-cls" onclick="this.closest(\'.toast-el\').remove()">&#10005;</button>' +
      '<div class="toast-prog"></div>';
    document.getElementById('toastWrap').appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(function () {
      el.classList.remove('show');
      setTimeout(function () { el.remove(); }, 380);
    }, 4400);
  }

  /* Bienvenida al cargar */
  window.addEventListener('load', function () {
    showToast('Dashboard cargado', 'Datos actualizados correctamente.', 'success');
  });

})();
</script>
{% endblock %}
"""

with open(DEST, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(TEMPLATE)

lines = TEMPLATE.count("\n") + 1
print(f"Wrote {lines} lines to {DEST}")
