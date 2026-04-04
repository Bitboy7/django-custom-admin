"""
Seed — Ventas Q1 2025 (Enero, Febrero, Marzo)
==============================================
Inserta ventas coherentes para Agrícola de la Costa:
  • Exportación de mango (en USD) a clientes en EE.UU.
  • Ventas nacionales (en MXN) a clientes en México
  • Mix de contado (pagado) y crédito (pendiente/parcial/vencido)
  • Incluye registros tipo MAQUILA para la sección Maquila x Cobrar

Tipo de cambio referencia Q1-2025: ~$17.90 MXN/USD  (datos Banxico)
Precios caja promedio (exportación FOB Tapachula):
  Manila:       $10.50 USD/caja  (4 kg)
  Ataulfo:      $13.00 USD/caja
  Tommy Arkins: $9.00  USD/caja
  Haden:        $10.00 USD/caja

Ejecutar:
    py manage.py shell < seed_ventas_q1_2025.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from decimal import Decimal
from datetime import date, timedelta
from djmoney.money import Money
from ventas.models import Ventas, Cliente, Agente, TerminoCredito
from catalogo.models import Sucursal, Producto
from gastos.models import Cuenta

# ---------------------------------------------------------------------------
# Referencias a objetos existentes en BD
# ---------------------------------------------------------------------------
# Clientes
PANORAMA      = Cliente.objects.get(id=1)   # Panorama LTD (USA)
AGROMOD       = Cliente.objects.get(id=2)   # Agromod Produce INC (USA)
GM_PRODUCE    = Cliente.objects.get(id=3)   # GM Produce Sales LLC (USA)
MARABELLA     = Cliente.objects.get(id=4)   # Marabella Produce LLC (USA, Mixto)
AGROCARICA    = Cliente.objects.get(id=5)   # Agrocarica SA DE CV (MX)
FRUTAS5       = Cliente.objects.get(id=6)   # Frutas Frescas 5 hermanos
INTEGRADORA   = Cliente.objects.get(id=7)   # Integradora Frutas Finas

# Agentes
LIBRADO = Agente.objects.get(id=1)
VIDAL   = Agente.objects.get(id=2)

# Sucursales
TAPACHULA    = Sucursal.objects.get(id=1)
SLL          = Sucursal.objects.get(id=2)   # San Luis La Loma
APATZINGAN   = Sucursal.objects.get(id=4)
NAYARIT      = Sucursal.objects.get(id=5)
ESCUINAPA    = Sucursal.objects.get(id=6)
NAYARIT_HAD  = Sucursal.objects.get(id=7)   # Nayarit Haden Gustavo

# Productos
MANILA       = Producto.objects.get(id=1)
ATAULFO      = Producto.objects.get(id=2)
TOMMY        = Producto.objects.get(id=3)
HADEN        = Producto.objects.get(id=4)
KEITT        = Producto.objects.get(id=5)

# Cuentas
CTA_BBVA     = Cuenta.objects.get(id=4)    # BBVA / Tapachula
CTA_SNTD_TAP = Cuenta.objects.get(id=5)    # Santander / Tapachula
CTA_SNTD_NAY = Cuenta.objects.get(id=6)    # Santander / Nayarit
CTA_SNTD_HAD = Cuenta.objects.get(id=7)    # Santander / Nayarit Haden
CTA_MONEX    = Cuenta.objects.get(id=8)    # Monex / Tapachula

# Término de crédito
NET60 = TerminoCredito.objects.get(id=1)

TC = Decimal('17.90')   # Tipo de cambio referencia Q1 2025

# ---------------------------------------------------------------------------
# Definición de ventas  (montos USD para exportación, MXN para nacional)
# ---------------------------------------------------------------------------
# Estructura de cada dict:
#   fecha_salida_manifiesto, fecha_deposito, agente_id, pedimento, carga, PO,
#   producto, cantidad, monto (Money), moneda_venta, tipo_cambio,
#   descripcion, cliente, sucursal_id, cuenta, tipo_venta,
#   modalidad_pago, termino_credito, monto_pagado, estado_cobranza,
#   tipo_registro
#
# Para CONTADO: monto_pagado = monto, estado = Pagado  (lo hace el save() auto)
# Para CREDITO: monto_pagado manual, estado manual
# ---------------------------------------------------------------------------

VENTAS_DATA = [

    # =========================================================
    # ENERO 2025 — Exportaciones de Ataulfo y Manila (inicio temporada)
    # =========================================================

    # Panorama LTD — Manila Tapachula — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 1,  8),
        fecha_deposito=date(2025, 1, 10),
        agente_id=LIBRADO, pedimento='25-TAP-0001', carga='C001-ENE25',
        PO='PO-PANO-0101',
        producto=MANILA, cantidad='1,100 cajas',
        monto=Money(Decimal('11550.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Manila temporada alta Ene-25',
        cliente=PANORAMA, sucursal_id=TAPACHULA, cuenta=CTA_SNTD_TAP,
        tipo_venta='Exportación', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # Agromod — Ataulfo Tapachula — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 1, 10),
        fecha_deposito=date(2025, 1, 13),
        agente_id=LIBRADO, pedimento='25-TAP-0002', carga='C002-ENE25',
        PO='PO-AGRO-0102',
        producto=ATAULFO, cantidad='900 cajas',
        monto=Money(Decimal('11700.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Ataulfo primera corrida Ene-25',
        cliente=AGROMOD, sucursal_id=TAPACHULA, cuenta=CTA_MONEX,
        tipo_venta='Exportación', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # GM Produce — Tommy SLL — CRÉDITO Net 60 — PENDIENTE (vencido Apr-2025)
    dict(
        fecha_salida_manifiesto=date(2025, 1, 15),
        fecha_deposito=date(2025, 1, 17),
        agente_id=VIDAL, pedimento='25-SLL-0001', carga='C003-ENE25',
        PO='PO-GM-0103',
        producto=TOMMY, cantidad='1,200 cajas',
        monto=Money(Decimal('10800.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Tommy Arkins SLL crédito 60d',
        cliente=GM_PRODUCE, sucursal_id=SLL, cuenta=CTA_BBVA,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('0.00'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='VENTA',
    ),

    # Marabella — Manila Nayarit — CRÉDITO Net 60 — PARCIAL (vencido)
    dict(
        fecha_salida_manifiesto=date(2025, 1, 20),
        fecha_deposito=date(2025, 1, 22),
        agente_id=VIDAL, pedimento='25-NAY-0001', carga='C004-ENE25',
        PO='PO-MAR-0104',
        producto=MANILA, cantidad='1,050 cajas',
        monto=Money(Decimal('11025.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Manila Nayarit crédito 60d',
        cliente=MARABELLA, sucursal_id=NAYARIT, cuenta=CTA_SNTD_NAY,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('5512.50'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='VENTA',
    ),

    # Agrocarica — Ataulfo TAPACHULA — Nacional CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 1, 24),
        fecha_deposito=date(2025, 1, 25),
        agente_id=LIBRADO, pedimento=None, carga='C005-ENE25',
        PO=None,
        producto=ATAULFO, cantidad='300 cajas',
        monto=Money(Decimal('66000.00'), 'MXN'),
        moneda_venta='MXN', tipo_cambio=Decimal('1.0000'),
        descripcion='Ataulfo mercado nacional Ene-25',
        cliente=AGROCARICA, sucursal_id=TAPACHULA, cuenta=CTA_SNTD_TAP,
        tipo_venta='Nacional', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # =========================================================
    # FEBRERO 2025 — Exportaciones de Ataulfo peak season
    # =========================================================

    # Panorama — Ataulfo Tapachula — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 2,  3),
        fecha_deposito=date(2025, 2,  5),
        agente_id=LIBRADO, pedimento='25-TAP-0010', carga='C010-FEB25',
        PO='PO-PANO-0201',
        producto=ATAULFO, cantidad='1,400 cajas',
        monto=Money(Decimal('18200.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Ataulfo peak season Feb-25',
        cliente=PANORAMA, sucursal_id=TAPACHULA, cuenta=CTA_SNTD_TAP,
        tipo_venta='Exportación', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # Agromod — Ataulfo Escuinapa — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 2,  7),
        fecha_deposito=date(2025, 2, 10),
        agente_id=VIDAL, pedimento='25-ESC-0001', carga='C011-FEB25',
        PO='PO-AGRO-0202',
        producto=ATAULFO, cantidad='1,100 cajas',
        monto=Money(Decimal('14300.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Ataulfo Escuinapa Feb-25',
        cliente=AGROMOD, sucursal_id=ESCUINAPA, cuenta=CTA_SNTD_NAY,
        tipo_venta='Exportación', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # GM Produce — Manila Nayarit — CRÉDITO Net 60 — PENDIENTE (vencido abr-25)
    dict(
        fecha_salida_manifiesto=date(2025, 2, 12),
        fecha_deposito=date(2025, 2, 14),
        agente_id=VIDAL, pedimento='25-NAY-0010', carga='C012-FEB25',
        PO='PO-GM-0203',
        producto=MANILA, cantidad='1,300 cajas',
        monto=Money(Decimal('13650.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Manila Nayarit crédito 60d Feb-25',
        cliente=GM_PRODUCE, sucursal_id=NAYARIT, cuenta=CTA_SNTD_NAY,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('0.00'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='VENTA',
    ),

    # Marabella — Haden Nayarit Haden — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 2, 18),
        fecha_deposito=date(2025, 2, 19),
        agente_id=VIDAL, pedimento='25-NAY-0011', carga='C013-FEB25',
        PO='PO-MAR-0204',
        producto=HADEN, cantidad='980 cajas',
        monto=Money(Decimal('9800.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Haden Nayarit contado Feb-25',
        cliente=MARABELLA, sucursal_id=NAYARIT_HAD, cuenta=CTA_SNTD_HAD,
        tipo_venta='Exportación', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # Frutas 5 hermanos — Ataulfo nacional — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 2, 20),
        fecha_deposito=date(2025, 2, 21),
        agente_id=LIBRADO, pedimento=None, carga='C014-FEB25',
        PO=None,
        producto=ATAULFO, cantidad='500 cajas',
        monto=Money(Decimal('115000.00'), 'MXN'),
        moneda_venta='MXN', tipo_cambio=Decimal('1.0000'),
        descripcion='Ataulfo mercado nacional Chiapas Feb-25',
        cliente=FRUTAS5, sucursal_id=TAPACHULA, cuenta=CTA_SNTD_TAP,
        tipo_venta='Nacional', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # Integradora Soconusco — Tommy Tapachula — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 2, 25),
        fecha_deposito=date(2025, 2, 26),
        agente_id=LIBRADO, pedimento=None, carga='C015-FEB25',
        PO=None,
        producto=TOMMY, cantidad='400 cajas',
        monto=Money(Decimal('84000.00'), 'MXN'),
        moneda_venta='MXN', tipo_cambio=Decimal('1.0000'),
        descripcion='Tommy nacional Soconusco Feb-25',
        cliente=INTEGRADORA, sucursal_id=TAPACHULA, cuenta=CTA_SNTD_TAP,
        tipo_venta='Nacional', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # =========================================================
    # MARZO 2025 — Haden + Tommy exportación temporada alta
    # =========================================================

    # Panorama — Tommy Nayarit — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 3,  4),
        fecha_deposito=date(2025, 3,  6),
        agente_id=LIBRADO, pedimento='25-NAY-0020', carga='C020-MAR25',
        PO='PO-PANO-0301',
        producto=TOMMY, cantidad='1,500 cajas',
        monto=Money(Decimal('13500.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Tommy Nayarit temporada Mar-25',
        cliente=PANORAMA, sucursal_id=NAYARIT, cuenta=CTA_SNTD_NAY,
        tipo_venta='Exportación', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # Agromod — Haden Nayarit — CRÉDITO Net 60 — PENDIENTE (vencido May-25)
    dict(
        fecha_salida_manifiesto=date(2025, 3, 10),
        fecha_deposito=date(2025, 3, 12),
        agente_id=VIDAL, pedimento='25-NAY-0021', carga='C021-MAR25',
        PO='PO-AGRO-0302',
        producto=HADEN, cantidad='1,200 cajas',
        monto=Money(Decimal('12000.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Haden crédito 60d Mar-25',
        cliente=AGROMOD, sucursal_id=NAYARIT_HAD, cuenta=CTA_SNTD_HAD,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('4000.00'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='VENTA',
    ),

    # GM Produce — Ataulfo Escuinapa — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 3, 14),
        fecha_deposito=date(2025, 3, 17),
        agente_id=VIDAL, pedimento='25-ESC-0010', carga='C022-MAR25',
        PO='PO-GM-0303',
        producto=ATAULFO, cantidad='1,000 cajas',
        monto=Money(Decimal('13000.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Ataulfo Escuinapa Mar-25',
        cliente=GM_PRODUCE, sucursal_id=ESCUINAPA, cuenta=CTA_SNTD_NAY,
        tipo_venta='Exportación', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # Marabella — Tommy Apatzingán — CRÉDITO Net 60 — PARCIAL (vencido)
    dict(
        fecha_salida_manifiesto=date(2025, 3, 18),
        fecha_deposito=date(2025, 3, 20),
        agente_id=LIBRADO, pedimento='25-APZ-0001', carga='C023-MAR25',
        PO='PO-MAR-0304',
        producto=TOMMY, cantidad='1,100 cajas',
        monto=Money(Decimal('9900.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Tommy Apatzingán crédito 60d Mar-25',
        cliente=MARABELLA, sucursal_id=APATZINGAN, cuenta=CTA_BBVA,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('3300.00'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='VENTA',
    ),

    # Agrocarica — Haden nacional — CONTADO
    dict(
        fecha_salida_manifiesto=date(2025, 3, 22),
        fecha_deposito=date(2025, 3, 24),
        agente_id=LIBRADO, pedimento=None, carga='C024-MAR25',
        PO=None,
        producto=HADEN, cantidad='350 cajas',
        monto=Money(Decimal('98000.00'), 'MXN'),
        moneda_venta='MXN', tipo_cambio=Decimal('1.0000'),
        descripcion='Haden mercado nacional Mar-25',
        cliente=AGROCARICA, sucursal_id=TAPACHULA, cuenta=CTA_SNTD_TAP,
        tipo_venta='Nacional', modalidad_pago='Contado',
        tipo_registro='VENTA',
    ),

    # =========================================================
    # MAQUILA — Tres registros distribuidos Q1
    # =========================================================

    # Panorama — Maquila Manila Tapachula — CRÉDITO — PENDIENTE (vencido)
    dict(
        fecha_salida_manifiesto=date(2025, 1, 28),
        fecha_deposito=date(2025, 1, 30),
        agente_id=LIBRADO, pedimento='25-MAQTAP-001', carga='MQ001-ENE25',
        PO='PO-PANO-MQ01',
        producto=MANILA, cantidad='600 cajas',
        monto=Money(Decimal('3600.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Maquila Manila Tapachula Ene-25',
        cliente=PANORAMA, sucursal_id=TAPACHULA, cuenta=CTA_MONEX,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('0.00'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='MAQUILA',
    ),

    # Agromod — Maquila Ataulfo Nayarit — CRÉDITO — PARCIAL (vencido)
    dict(
        fecha_salida_manifiesto=date(2025, 2, 14),
        fecha_deposito=date(2025, 2, 17),
        agente_id=VIDAL, pedimento='25-MAQNAY-001', carga='MQ002-FEB25',
        PO='PO-AGRO-MQ02',
        producto=ATAULFO, cantidad='500 cajas',
        monto=Money(Decimal('4500.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Maquila Ataulfo Nayarit Feb-25',
        cliente=AGROMOD, sucursal_id=NAYARIT, cuenta=CTA_SNTD_NAY,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('2000.00'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='MAQUILA',
    ),

    # GM Produce — Maquila Tommy Escuinapa — CRÉDITO — PENDIENTE
    dict(
        fecha_salida_manifiesto=date(2025, 3, 26),
        fecha_deposito=date(2025, 3, 28),
        agente_id=VIDAL, pedimento='25-MAQESC-001', carga='MQ003-MAR25',
        PO='PO-GM-MQ03',
        producto=TOMMY, cantidad='700 cajas',
        monto=Money(Decimal('4900.00'), 'USD'),
        moneda_venta='USD', tipo_cambio=TC,
        descripcion='Maquila Tommy Escuinapa Mar-25',
        cliente=GM_PRODUCE, sucursal_id=ESCUINAPA, cuenta=CTA_SNTD_NAY,
        tipo_venta='Exportación', modalidad_pago='Credito',
        termino_credito=NET60,
        monto_pagado=Money(Decimal('0.00'), 'USD'),
        estado_cobranza='Vencido',
        tipo_registro='MAQUILA',
    ),
]


# ---------------------------------------------------------------------------
# Inserción en BD
# ---------------------------------------------------------------------------

def insertar_ventas():
    creadas = 0
    omitidas = 0

    for d in VENTAS_DATA:
        tipo = d.get('tipo_registro', 'VENTA')
        existe = Ventas.objects.filter(
            carga=d['carga'],
            cliente=d['cliente'],
        ).exists()

        if existe:
            print(f"  ⏭  {tipo} {d['carga']} {d['cliente'].nombre[:20]:<20}  →  ya existe, omitida")
            omitidas += 1
            continue

        # Separar campos que no van directo al constructor
        monto_pagado   = d.pop('monto_pagado', None)
        estado_manual  = d.pop('estado_cobranza', None)
        termino        = d.pop('termino_credito', None)

        venta = Ventas(**d)

        if termino:
            venta.termino_credito = termino

        # El save() calculará fecha_vencimiento y pondrá estado inicial
        venta.save()

        # Para crédito: aplicar monto_pagado y estado post-save
        if d['modalidad_pago'] == 'Credito':
            if monto_pagado is not None:
                venta.monto_pagado = monto_pagado
            if estado_manual:
                venta.estado_cobranza = estado_manual
            # Recalcular fecha de vencimiento manualmente si hace falta
            if termino and not venta.fecha_vencimiento:
                venta.fecha_vencimiento = venta.fecha_deposito + __import__('datetime').timedelta(days=termino.dias_credito)
            Ventas.objects.filter(pk=venta.pk).update(
                monto_pagado=venta.monto_pagado.amount,
                estado_cobranza=venta.estado_cobranza,
            )

        monto_str = f"{float(venta.monto.amount):>12,.2f} {venta.moneda_venta}"
        print(f"  ✅ {tipo:<7} {d['carga']:<14} {d['cliente'].nombre[:22]:<22}  {monto_str}")
        creadas += 1

    print()
    print(f"Resultado: {creadas} creadas, {omitidas} omitidas.")


if __name__ == "__main__":
    print()
    print("=" * 68)
    print("  SEED — Ventas Q1 2025 (Ene / Feb / Mar)")
    print("=" * 68)
    print()
    insertar_ventas()
    print()
