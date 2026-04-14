"""
Pruebas unitarias — Reporte Global de Cobranza
===============================================
Cubre específicamente la lógica de «Saldo a favor del cliente»
introducida en generar_reporte_cobranza (sección 5):

  - Anticipos con estado Pendiente suman su monto completo.
  - Anticipo Aplicado donde anticipo.monto > venta.monto genera
    un excedente que se añade al saldo a favor.
  - Anticipo Aplicado donde anticipo.monto <= venta.monto no genera excedente.
  - Ambas fuentes se acumulan por cliente de forma independiente.
  - El saldo a favor de un cliente no contamina el de otro.
  - El filtrado por rango de fechas se aplica correctamente a ambas fuentes.
  - El saldo a favor se inyecta en la fila correspondiente de ventas_por_cliente.

Ejecución:
    python manage.py test ventas.tests --verbosity=2
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from djmoney.money import Money

from catalogo.models import Estado, Pais, Producto, Sucursal
from gastos.models import Banco, Cuenta
from ventas.models import (
    Agente,
    Anticipo,
    Cliente,
    ConfiguracionCuentasPorCobrar,
    Ventas,
)
from ventas.services.reporte_cobranza_service import generar_reporte_cobranza


# =============================================================================
# Fixture base
# =============================================================================

class ReporteCobranzaBaseTest(TestCase):
    """
    Fixture mínimo compartido.

    setUpTestData crea catálogos que se reusan en todos los tests de la clase.
    Los objetos variables (clientes, anticipos, ventas) se crean en cada test
    para que el rollback por test los descarte automáticamente.
    """

    @classmethod
    def setUpTestData(cls):
        cls.pais = Pais.objects.create(siglas='RCT', nombre='RC México', moneda='MXN')
        cls.estado = Estado.objects.create(id='RC_SIN', nombre='RC Sinaloa', pais=cls.pais)
        cls.sucursal = Sucursal.objects.create(nombre='RC Sucursal', id_estado=cls.estado)
        cls.producto = Producto.objects.create(
            nombre='Mango', variedad='RC Tommy', disponible=True
        )
        cls.agente = Agente.objects.create(nombre='Agente RC', pais=cls.pais)
        cls.banco = Banco.objects.create(nombre='Banco RC')
        cls.cuenta = Cuenta.objects.create(
            id_banco=cls.banco,
            id_sucursal=cls.sucursal,
            numero_cuenta='RC-9999',
        )
        # ConfiguracionCuentasPorCobrar necesaria para el tipo de cambio de fallback
        ConfiguracionCuentasPorCobrar.obtener_configuracion()

    # ------------------------------------------------------------------
    # Helpers de creación
    # ------------------------------------------------------------------

    def _cliente(self, nombre='Cliente RC'):
        return Cliente.objects.create(nombre=nombre, pais=self.pais)

    def _anticipo(self, cliente, monto, estado='Pendiente', fecha=None):
        """Crea un Anticipo usando objects.create() (no invoca full_clean)."""
        return Anticipo.objects.create(
            cliente=cliente,
            cuenta=self.cuenta,
            monto=Money(monto, 'MXN'),
            fecha=fecha or date(2026, 1, 15),
            estado_anticipo=estado,
        )

    def _venta_credito(self, cliente, monto, anticipo=None,
                       fecha=date(2026, 2, 1)):
        """
        Crea una Venta a crédito que queda en estado 'Pendiente'
        (ESTADOS_CON_DEUDA) sin invocar full_clean.
        """
        return Ventas.objects.create(
            cliente=cliente,
            sucursal_id=self.sucursal,
            producto=self.producto,
            agente_id=self.agente,
            cuenta=self.cuenta,
            tipo_venta='Nacional',
            tipo_registro='VENTA',
            modalidad_pago='Credito',
            monto=Money(monto, 'MXN'),
            monto_pagado=Money('0.00', 'MXN'),
            cantidad=Decimal('100.000'),
            fecha_salida_manifiesto=fecha,
            fecha_deposito=fecha,
            anticipo=anticipo,
        )

    def _aplicar_anticipo(self, anticipo):
        """
        Marca el anticipo como Aplicado usando update() para evitar
        la validación de clean() (que exige venta asociada via ORM).
        """
        Anticipo.objects.filter(pk=anticipo.pk).update(estado_anticipo='Aplicado')
        anticipo.refresh_from_db()


# =============================================================================
# Anticipos Pendientes
# =============================================================================

class AnticiposPendientesTest(ReporteCobranzaBaseTest):

    def test_sin_anticipos_total_es_cero(self):
        """Sin anticipos ni excedentes el total debe ser 0."""
        datos = generar_reporte_cobranza()
        self.assertEqual(datos['total_anticipos'], 0.0)

    def test_anticipo_pendiente_suma_monto_completo(self):
        """Un anticipo Pendiente aporta su monto completo al total."""
        cliente = self._cliente('Cliente Pendiente')
        self._anticipo(cliente, '5000.00')

        datos = generar_reporte_cobranza()

        self.assertAlmostEqual(datos['total_anticipos'], 5000.0)
        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente.id], 5000.0)

    def test_varios_anticipos_pendientes_mismo_cliente_se_acumulan(self):
        """Múltiples anticipos Pendientes del mismo cliente suman sus montos."""
        cliente = self._cliente('Cliente Multi-Anticipo')
        self._anticipo(cliente, '3000.00', fecha=date(2026, 1, 10))
        self._anticipo(cliente, '2000.00', fecha=date(2026, 1, 20))

        datos = generar_reporte_cobranza()

        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente.id], 5000.0)
        self.assertAlmostEqual(datos['total_anticipos'], 5000.0)

    def test_anticipo_cancelado_no_suma(self):
        """Un anticipo Cancelado no debe aparecer en el saldo a favor."""
        cliente = self._cliente('Cliente Cancelado')
        self._anticipo(cliente, '4000.00', estado='Cancelado')

        datos = generar_reporte_cobranza()

        self.assertEqual(datos['total_anticipos'], 0.0)
        self.assertNotIn(cliente.id, datos['anticipos_por_cliente'])


# =============================================================================
# Excedente de anticipo Aplicado
# =============================================================================

class ExcedenteAnticipoAplicadoTest(ReporteCobranzaBaseTest):

    def test_anticipo_aplicado_exacto_no_genera_excedente(self):
        """Anticipo igual al monto de la venta → excedente = 0."""
        cliente = self._cliente('Cliente Exacto')
        anticipo = self._anticipo(cliente, '8000.00')
        self._venta_credito(cliente, '8000.00', anticipo=anticipo)
        self._aplicar_anticipo(anticipo)

        datos = generar_reporte_cobranza()

        self.assertEqual(datos['total_anticipos'], 0.0)

    def test_anticipo_aplicado_mayor_genera_excedente(self):
        """anticipo.monto > venta.monto → la diferencia es saldo a favor."""
        cliente = self._cliente('Cliente Excedente')
        anticipo = self._anticipo(cliente, '10000.00')
        self._venta_credito(cliente, '8000.00', anticipo=anticipo)
        self._aplicar_anticipo(anticipo)

        datos = generar_reporte_cobranza()

        self.assertAlmostEqual(datos['total_anticipos'], 2000.0)
        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente.id], 2000.0)

    def test_anticipo_aplicado_menor_no_genera_excedente(self):
        """anticipo.monto < venta.monto → excedente negativo se descarta (= 0)."""
        cliente = self._cliente('Cliente Sin Excedente')
        anticipo = self._anticipo(cliente, '5000.00')
        self._venta_credito(cliente, '8000.00', anticipo=anticipo)
        self._aplicar_anticipo(anticipo)

        datos = generar_reporte_cobranza()

        self.assertEqual(datos['total_anticipos'], 0.0)

    def test_anticipo_pendiente_y_excedente_aplicado_se_acumulan(self):
        """
        Mismo cliente con anticipo Pendiente + excedente de anticipo Aplicado:
        total = anticipo_pendiente + excedente.
        """
        cliente = self._cliente('Cliente Combo')
        # Anticipo pendiente de $3 000
        self._anticipo(cliente, '3000.00')
        # Anticipo aplicado con excedente de $1 500 (10 000 - 8 500)
        anticipo_aplicado = self._anticipo(cliente, '10000.00')
        self._venta_credito(cliente, '8500.00', anticipo=anticipo_aplicado)
        self._aplicar_anticipo(anticipo_aplicado)

        datos = generar_reporte_cobranza()

        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente.id], 4500.0)
        self.assertAlmostEqual(datos['total_anticipos'], 4500.0)


# =============================================================================
# Independencia entre clientes
# =============================================================================

class SaldoFavorIndependenciaClientesTest(ReporteCobranzaBaseTest):

    def test_saldos_por_cliente_son_independientes(self):
        """El saldo a favor de un cliente no afecta al de otro."""
        cliente_a = self._cliente('Cliente Ind A')
        cliente_b = self._cliente('Cliente Ind B')
        self._anticipo(cliente_a, '7000.00')
        self._anticipo(cliente_b, '3000.00')

        datos = generar_reporte_cobranza()

        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente_a.id], 7000.0)
        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente_b.id], 3000.0)
        self.assertAlmostEqual(datos['total_anticipos'], 10000.0)

    def test_excedente_de_un_cliente_no_afecta_a_otro(self):
        """El excedente de anticipo de cliente A no aparece en cliente B."""
        cliente_a = self._cliente('Cliente Exc A')
        cliente_b = self._cliente('Cliente Exc B')

        anticipo_a = self._anticipo(cliente_a, '12000.00')
        self._venta_credito(cliente_a, '10000.00', anticipo=anticipo_a)
        self._aplicar_anticipo(anticipo_a)

        self._anticipo(cliente_b, '500.00')

        datos = generar_reporte_cobranza()

        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente_a.id], 2000.0)
        self.assertAlmostEqual(datos['anticipos_por_cliente'][cliente_b.id], 500.0)


# =============================================================================
# Filtrado por rango de fechas
# =============================================================================

class FiltroFechasTest(ReporteCobranzaBaseTest):

    def test_anticipo_dentro_del_rango_incluido(self):
        """Anticipo Pendiente con fecha dentro del rango → se incluye."""
        cliente = self._cliente('Cliente Rango In')
        self._anticipo(cliente, '5000.00', fecha=date(2026, 3, 15))

        datos = generar_reporte_cobranza(
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 3, 31),
        )

        self.assertAlmostEqual(datos['total_anticipos'], 5000.0)

    def test_anticipo_pendiente_fuera_del_rango_excluido(self):
        """Anticipo Pendiente anterior al rango → no se incluye."""
        cliente = self._cliente('Cliente Rango Out')
        self._anticipo(cliente, '5000.00', fecha=date(2026, 1, 5))

        datos = generar_reporte_cobranza(
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 3, 31),
        )

        self.assertEqual(datos['total_anticipos'], 0.0)

    def test_venta_con_excedente_fuera_del_rango_excluida(self):
        """
        Venta (con anticipo Aplicado excedente) fuera del rango de fechas
        → el excedente no debe aparecer en total_anticipos.
        """
        cliente = self._cliente('Cliente Exc Out')
        anticipo = self._anticipo(cliente, '10000.00', fecha=date(2026, 1, 5))
        self._venta_credito(cliente, '7000.00', anticipo=anticipo,
                            fecha=date(2026, 1, 10))
        self._aplicar_anticipo(anticipo)

        datos = generar_reporte_cobranza(
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 3, 31),
        )

        self.assertEqual(datos['total_anticipos'], 0.0)

    def test_venta_con_excedente_dentro_del_rango_incluida(self):
        """
        Venta (con anticipo Aplicado excedente) dentro del rango
        → el excedente aparece en total_anticipos.
        """
        cliente = self._cliente('Cliente Exc In')
        anticipo = self._anticipo(cliente, '10000.00', fecha=date(2026, 3, 5))
        self._venta_credito(cliente, '7000.00', anticipo=anticipo,
                            fecha=date(2026, 3, 10))
        self._aplicar_anticipo(anticipo)

        datos = generar_reporte_cobranza(
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 3, 31),
        )

        self.assertAlmostEqual(datos['total_anticipos'], 3000.0)


# =============================================================================
# Inyección del saldo a favor en filas de ventas_por_cliente
# =============================================================================

class InyeccionSaldoEnFilaTest(ReporteCobranzaBaseTest):

    def test_saldo_favor_inyectado_en_fila_ventas_pendientes(self):
        """
        Cliente con venta pendiente: el campo 'anticipo' de su fila
        debe contener el saldo a favor calculado.
        """
        cliente = self._cliente('Cliente Inyeccion')
        self._venta_credito(cliente, '6000.00')
        self._anticipo(cliente, '4000.00')

        datos = generar_reporte_cobranza()

        fila = next(
            (f for f in datos['ventas_por_cliente'] if f['cliente'].id == cliente.id),
            None,
        )
        self.assertIsNotNone(fila, "La fila del cliente debe estar en ventas_por_cliente")
        self.assertAlmostEqual(fila['anticipo'], 4000.0)

    def test_cliente_sin_ventas_pendientes_no_tiene_fila_pero_si_en_total(self):
        """
        Cliente solo con anticipo (sin ventas pendientes) no aparece en
        ventas_por_cliente, pero sí suma a total_anticipos.
        """
        cliente = self._cliente('Cliente Solo Anticipo')
        self._anticipo(cliente, '3000.00')

        datos = generar_reporte_cobranza()

        fila = next(
            (f for f in datos['ventas_por_cliente'] if f['cliente'].id == cliente.id),
            None,
        )
        self.assertIsNone(fila, "Sin ventas pendientes no debe haber fila")
        self.assertAlmostEqual(datos['total_anticipos'], 3000.0)

    def test_excedente_aplicado_inyectado_en_fila(self):
        """
        Excedente de anticipo aplicado se inyecta en la fila del cliente
        cuando también tiene ventas pendientes.
        """
        cliente = self._cliente('Cliente Exc Inyeccion')
        # Venta pendiente independiente (sin anticipo)
        self._venta_credito(cliente, '6000.00')
        # Venta con anticipo aplicado que genera excedente
        anticipo = self._anticipo(cliente, '10000.00')
        self._venta_credito(cliente, '8000.00', anticipo=anticipo)
        self._aplicar_anticipo(anticipo)

        datos = generar_reporte_cobranza()

        fila = next(
            (f for f in datos['ventas_por_cliente'] if f['cliente'].id == cliente.id),
            None,
        )
        self.assertIsNotNone(fila)
        self.assertAlmostEqual(fila['anticipo'], 2000.0)  # excedente = 10000 - 8000
