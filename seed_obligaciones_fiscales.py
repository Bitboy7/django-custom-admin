"""
Script de datos de prueba — Obligaciones Fiscales (SAT México)
===============================================================
Inserta registros de ObligacionFiscal con montos calculados conforme a:

  • Art. 74 LISR    — ISR para personas morales AGAPES (tasa 30%)
  • Art. 94-97 LISR — ISR retenciones por salarios (tarifa progresiva)
  • Art. 111-113 LISR — RESICO personas morales (1% - 2.5% ingresos cobrados)
  • Art. 1-A Frac. II LIVA — Retención IVA servicios profesionales (10.6667%)

Empresa:  Agrícola de la Costa (persona moral, régimen AGAPES)
Ingresos anuales estimados: ~$12,000,000 MXN
Nómina mensual estimada:    ~$180,000 MXN (8 empleados)
Servicios profesionales:    ~$250,000 MXN por semestre

Ejecutar:
    py manage.py shell < seed_obligaciones_fiscales.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from decimal import Decimal
from ventas.models import ObligacionFiscal


# ---------------------------------------------------------------------------
# Datos de prueba — 5 períodos semestrales (2023-2025)
# ---------------------------------------------------------------------------
#
# Metodología de cálculo por semestre:
#
# ISR INGRESOS PROPIOS
#   Ingresos acumulables del semestre × margen neto estimado × tasa ISR 30%
#   AGAPES tienen exención Art.74: hasta 20 SMLV anuales exentos.
#   Aquí se muestra solo la parte gravada.
#
# ISR RESICO (Régimen Simplificado de Confianza)
#   Aplica sobre servicios profesionales contratados a personas físicas RESICO.
#   Tasa efectiva ~1.5% sobre ingresos de profesionistas.
#
# ISR RETENCIONES SALARIOS
#   8 empleados. Salarios brutos mensuales promedio: $22,500 MXN
#   ISR mensual prom. por empleado: ~$2,890 (tarifa Art. 96 LISR 2025)
#   Semestre = 8 empleados × $2,890 × 6 meses
#
# IVA RETENCIONES PROFESIONALES
#   Honorarios pagados en el semestre × 10.6667%
#   (Art. 1-A Frac. II inciso a) LIVA: retención de 2/3 del IVA al 16%)
# ---------------------------------------------------------------------------

PERIODOS = [
    {
        "periodo": "Semestre Enero–Junio 2023",
        # Ingresos semestre: ~$4,800,000, margen neto 12%, ISR 30%
        "isr_ingresos_propios": Decimal("172800.00"),
        # Honorarios pagados: $210,000 × 1.5% RESICO
        "isr_resico": Decimal("3150.00"),
        # 8 emp × $2,640/mes × 6 meses (nivel salarial 2023)
        "isr_retenciones_salarios": Decimal("126720.00"),
        # Honorarios brutos: $210,000 × 10.6667%
        "iva_retenciones_profesionales": Decimal("22400.00"),
    },
    {
        "periodo": "Semestre Julio–Diciembre 2023",
        # Ingresos semestre: ~$5,400,000, margen 12%, ISR 30%
        "isr_ingresos_propios": Decimal("194400.00"),
        # Honorarios: $230,000 × 1.5%
        "isr_resico": Decimal("3450.00"),
        # 8 emp × $2,760/mes × 6 meses
        "isr_retenciones_salarios": Decimal("132480.00"),
        # $230,000 × 10.6667%
        "iva_retenciones_profesionales": Decimal("24533.41"),
    },
    {
        "periodo": "Semestre Enero–Junio 2024",
        # Ingresos semestre: ~$5,900,000, margen 13%, ISR 30%
        "isr_ingresos_propios": Decimal("230100.00"),
        # Honorarios: $240,000 × 1.5%
        "isr_resico": Decimal("3600.00"),
        # 8 emp × $2,890/mes × 6 meses  (ajuste salarial 2024)
        "isr_retenciones_salarios": Decimal("138720.00"),
        # $240,000 × 10.6667%
        "iva_retenciones_profesionales": Decimal("25600.08"),
    },
    {
        "periodo": "Semestre Julio–Diciembre 2024",
        # Ingresos semestre: ~$6,200,000, margen 13%, ISR 30%
        "isr_ingresos_propios": Decimal("241800.00"),
        # Honorarios: $255,000 × 1.5%
        "isr_resico": Decimal("3825.00"),
        # 8 emp × $3,010/mes × 6 meses
        "isr_retenciones_salarios": Decimal("144480.00"),
        # $255,000 × 10.6667%
        "iva_retenciones_profesionales": Decimal("27200.09"),
    },
    {
        "periodo": "Semestre Enero–Junio 2025",
        # Ingresos semestre: ~$6,800,000, margen 14%, ISR 30%
        "isr_ingresos_propios": Decimal("285600.00"),
        # Honorarios: $265,000 × 1.5%
        "isr_resico": Decimal("3975.00"),
        # 8 emp × $3,150/mes × 6 meses  (UMA 2025: $108.57/día)
        "isr_retenciones_salarios": Decimal("151200.00"),
        # $265,000 × 10.6667%
        "iva_retenciones_profesionales": Decimal("28266.76"),
    },
]


def insertar_obligaciones():
    creados = 0
    omitidos = 0

    for datos in PERIODOS:
        obj, created = ObligacionFiscal.objects.get_or_create(
            periodo=datos["periodo"],
            defaults={
                "isr_ingresos_propios":          datos["isr_ingresos_propios"],
                "isr_resico":                    datos["isr_resico"],
                "isr_retenciones_salarios":      datos["isr_retenciones_salarios"],
                "iva_retenciones_profesionales": datos["iva_retenciones_profesionales"],
            }
        )
        if created:
            total = (
                datos["isr_ingresos_propios"]
                + datos["isr_resico"]
                + datos["isr_retenciones_salarios"]
                + datos["iva_retenciones_profesionales"]
            )
            print(
                f"  ✅ {obj.periodo}"
                f"  →  Total: ${total:,.2f} MXN"
            )
            creados += 1
        else:
            print(f"  ⏭  {obj.periodo}  →  ya existe, omitido")
            omitidos += 1

    print()
    print(f"Resultado: {creados} creados, {omitidos} omitidos.")


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  SEED — Obligaciones Fiscales (SAT México)")
    print("=" * 60)
    print()
    insertar_obligaciones()
    print()
