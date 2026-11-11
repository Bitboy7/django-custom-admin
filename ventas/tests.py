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
from types import SimpleNamespace

from django.contrib import admin
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase
from django.urls import path
from django.views.i18n import set_language
from djmoney.money import Money

from catalogo.models import Estado, Pais, Producto, Sucursal
from gastos.models import Banco, Cuenta
from ventas.models import (
    Agente,
    Anticipo,
    Cliente,
    ConfiguracionCuentasPorCobrar,
    DocumentoCFDI,
    PagoVenta,
    TerminoCredito,
    Ventas,
)
from ventas.services.reporte_cobranza_service import generar_reporte_cobranza
from ventas.cfdi_parser import parse_cfdi
from ventas.services.cfdi_import_service import (
    crear_cliente_desde_cfdi,
    crear_producto_desde_cfdi,
    importar_cfdi,
    match_cliente,
    match_producto,
    sugerir_producto_desde_cfdi,
)
from ventas.tests_cfdi_parser import (
    XML_40_INGRESO,
    XML_INGRESO_MIXTO,
    XML_INGRESO_SERVICIO,
    XML_MULTI_CONCEPTOS,
    XML_NOTA_CARGO,
    XML_RECIBO_PAGO_20,
)
from ventas.admin import (
    CFDI_UPLOAD_LIMITS,
    ClienteAdmin,
    VentasAdmin,
    _pdf_response,
    _validar_archivo_cfdi,
)
from ventas.forms import CFDIConfirmForm

def _empty_test_view(request, *args, **kwargs):
    return HttpResponse()


urlpatterns = [
    path('admin/mi-perfil/', _empty_test_view, name='profile_settings'),
    path('manual/', _empty_test_view, name='user_manual'),
    path('admin/', admin.site.urls),
    path('i18n/setlang/', set_language, name='set_language'),
]


class VentasAdminDisplayTest(SimpleTestCase):

    def setUp(self):
        self.model_admin = VentasAdmin(Ventas, admin.site)

    def test_cliente_info_usa_icono_y_bandera_sin_emojis(self):
        bandera = SimpleNamespace(
            name='paises/banderas/mexico.png',
            url='/media/paises/banderas/mexico.png',
        )
        pais = SimpleNamespace(nombre='México', bandera=bandera)
        cliente = SimpleNamespace(
            nombre='Productora Agrícola',
            calificacion_credito='A',
            pais=pais,
            get_calificacion_credito_display=lambda: 'Bueno',
        )

        html = str(self.model_admin.get_cliente_info(SimpleNamespace(cliente=cliente)))

        self.assertIn('fas fa-chart-line', html)
        self.assertIn('sales-country__flag', html)
        self.assertIn('/media/paises/banderas/mexico.png', html)
        self.assertIn('width="18" height="12"', html)
        self.assertNotIn('📊', html)
        self.assertNotIn('🌍', html)

    def test_cliente_info_muestra_respaldo_si_no_hay_bandera(self):
        pais = SimpleNamespace(nombre='México', bandera=None)
        cliente = SimpleNamespace(
            nombre='Productora Agrícola',
            calificacion_credito='B',
            pais=pais,
            get_calificacion_credito_display=lambda: 'Bueno',
        )

        html = str(self.model_admin.get_cliente_info(SimpleNamespace(cliente=cliente)))

        self.assertIn('fas fa-map-marker-alt', html)
        self.assertIn('México', html)

    def test_saldo_pagado_usa_icono_font_awesome(self):
        venta = SimpleNamespace(modalidad_pago='Contado')

        html = str(self.model_admin.get_saldo_pendiente(venta))

        self.assertIn('fas fa-check', html)
        self.assertNotIn('✓', html)


class CFDIUploadLimitsTest(SimpleTestCase):

    def test_zip_de_hasta_5_mb_es_valido(self):
        limite_zip = CFDI_UPLOAD_LIMITS['zip'][0]
        archivo = SimpleNamespace(name='cfdi-lote.zip', size=limite_zip)

        self.assertIsNone(_validar_archivo_cfdi(archivo))

    def test_zip_mayor_a_5_mb_es_rechazado(self):
        limite_zip = CFDI_UPLOAD_LIMITS['zip'][0]
        archivo = SimpleNamespace(name='cfdi-lote.zip', size=limite_zip + 1)

        self.assertEqual(
            _validar_archivo_cfdi(archivo),
            '"cfdi-lote.zip" supera 5 MB.',
        )

    def test_xml_conserva_limite_de_1_mb(self):
        limite_xml = CFDI_UPLOAD_LIMITS['xml'][0]
        archivo = SimpleNamespace(name='factura.xml', size=limite_xml + 1)

        self.assertEqual(
            _validar_archivo_cfdi(archivo),
            '"factura.xml" supera 1 MB.',
        )


class PDFResponseTest(SimpleTestCase):

    def test_pdf_is_served_from_storage_without_redirecting_to_its_url(self):
        from io import BytesIO

        class StoredPDF:
            name = 'cfdi/pdf/2026/08/factura.pdf'

            @property
            def url(self):
                raise AssertionError('La respuesta no debe solicitar una URL firmada')

            def open(self, mode):
                self.open_mode = mode
                return BytesIO(b'%PDF-1.4\ncontenido')

        stored_pdf = StoredPDF()
        response = _pdf_response(stored_pdf)

        self.assertEqual(stored_pdf.open_mode, 'rb')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('inline', response['Content-Disposition'])
        self.assertEqual(response['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(
            b''.join(response.streaming_content),
            b'%PDF-1.4\ncontenido',
        )


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
                       fecha=date(2026, 2, 1), moneda='MXN'):
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
            monto=Money(monto, moneda),
            monto_pagado=Money('0.00', moneda),
            cantidad=Decimal('100.000'),
            fecha_salida_manifiesto=fecha,
            fecha_deposito=fecha,
            anticipo=anticipo,
        )

    def _aplicar_anticipo(self, anticipo):
        """
        Marca el anticipo como Aplicado ajustando monto_aplicado.
        """
        venta = Ventas.objects.filter(anticipo=anticipo).first()
        monto_aplicado = venta.monto.amount if venta else anticipo.monto.amount
        Anticipo.objects.filter(pk=anticipo.pk).update(
            estado_anticipo='Aplicado',
            monto_aplicado=monto_aplicado,
            monto_aplicado_currency=anticipo.monto.currency,
        )
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


# =============================================================================
# Saldo por cobrar con notas (DocumentoCFDI)
# =============================================================================

class SaldoPorCobrarNotasTest(ReporteCobranzaBaseTest):

    def test_nota_credito_que_liquida_saldo_actualiza_venta_a_pagada(self):
        cliente = self._cliente('Cliente Nota liquida saldo')
        venta = self._venta_credito(cliente, '1000.00')
        Ventas.objects.filter(pk=venta.pk).update(
            estado_cobranza=Ventas.EstadoCobranza.VENCIDO,
        )
        venta.refresh_from_db()

        nota = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.EGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.NOTA_CREDITO,
            monto=Money('1000.00', 'MXN'),
            venta=venta,
        )

        venta.refresh_from_db()
        self.assertEqual(venta.estado_cobranza, Ventas.EstadoCobranza.PAGADO)

        nota.delete()
        venta.refresh_from_db()
        self.assertEqual(venta.estado_cobranza, Ventas.EstadoCobranza.PENDIENTE)

    def test_rep_sin_pagoventa_no_actualiza_estado_operativo(self):
        cliente = self._cliente('Cliente REP sin vínculo operativo')
        venta = self._venta_credito(cliente, '1000.00')
        Ventas.objects.filter(pk=venta.pk).update(
            estado_cobranza=Ventas.EstadoCobranza.VENCIDO,
        )
        venta.refresh_from_db()

        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.PAGO,
            subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
            monto=Money('1000.00', 'MXN'),
            venta=venta,
        )

        venta.refresh_from_db()
        self.assertEqual(venta.estado_cobranza, Ventas.EstadoCobranza.VENCIDO)

    def test_editar_nota_recalcula_venta_anterior_y_nueva(self):
        cliente = self._cliente('Cliente nota movida entre ventas')
        venta_anterior = self._venta_credito(cliente, '1000.00')
        venta_nueva = self._venta_credito(cliente, '1000.00')
        nota = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.EGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.NOTA_CREDITO,
            monto=Money('1000.00', 'MXN'),
            venta=venta_anterior,
        )
        venta_anterior.refresh_from_db()
        self.assertEqual(venta_anterior.estado_cobranza, Ventas.EstadoCobranza.PAGADO)

        nota.venta = venta_nueva
        nota.save(update_fields=['venta'])

        venta_anterior.refresh_from_db()
        venta_nueva.refresh_from_db()
        self.assertEqual(
            venta_anterior.estado_cobranza, Ventas.EstadoCobranza.PENDIENTE,
        )
        self.assertEqual(
            venta_nueva.estado_cobranza, Ventas.EstadoCobranza.PAGADO,
        )

    def test_eliminar_venta_con_nota_no_recalcula_venta_en_cascada(self):
        from unittest.mock import patch

        cliente = self._cliente('Cliente Venta eliminada con nota')
        venta = self._venta_credito(cliente, '1000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.EGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.NOTA_CREDITO,
            monto=Money('100.00', 'MXN'),
            venta=venta,
        )

        with patch.object(Ventas, 'actualizar_estado_cobranza') as actualizar:
            venta.delete()

        actualizar.assert_not_called()

    def test_nota_cargo_suma_y_nota_credito_resta(self):
        """Nota de cargo suma al saldo; nota de crédito resta."""
        cliente = self._cliente('Cliente Notas')
        venta = self._venta_credito(cliente, '10000.00')

        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.NOTA_CARGO,
            monto=Money('500.00', 'MXN'),
            venta=venta,
        )
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.EGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.NOTA_CREDITO,
            monto=Money('200.00', 'MXN'),
            venta=venta,
        )

        self.assertAlmostEqual(venta.saldo_por_cobrar(), 10300.00)

    def test_nota_credito_cancelada_no_afecta_saldo(self):
        """Una nota de crédito cancelada no debe restar del saldo."""
        cliente = self._cliente('Cliente NC Cancelada')
        venta = self._venta_credito(cliente, '10000.00')

        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.EGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.NOTA_CREDITO,
            monto=Money('200.00', 'MXN'),
            venta=venta,
            estado=DocumentoCFDI.EstadoDocumento.CANCELADO,
        )

        self.assertAlmostEqual(venta.saldo_por_cobrar(), 10000.00)


class ServiciosPorCobrarTest(ReporteCobranzaBaseTest):

    def test_ingreso_servicio_aparece_en_maquila_y_servicios(self):
        cliente = self._cliente('Cliente Servicio Pendiente')
        Ventas.objects.create(
            cliente=cliente,
            sucursal_id=self.sucursal,
            producto=None,
            cuenta=self.cuenta,
            tipo_venta=Ventas.TipoVenta.NACIONAL,
            tipo_registro=Ventas.TipoRegistro.SERVICIO,
            modalidad_pago=Ventas.ModalidadPago.CREDITO,
            estado_cobranza=Ventas.EstadoCobranza.PENDIENTE,
            monto=Money('3000.00', 'MXN'),
            monto_pagado=Money('0.00', 'MXN'),
            cantidad=Decimal('1.000'),
            descripcion='Servicio de fumigación',
            fecha_salida_manifiesto=date(2026, 2, 1),
            fecha_deposito=date(2026, 2, 1),
        )

        datos = generar_reporte_cobranza()

        fila = next(
            item for item in datos['maquila_por_cliente']
            if item['cliente'].id == cliente.id
        )
        self.assertAlmostEqual(fila['total'], 3000.0)


# =============================================================================
# Importación de CFDI (servicio)
# =============================================================================

class CFDIImportServiceTest(ReporteCobranzaBaseTest):

    def test_evento_pago_usa_usuario_actual(self):
        from django.contrib.auth.models import User

        from auditoria.models import LogActividad
        from auditoria.request_context import reset_audit_actor, set_audit_actor

        cliente = self._cliente('Cliente Auditoría PagoVenta')
        venta = self._venta_credito(cliente, '1000.00')
        usuario = User.objects.create_user(username='auditor-pago')
        token = set_audit_actor(usuario)
        try:
            pago = PagoVenta.objects.create(
                venta=venta,
                fecha_pago=date(2026, 7, 16),
                monto_pago=Money('100.00', 'MXN'),
                cuenta_destino=self.cuenta,
                metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            )
        finally:
            reset_audit_actor(token)

        log = LogActividad.objects.get(
            modelo_afectado='PagoVenta', objeto_id=str(pago.pk),
        )
        self.assertEqual(log.usuario_id, usuario.pk)
        self.assertEqual(log.nombre_usuario, usuario.username)

    def test_tarea_sin_usuario_usa_sistema(self):
        from auditoria.models import LogActividad

        cliente = self._cliente('Cliente Auditoría Sistema')
        venta = self._venta_credito(cliente, '1000.00')

        pago = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 16),
            monto_pago=Money('100.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
        )

        log = LogActividad.objects.get(
            modelo_afectado='PagoVenta', objeto_id=str(pago.pk),
        )
        self.assertIsNone(log.usuario_id)
        self.assertEqual(log.nombre_usuario, 'Sistema')

    def test_importar_pago_20_lo_aplica_a_la_factura_relacionada(self):
        cliente = self._cliente('EMSEGA MARKET')
        cliente.rfc = 'EMA220607QL9'
        cliente.save(update_fields=['rfc'])
        venta = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())

        pago, documento, subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertEqual(subtipo, 'recibo_pago')
        self.assertEqual(pago.venta_id, venta.id)
        self.assertEqual(pago.fecha_pago, date(2026, 7, 16))
        self.assertEqual(pago.monto_pago, Money('162480.00', 'MXN'))
        self.assertEqual(documento.venta_id, venta.id)
        self.assertEqual(documento.pago_venta_id, pago.id)
        self.assertEqual(documento.monto, Money('162480.00', 'MXN'))
        venta.refresh_from_db()
        self.assertEqual(venta.estado_cobranza, Ventas.EstadoCobranza.PAGADO)

    def test_importar_rep_reutiliza_pagoventa_por_uuid_exacto(self):
        cliente = self._cliente('Cliente REP enlace exacto')
        venta = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())
        pago_existente = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 16),
            monto_pago=Money('162480.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            folio_rep=parsed['folio_num'],
            uuid_rep=parsed['uuid'],
        )

        pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertEqual(pago.pk, pago_existente.pk)
        self.assertEqual(documento.pago_venta_id, pago_existente.pk)
        self.assertEqual(PagoVenta.objects.filter(venta=venta).count(), 1)

    def test_importar_rep_no_asocia_por_monto_si_uuid_no_coincide(self):
        cliente = self._cliente('Cliente REP sin UUID coincidente')
        venta = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )
        PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 16),
            monto_pago=Money('162480.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            folio_rep='REP-ANTERIOR',
            uuid_rep='AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA',
        )
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())

        pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertIsNone(pago)
        self.assertIsNone(documento.pago_venta_id)
        self.assertEqual(
            documento.detalle_complemento['vinculo_pago']['estado'],
            'no_encontrado',
        )

    def test_importar_rep_no_asocia_factura_de_otro_cliente(self):
        cliente_rep = self._cliente('Cliente receptor del REP')
        cliente_factura = self._cliente('Cliente propietario de factura')
        venta = self._venta_credito(cliente_factura, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente_factura,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )

        pago, documento, _subtipo = importar_cfdi(
            parse_cfdi(XML_RECIBO_PAGO_20.encode()),
            cliente=cliente_rep,
            cuenta=self.cuenta,
        )

        self.assertIsNone(pago)
        self.assertIsNone(documento.venta_id)
        self.assertIsNone(documento.pago_venta_id)
        self.assertEqual(
            documento.detalle_complemento['vinculo_pago']['estado'],
            'cliente_documento_discordante',
        )
        self.assertEqual(PagoVenta.objects.filter(venta=venta).count(), 0)

    def test_importar_rep_ambiguo_no_elige_un_pago_por_uuid_repetido(self):
        cliente = self._cliente('Cliente REP UUID ambiguo')
        venta = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )
        for monto in ('81240.00', '81240.00'):
            PagoVenta.objects.create(
                venta=venta,
                fecha_pago=date(2026, 7, 16),
                monto_pago=Money(monto, 'MXN'),
                cuenta_destino=self.cuenta,
                metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
                folio_rep='2325',
                uuid_rep='10BEF933-60EF-45B5-AB78-40C7D9A6246D',
            )
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())

        pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertIsNone(pago)
        self.assertIsNone(documento.pago_venta_id)
        self.assertEqual(
            documento.detalle_complemento['vinculo_pago']['estado'],
            'ambiguo',
        )

    def test_backfill_vincula_solo_uuid_exactos(self):
        from django.core.management import call_command

        cliente = self._cliente('Cliente Backfill UUID')
        venta = self._venta_credito(cliente, '1000.00')
        pago = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 16),
            monto_pago=Money('1000.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            folio_rep='REP-EXACTO',
            uuid_rep='AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA',
        )
        documento = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.PAGO,
            subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
            folio='REP-EXACTO',
            uuid='AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA',
            monto=Money('1000.00', 'MXN'),
            venta=venta,
        )

        call_command('backfill_cfdi_detalle_reps', cliente_id=cliente.pk)

        documento.refresh_from_db()
        self.assertEqual(documento.pago_venta_id, pago.pk)

    def test_backfill_no_infiere_vinculo_por_monto_o_fecha_en_dry_run(self):
        from django.core.management import call_command

        cliente = self._cliente('Cliente Backfill Ambiguo')
        venta = self._venta_credito(cliente, '1000.00')
        PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 16),
            monto_pago=Money('1000.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            folio_rep='REP-OTRO',
            uuid_rep='BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB',
        )
        documento = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.PAGO,
            subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
            folio='REP-SIN-PAGO',
            uuid='CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC',
            monto=Money('1000.00', 'MXN'),
            venta=venta,
        )

        call_command('backfill_cfdi_detalle_reps', cliente_id=cliente.pk, dry_run=True)

        documento.refresh_from_db()
        self.assertIsNone(documento.pago_venta_id)

    def test_backfill_dry_run_no_persiste_vinculo_uuid_exacto(self):
        from django.core.management import call_command

        cliente = self._cliente('Cliente Backfill Dry Run Exacto')
        venta = self._venta_credito(cliente, '1000.00')
        PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 16),
            monto_pago=Money('1000.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            folio_rep='REP-DRY-RUN',
            uuid_rep='DDDDDDDD-DDDD-DDDD-DDDD-DDDDDDDDDDDD',
        )
        documento = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.PAGO,
            subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
            folio='REP-DRY-RUN',
            uuid='DDDDDDDD-DDDD-DDDD-DDDD-DDDDDDDDDDDD',
            monto=Money('1000.00', 'MXN'),
            venta=venta,
        )

        call_command('backfill_cfdi_detalle_reps', cliente_id=cliente.pk, dry_run=True)

        documento.refresh_from_db()
        self.assertIsNone(documento.pago_venta_id)

    def test_backfill_no_asocia_venta_de_otro_cliente(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.management import call_command
        from django.test.utils import override_settings
        from tempfile import TemporaryDirectory

        cliente_rep = self._cliente('Cliente Backfill receptor')
        cliente_factura = self._cliente('Cliente Backfill factura')
        venta = self._venta_credito(cliente_factura, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente_factura,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())
        PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 16),
            monto_pago=Money('162480.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            uuid_rep=parsed['uuid'],
        )
        with TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root,
        ):
            documento = DocumentoCFDI.objects.create(
                cliente=cliente_rep,
                tipo=DocumentoCFDI.TipoDocumento.PAGO,
                subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
                uuid=parsed['uuid'],
                monto=Money('162480.00', 'MXN'),
                archivo_xml=SimpleUploadedFile(
                    'rep-otro-cliente.xml', XML_RECIBO_PAGO_20.encode(),
                    content_type='application/xml',
                ),
            )

            call_command(
                'backfill_cfdi_detalle_reps', cliente_id=cliente_rep.pk,
            )

        documento.refresh_from_db()
        self.assertIsNone(documento.venta_id)
        self.assertIsNone(documento.pago_venta_id)
        self.assertEqual(
            documento.detalle_complemento['vinculo_pago']['estado'],
            'cliente_documento_discordante',
        )

    def test_backfill_no_persiste_detalle_si_uuid_xml_no_coincide_o_falta(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.management import call_command
        from django.test.utils import override_settings
        from tempfile import TemporaryDirectory

        cliente = self._cliente('Cliente Backfill XML discordante')
        xml_sin_uuid = XML_RECIBO_PAGO_20.replace(
            'UUID="10BEF933-60EF-45B5-AB78-40C7D9A6246D"\n      FechaTimbrado',
            'FechaTimbrado',
        ).encode()
        with TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root,
        ):
            documento_discordante = DocumentoCFDI.objects.create(
                cliente=cliente,
                tipo=DocumentoCFDI.TipoDocumento.PAGO,
                subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
                uuid='AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA',
                monto=Money('1000.00', 'MXN'),
                archivo_xml=SimpleUploadedFile(
                    'rep-uuid-distinto.xml', XML_RECIBO_PAGO_20.encode(),
                    content_type='application/xml',
                ),
            )
            documento_sin_uuid = DocumentoCFDI.objects.create(
                cliente=cliente,
                tipo=DocumentoCFDI.TipoDocumento.PAGO,
                subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
                uuid='BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB',
                monto=Money('1000.00', 'MXN'),
                archivo_xml=SimpleUploadedFile(
                    'rep-sin-uuid.xml', xml_sin_uuid,
                    content_type='application/xml',
                ),
            )

            call_command('backfill_cfdi_detalle_reps', cliente_id=cliente.pk)

        documento_discordante.refresh_from_db()
        documento_sin_uuid.refresh_from_db()
        self.assertEqual(documento_discordante.detalle_complemento, {})
        self.assertEqual(documento_sin_uuid.detalle_complemento, {})

    def test_backfill_reporta_uuid_docto_sin_coincidencia(self):
        from io import StringIO
        from tempfile import TemporaryDirectory

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test.utils import override_settings
        from django.core.management import call_command

        cliente = self._cliente('Cliente Backfill UUID Docto faltante')
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())
        salida = StringIO()
        with TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root,
        ):
            DocumentoCFDI.objects.create(
                cliente=cliente,
                tipo=DocumentoCFDI.TipoDocumento.PAGO,
                subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
                uuid=parsed['uuid'],
                monto=Money('1000.00', 'MXN'),
                archivo_xml=SimpleUploadedFile(
                    'rep.xml', XML_RECIBO_PAGO_20.encode(),
                    content_type='application/xml',
                ),
            )

            call_command('backfill_cfdi_detalle_reps', dry_run=True, stdout=salida)

        self.assertIn('1 UUID sin coincidencia', salida.getvalue())

    def test_importar_rep_guarda_todos_los_detalles_de_pago(self):
        cliente = self._cliente('Cliente REP multipago')
        venta = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )
        segundo_pago = '''
      <pago20:Pago FechaPago="2026-08-16T09:30:00" FormaDePagoP="03"
          MonedaP="USD" TipoCambioP="18.0000" Monto="100.00">
        <pago20:DoctoRelacionado
          IdDocumento="28C06FD3-D87D-45C5-8C4D-D4927FCD3A64"
          Serie="B" Folio="2325" MonedaDR="MXN" EquivalenciaDR="18.000000"
          NumParcialidad="2" ImpSaldoAnt="162480.00" ImpPagado="1800.00"
          ImpSaldoInsoluto="160680.00" />
      </pago20:Pago>
        '''
        xml = XML_RECIBO_PAGO_20.replace(
            '</pago20:Pagos>', segundo_pago + '</pago20:Pagos>'
        )
        parsed = parse_cfdi(xml.encode())

        _pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        detalle = documento.detalle_complemento
        self.assertEqual(detalle['relacionados'], [])
        self.assertEqual(len(detalle['pagos']), 2)
        self.assertEqual(detalle['pagos'][1]['fecha_pago'], '2026-08-16')
        self.assertEqual(detalle['pagos'][1]['monto'], '100.00')
        self.assertEqual(detalle['pagos'][1]['moneda'], 'USD')
        docto = detalle['pagos'][1]['doctos'][0]
        self.assertEqual(
            docto['uuid'], '28C06FD3-D87D-45C5-8C4D-D4927FCD3A64'
        )
        self.assertEqual(docto['imp_pagado'], '1800.00')
        self.assertEqual(docto['saldo_insoluto'], '160680.00')
        self.assertEqual(docto['equivalencia'], '18.000000')

    def test_importar_rep_multipago_no_crea_pago_operativo_sintetico(self):
        cliente = self._cliente('Cliente REP multipago sin desglose operativo')
        venta = self._venta_credito(cliente, '200000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('200000.00', 'MXN'),
            venta=venta,
        )
        segundo_pago = '''
      <pago20:Pago FechaPago="2026-08-16T09:30:00" FormaDePagoP="03"
          MonedaP="USD" TipoCambioP="18.0000" Monto="100.00">
        <pago20:DoctoRelacionado
          IdDocumento="28C06FD3-D87D-45C5-8C4D-D4927FCD3A64"
          Serie="B" Folio="2325" MonedaDR="MXN" EquivalenciaDR="18.000000"
          NumParcialidad="2" ImpSaldoAnt="200000.00" ImpPagado="1800.00"
          ImpSaldoInsoluto="35720.00" />
      </pago20:Pago>
        '''
        xml = XML_RECIBO_PAGO_20.replace(
            'ImpSaldoAnt="162480.00" ImpPagado="162480.00" ImpSaldoInsoluto="0"',
            'ImpSaldoAnt="200000.00" ImpPagado="162480.00" ImpSaldoInsoluto="37520.00"',
        ).replace('</pago20:Pagos>', segundo_pago + '</pago20:Pagos>')
        parsed = parse_cfdi(xml.encode())

        pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertIsNone(pago)
        self.assertEqual(PagoVenta.objects.filter(venta=venta).count(), 0)
        self.assertEqual(len(documento.detalle_complemento['pagos']), 2)
        self.assertEqual(
            documento.detalle_complemento['vinculo_pago']['estado'],
            'multipago_revision',
        )

    def test_importar_rep_resuelve_la_factura_docto_antes_del_cfdi_sustituido(self):
        cliente = self._cliente('Cliente REP sustitución')
        venta_anterior = self._venta_credito(cliente, '1000.00')
        documento_sustituido = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.PAGO,
            subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
            uuid='BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB',
            monto=Money('1000.00', 'MXN'),
            venta=venta_anterior,
        )
        venta_facturada = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta_facturada,
        )
        xml = XML_RECIBO_PAGO_20.replace(
            '<cfdi:Receptor',
            '<cfdi:CfdiRelacionados TipoRelacion="04">'
            '<cfdi:CfdiRelacionado UUID="BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB"/>'
            '</cfdi:CfdiRelacionados><cfdi:Receptor',
        )
        parsed = parse_cfdi(xml.encode())

        _pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertEqual(documento.venta_id, venta_facturada.pk)
        self.assertNotEqual(documento.venta_id, venta_anterior.pk)
        self.assertEqual(documento.cfdi_relacionado_id, documento_sustituido.pk)

    def test_importar_rep_con_doctos_de_varias_ventas_requiere_revision(self):
        cliente = self._cliente('Cliente REP varias ventas')
        venta_uno = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta_uno,
        )
        venta_dos = self._venta_credito(cliente, '500.00')
        segundo_docto = '''
        <pago20:DoctoRelacionado
          IdDocumento="CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC"
          Serie="B" Folio="OTRA" MonedaDR="MXN" EquivalenciaDR="1"
          NumParcialidad="1" ImpSaldoAnt="500.00" ImpPagado="500.00"
          ImpSaldoInsoluto="0.00" />
        '''
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC',
            monto=Money('500.00', 'MXN'),
            venta=venta_dos,
        )
        xml = XML_RECIBO_PAGO_20.replace(
            '</pago20:Pago>', segundo_docto + '</pago20:Pago>'
        )
        parsed = parse_cfdi(xml.encode())

        pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertIsNone(pago)
        self.assertIsNone(documento.venta_id)
        self.assertEqual(
            documento.detalle_complemento['vinculo_pago']['estado'],
            'multiples_ventas_revision',
        )
        self.assertEqual(PagoVenta.objects.filter(venta__cliente=cliente).count(), 0)

    def test_pago_20_sin_factura_relacionada_se_conserva_pendiente(self):
        cliente = self._cliente('EMSEGA MARKET sin factura')
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())

        pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertIsNone(pago)
        self.assertIsNone(documento.venta_id)
        self.assertIsNone(documento.pago_venta_id)
        self.assertEqual(
            documento.detalle_complemento['vinculo_pago']['estado'],
            'uuid_documento_no_encontrado',
        )

    def test_reimportar_pago_20_repara_documento_incompleto(self):
        cliente = self._cliente('EMSEGA MARKET reparación')
        venta = self._venta_credito(cliente, '162480.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='28C06FD3-D87D-45C5-8C4D-D4927FCD3A64',
            monto=Money('162480.00', 'MXN'),
            venta=venta,
        )
        incompleto = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.PAGO,
            subtipo=DocumentoCFDI.SubtipoDocumento.RECIBO_PAGO,
            uuid='10BEF933-60EF-45B5-AB78-40C7D9A6246D',
            monto=Money('0.00', 'XXX'),
        )
        parsed = parse_cfdi(XML_RECIBO_PAGO_20.encode())

        pago, documento, _subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertNotEqual(documento.id, incompleto.id)
        self.assertEqual(documento.monto, Money('162480.00', 'MXN'))
        self.assertEqual(documento.pago_venta_id, pago.id)
        self.assertEqual(
            DocumentoCFDI.objects.filter(uuid=parsed['uuid']).count(), 1
        )

    def test_recibo_pago_usd_conserva_tipo_cambio_del_complemento(self):
        """Un REP en USD debe guardar su TipoCambioP para no subvaluar el
        equivalente en pesos (monto_pago_mxn)."""
        cliente = self._cliente('Cliente REP USD')
        venta = self._venta_credito(cliente, '2000.00', moneda='USD')
        uuid_factura = 'AA000000-0000-0000-0000-000000000001'
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_EXPORTACION,
            uuid=uuid_factura,
            monto=Money('2000.00', 'USD'),
            moneda='USD',
            venta=venta,
        )
        xml = (
            XML_RECIBO_PAGO_20
            .replace('MonedaP="MXN"', 'MonedaP="USD"')
            .replace('TipoCambioP="1"', 'TipoCambioP="17.50"')
            .replace('Monto="162480.00"', 'Monto="2000.00"')
            .replace('ImpSaldoAnt="162480.00" ImpPagado="162480.00"',
                     'ImpSaldoAnt="2000.00" ImpPagado="2000.00"')
            .replace('IdDocumento="28C06FD3-D87D-45C5-8C4D-D4927FCD3A64"',
                     f'IdDocumento="{uuid_factura}"')
            .replace('UUID="10BEF933-60EF-45B5-AB78-40C7D9A6246D"',
                     'UUID="BB000000-0000-0000-0000-000000000002"')
        )
        parsed = parse_cfdi(xml.encode())

        pago, _documento, subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertEqual(subtipo, 'recibo_pago')
        self.assertEqual(pago.monto_pago, Money('2000.00', 'USD'))
        self.assertEqual(pago.tipo_cambio, Decimal('17.5000'))
        self.assertEqual(pago.monto_pago_mxn, Decimal('35000.00'))

    def test_match_producto_usa_conceptos_del_cfdi(self):
        parsed = parse_cfdi(XML_MULTI_CONCEPTOS.encode())

        producto = match_producto(parsed)

        self.assertEqual(producto, self.producto)

    def test_servicio_no_se_propone_como_producto(self):
        parsed = parse_cfdi(XML_INGRESO_SERVICIO.encode())

        self.assertIsNone(match_producto(parsed))
        self.assertIsNone(sugerir_producto_desde_cfdi(parsed))

    def test_importar_ingreso_servicio_no_crea_producto(self):
        cliente = self._cliente('Jose Feliciano Lopez')
        parsed = parse_cfdi(XML_INGRESO_SERVICIO.encode())
        productos_antes = Producto.objects.count()

        venta, documento, subtipo = importar_cfdi(
            parsed, cliente=cliente, sucursal=self.sucursal, cuenta=self.cuenta,
        )

        self.assertEqual(subtipo, 'ingreso_servicio')
        self.assertEqual(documento.subtipo, 'ingreso_servicio')
        self.assertEqual(documento.venta_id, venta.id)
        self.assertIsNone(venta.producto_id)
        self.assertEqual(venta.tipo_registro, Ventas.TipoRegistro.SERVICIO)
        self.assertEqual(
            venta.descripcion,
            'Servicio de trabajo agrícola 4 has fumigación.',
        )
        self.assertEqual(Producto.objects.count(), productos_antes)

    def test_importar_ingreso_mixto_se_detiene_para_revision(self):
        cliente = self._cliente('Cliente Mixto')
        parsed = parse_cfdi(XML_INGRESO_MIXTO.encode())

        with self.assertRaisesMessage(ValueError, 'mezcla productos y servicios'):
            importar_cfdi(parsed, cliente=cliente)

        self.assertFalse(
            DocumentoCFDI.objects.filter(uuid=parsed['uuid']).exists()
        )

    def test_sugerir_producto_repetido_en_varios_conceptos(self):
        parsed = {
            'descripcion': 'Soya',
            'conceptos': [
                {
                    'descripcion': 'Soya',
                    'clave_prod_serv': '10151516',
                    'no_identificacion': '01010110',
                    'clave_unidad': 'A75',
                },
                {
                    'descripcion': '  Soya  ',
                    'clave_prod_serv': '10151516',
                    'no_identificacion': '01010110',
                    'clave_unidad': 'A75',
                },
            ],
        }

        sugerencia = sugerir_producto_desde_cfdi(parsed)

        self.assertEqual(sugerencia['nombre'], 'Soya')
        self.assertEqual(sugerencia['variedad'], 'Soya')
        self.assertEqual(sugerencia['clave_sat'], '10151516')
        self.assertEqual(sugerencia['no_identificacion'], '01010110')
        self.assertEqual(sugerencia['clave_unidad'], 'A75')

    def test_no_sugiere_un_producto_si_los_conceptos_son_distintos(self):
        parsed = {
            'conceptos': [
                {'descripcion': 'Soya'},
                {'descripcion': 'Maíz'},
            ],
        }

        self.assertIsNone(sugerir_producto_desde_cfdi(parsed))

    def test_crear_producto_desde_cfdi_reutiliza_el_catalogo(self):
        parsed = {
            'descripcion': 'Soya',
            'conceptos': [{
                'descripcion': 'Soya',
                'clave_prod_serv': '10151516',
                'no_identificacion': '01010110',
                'clave_unidad': 'A75',
            }],
            '_no_identificacion': '01010110',
            '_fraccion_arancelaria': '',
        }

        producto, creado = crear_producto_desde_cfdi(parsed)

        self.assertTrue(creado)
        self.assertEqual(producto.nombre, 'Soya')
        self.assertEqual(producto.variedad, 'Soya')
        self.assertEqual(producto.precio_unitario, 0)
        self.assertIn('Clave SAT: 10151516', producto.descripcion)
        self.assertIn('No. identificación: 01010110', producto.descripcion)
        self.assertEqual(match_producto(parsed), producto)

        mismo_producto, creado_nuevamente = crear_producto_desde_cfdi(parsed)
        self.assertFalse(creado_nuevamente)
        self.assertEqual(mismo_producto, producto)

    def test_importar_venta_sin_producto_muestra_error_claro(self):
        cliente = self._cliente('Cliente sin producto CFDI')
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed.update({
            'descripcion': 'Producto agrícola sin variedad',
            'conceptos': [{
                'descripcion': 'Producto agrícola sin variedad',
                'no_identificacion': '',
            }],
            '_no_identificacion': '',
            '_fraccion_arancelaria': '',
        })

        with self.assertRaisesMessage(
            ValueError,
            'Selecciona un producto para importar este CFDI como venta.',
        ):
            importar_cfdi(parsed, cliente=cliente)

    def test_match_cliente_nacional_prioriza_rfc(self):
        cliente = self._cliente('Grupo Karicy SA de CV')
        cliente.rfc = 'GKA971127HY7'
        cliente.save(update_fields=['rfc'])
        parsed = {
            '_receptor_nombre': 'GRUPO KARYCY',
            '_receptor_rfc': 'GKA971127HY7',
        }

        self.assertEqual(match_cliente(parsed), cliente)

    def test_match_cliente_extranjero_usa_registro_fiscal(self):
        cliente = self._cliente('Panorama Produce LTD')
        cliente.rfc = Cliente.RFC_GENERICO_EXTRANJERO
        cliente.residencia_fiscal = 'CAN'
        cliente.numero_registro_fiscal = '834911224'
        cliente.save(update_fields=[
            'rfc', 'residencia_fiscal', 'numero_registro_fiscal',
        ])
        parsed = {
            '_receptor_nombre': 'PANORAMA PRODUCE LTD',
            '_receptor_rfc': Cliente.RFC_GENERICO_EXTRANJERO,
            '_receptor_residencia_fiscal': 'CAN',
            '_receptor_num_reg_id_trib': '834911224',
        }

        self.assertEqual(match_cliente(parsed), cliente)

    def test_crear_cliente_desde_cfdi_precarga_datos_fiscales(self):
        parsed = parse_cfdi(XML_40_INGRESO.encode())

        cliente, creado = crear_cliente_desde_cfdi(parsed, pais=self.pais)

        self.assertTrue(creado)
        self.assertEqual(cliente.nombre, 'Panorama Produce SA')
        self.assertEqual(cliente.rfc, Cliente.RFC_GENERICO_EXTRANJERO)
        self.assertEqual(cliente.residencia_fiscal, 'CAN')
        self.assertEqual(cliente.numero_registro_fiscal, '834911224')
        self.assertEqual(cliente.codigo_postal_fiscal, '40906')
        self.assertEqual(cliente.regimen_fiscal, '616')
        self.assertEqual(cliente.tipo_cliente, Cliente.TipoCliente.CONTADO)

        mismo_cliente, creado_nuevamente = crear_cliente_desde_cfdi(
            parsed, pais=self.pais,
        )
        self.assertFalse(creado_nuevamente)
        self.assertEqual(mismo_cliente, cliente)

    def test_importar_venta_crea_venta_y_documento(self):
        cliente = self._cliente('Cliente Import CFDI')
        parsed = parse_cfdi(XML_40_INGRESO.encode())

        venta, doc, subtipo = importar_cfdi(
            parsed, cliente=cliente, producto=self.producto,
            sucursal=self.sucursal, cuenta=self.cuenta,
        )

        self.assertEqual(subtipo, 'venta_nacional')
        self.assertIsNotNone(venta)
        self.assertEqual(doc.subtipo, 'venta_nacional')
        self.assertEqual(doc.cliente_id, cliente.id)
        self.assertEqual(venta.cliente_id, cliente.id)
        self.assertEqual(str(doc.monto.amount), '13125.00')
        cliente.refresh_from_db()
        self.assertEqual(cliente.residencia_fiscal, 'CAN')
        self.assertEqual(cliente.numero_registro_fiscal, '834911224')

    def test_importar_venta_contado_sin_cuenta_muestra_error(self):
        cliente = self._cliente('Cliente Contado sin cuenta')
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed['uuid'] = 'AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA'
        parsed['folio_factura'] = 'B 2991 | AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA'

        with self.assertRaisesMessage(
            ValueError,
            'Selecciona la cuenta bancaria para esta venta de contado.',
        ):
            importar_cfdi(
                parsed, cliente=cliente, producto=self.producto,
                sucursal=self.sucursal,
            )

    def test_importar_venta_credito_sin_cuenta_se_crea_con_cuenta_nula(self):
        cliente = self._cliente('Cliente Credito sin cuenta')
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed['uuid'] = 'BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB'
        parsed['folio_factura'] = 'B 2992 | BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB'
        parsed['modalidad_pago'] = 'Credito'

        venta, doc, subtipo = importar_cfdi(
            parsed, cliente=cliente, producto=self.producto,
            sucursal=self.sucursal,
        )

        self.assertEqual(subtipo, 'venta_nacional')
        self.assertIsNone(venta.cuenta_id)
        self.assertEqual(venta.modalidad_pago, Ventas.ModalidadPago.CREDITO)

    def test_importar_venta_credito_con_termino_calcula_fecha_vencimiento(self):
        cliente = self._cliente('Cliente Credito con termino')
        termino = TerminoCredito.objects.create(
            nombre='RC Net 30', dias_credito=30, activo=True,
        )
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed['uuid'] = 'BBBBBBBB-CCCC-DDDD-EEEE-BBBBBBBBBBBB'
        parsed['folio_factura'] = 'B 2994 | BBBBBBBB-CCCC-DDDD-EEEE-BBBBBBBBBBBB'
        parsed['modalidad_pago'] = 'Credito'
        parsed['fecha_emision_cfdi'] = date(2026, 2, 1)

        venta, doc, subtipo = importar_cfdi(
            parsed, cliente=cliente, producto=self.producto,
            sucursal=self.sucursal, termino_credito=termino,
        )

        self.assertEqual(venta.termino_credito_id, termino.id)
        self.assertEqual(venta.fecha_vencimiento, date(2026, 3, 3))

    def test_importar_venta_sin_sucursal_muestra_error(self):
        cliente = self._cliente('Cliente sin sucursal')
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed['uuid'] = 'CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC'
        parsed['folio_factura'] = 'B 2993 | CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC'

        with self.assertRaisesMessage(
            ValueError,
            'Selecciona la sucursal para importar esta venta.',
        ):
            importar_cfdi(
                parsed, cliente=cliente, producto=self.producto,
                cuenta=self.cuenta,
            )

    def test_uuid_duplicado_no_crea_una_segunda_venta(self):
        cliente = self._cliente('Cliente UUID Duplicado')
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        importar_cfdi(
            parsed, cliente=cliente, producto=self.producto,
            sucursal=self.sucursal, cuenta=self.cuenta,
        )
        ventas_antes = Ventas.objects.count()

        with self.assertRaisesMessage(ValueError, 'ya fue importado'):
            importar_cfdi(parsed, cliente=cliente, producto=self.producto)

        self.assertEqual(Ventas.objects.count(), ventas_antes)
        self.assertEqual(
            DocumentoCFDI.objects.filter(uuid=parsed['uuid']).count(),
            1,
        )

    def test_importar_nota_cargo_vincula_venta_padre(self):
        cliente = self._cliente('Cliente Nota Cargo Import')
        venta_padre = self._venta_credito(cliente, '10000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo=DocumentoCFDI.TipoDocumento.INGRESO,
            subtipo=DocumentoCFDI.SubtipoDocumento.VENTA_NACIONAL,
            uuid='11111111-1111-1111-1111-111111111111',
            monto=Money('10000.00', 'MXN'),
            venta=venta_padre,
        )

        parsed = parse_cfdi(XML_NOTA_CARGO.encode())
        _obj, doc, subtipo = importar_cfdi(parsed, cliente=cliente)

        self.assertEqual(subtipo, 'nota_cargo')
        self.assertEqual(doc.venta_id, venta_padre.id)
        self.assertEqual(doc.subtipo, 'nota_cargo')

    def test_importar_remanente_cero_guarda_documento_sin_anticipo(self):
        cliente = self._cliente('Cliente Remanente Cero')
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed.update({
            'uuid': '38E576C9-E87F-49A9-9F86-FD79DE7FCAFC',
            'folio_factura': 'B 2020 | 38E576C9-E87F-49A9-9F86-FD79DE7FCAFC',
            'descripcion': 'REMANENTE DE ANTICIPO',
            'monto': Decimal('0.00'),
        })

        objeto, doc, subtipo = importar_cfdi(parsed, cliente=cliente)

        self.assertEqual(subtipo, 'remanente_anticipo')
        self.assertEqual(objeto, doc)
        self.assertEqual(doc.monto, Money('0.00', 'MXN'))
        self.assertIsNone(doc.anticipo_id)
        self.assertFalse(
            Anticipo.objects.filter(uuid_cfdi=parsed['uuid']).exists()
        )

    def test_importar_remanente_positivo_crea_anticipo(self):
        cliente = self._cliente('Cliente Remanente Positivo')
        parsed = parse_cfdi(XML_40_INGRESO.encode())
        parsed.update({
            'uuid': '99999999-9999-9999-9999-999999999999',
            'folio_factura': 'B 2024 | 99999999-9999-9999-9999-999999999999',
            'descripcion': 'REMANENTE DE ANTICIPO',
            'monto': Decimal('1234.56'),
        })

        anticipo, doc, subtipo = importar_cfdi(
            parsed, cliente=cliente, cuenta=self.cuenta,
        )

        self.assertEqual(subtipo, 'remanente_anticipo')
        self.assertEqual(anticipo.monto, Money('1234.56', 'MXN'))
        self.assertEqual(doc.anticipo_id, anticipo.id)

    def test_importar_venta_guarda_conceptos_y_pdf(self):
        import tempfile
        from django.core.files.base import ContentFile
        from django.test import override_settings

        cliente = self._cliente('Cliente Conceptos PDF')
        parsed = parse_cfdi(XML_MULTI_CONCEPTOS.encode())

        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            _venta, doc, subtipo = importar_cfdi(
                parsed,
                cliente=cliente,
                producto=self.producto,
                sucursal=self.sucursal,
                cuenta=self.cuenta,
                archivo_pdf=ContentFile(
                    b'%PDF-1.4 fake',
                    name='66666666-6666-6666-6666-666666666666.pdf',
                ),
            )

        self.assertEqual(subtipo, 'venta_nacional')
        self.assertEqual(len(doc.conceptos), 2)
        self.assertEqual(doc.conceptos[0]['no_identificacion'], 'TOMMY')
        self.assertEqual(doc.conceptos[0]['cantidad'], '800')
        self.assertEqual(doc.conceptos[0]['clave_unidad'], 'H87')
        self.assertTrue(doc.archivo_pdf.name.endswith('.pdf'))


# =============================================================================
# Conciliación de CFDI (saldo por cliente)
# =============================================================================

class ConciliacionCFDITest(ReporteCobranzaBaseTest):

    def test_conciliacion_filtra_rep_por_fecha_pago(self):
        from ventas.services.conciliacion_service import (
            conciliacion_cliente,
            pagos_rep_por_moneda,
        )

        cliente = self._cliente('Cliente REP por fecha de pago')
        rep_dentro = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-FECHA-DENTRO',
            fecha_emision=date(2026, 1, 10),
            monto=Money('900.00', 'MXN'),
            detalle_complemento={
                'pagos': [
                    {
                        'fecha_pago': '2026-03-15',
                        'doctos': [
                            {'uuid': 'FACTURA-A', 'imp_pagado': '100.00', 'moneda': 'MXN'},
                        ],
                    },
                    {
                        'fecha_pago': '2026-04-01',
                        'doctos': [
                            {'uuid': 'FACTURA-A', 'imp_pagado': '200.00', 'moneda': 'MXN'},
                        ],
                    },
                ],
            },
        )
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-FECHA-FUERA',
            fecha_emision=date(2026, 3, 15),
            monto=Money('50.00', 'MXN'),
            detalle_complemento={
                'pagos': [
                    {
                        'fecha_pago': '2026-02-15',
                        'doctos': [
                            {'uuid': 'FACTURA-B', 'imp_pagado': '50.00', 'moneda': 'MXN'},
                        ],
                    },
                ],
            },
        )
        periodo = cliente.documentos_cfdi.filter(subtipo='recibo_pago')

        por_moneda = pagos_rep_por_moneda(
            periodo, date(2026, 3, 1), date(2026, 3, 31),
        )
        fila = conciliacion_cliente(
            cliente, date(2026, 3, 1), date(2026, 3, 31),
        )

        self.assertEqual(por_moneda, {'MXN': Decimal('100.00')})
        self.assertAlmostEqual(fila['detalle']['recibos_pago']['MXN'], 100.00)
        self.assertEqual(
            fila['rep_desglose'][0]['fecha_fuente'], 'FechaPago',
        )
        self.assertEqual(fila['rep_desglose'][0]['fecha_pago'], date(2026, 3, 15))

    def test_rep_multimoneda_conserva_moneda_de_aplicacion(self):
        from ventas.services.conciliacion_service import pagos_rep_por_moneda

        cliente = self._cliente('Cliente REP multimoneda aplicada')
        rep = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-MULTIMONEDA',
            monto=Money('22157.78', 'USD'),
            moneda='USD',
            detalle_complemento={
                'pagos': [
                    {
                        'fecha_pago': '2026-03-15',
                        'monto': '22157.78',
                        'moneda': 'USD',
                        'doctos': [
                            {'uuid': 'FACTURA-MXN', 'imp_pagado': '398840.00', 'moneda': 'MXN'},
                            {'uuid': 'FACTURA-USD', 'imp_pagado': '100.00', 'moneda': 'USD'},
                        ],
                    },
                ],
            },
        )

        por_moneda = pagos_rep_por_moneda([rep])

        self.assertEqual(
            por_moneda,
            {'MXN': Decimal('398840.00'), 'USD': Decimal('100.00')},
        )

    def test_conciliacion_historico_rep_usa_fecha_emision_y_marca_respaldo(self):
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente REP histórico sin detalle')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-HISTORICO-SIN-JSON',
            fecha_emision=date(2026, 3, 15),
            monto=Money('250.00', 'MXN'),
            moneda='MXN',
        )

        fila = conciliacion_cliente(
            cliente, date(2026, 3, 1), date(2026, 3, 31),
        )

        self.assertAlmostEqual(fila['detalle']['recibos_pago']['MXN'], 250.00)
        rep = fila['rep_desglose'][0]
        self.assertEqual(rep['fecha_fuente'], 'fecha_emision')
        self.assertTrue(rep['es_legacy'])
        self.assertTrue(rep['requiere_revision'])

    def test_rep_exacto_no_se_resta_dos_veces_del_pago_operativo(self):
        import json

        from ventas.services.conciliacion_service import (
            _rehidratar_fila,
            _serializar_fila,
            conciliacion_cliente,
        )

        cliente = self._cliente('Cliente REP exacto aplicado parcialmente')
        venta = self._venta_credito(cliente, '446880.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='I',
            subtipo='venta_nacional',
            uuid='FACTURA-REP-EXACTO',
            monto=Money('446880.00', 'MXN'),
            venta=venta,
        )
        pago = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 3),
            monto_pago=Money('446880.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            uuid_rep='REP-EXACTO-PARCIAL',
        )
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-EXACTO-PARCIAL',
            fecha_emision=date(2026, 7, 3),
            monto=Money('446880.00', 'MXN'),
            venta=venta,
            pago_venta=pago,
            detalle_complemento={
                'vinculo_pago': {'estado': 'uuid_coincidente'},
                'pagos': [
                    {
                        'fecha_pago': '2026-07-03',
                        'doctos': [
                            {
                                'uuid': 'FACTURA-REP-EXACTO',
                                'imp_pagado': '398840.00',
                                'saldo_insoluto': '48040.00',
                                'moneda': 'MXN',
                            },
                        ],
                    },
                ],
            },
        )

        fila = conciliacion_cliente(cliente)
        rep = fila['rep_desglose'][0]
        serializada = _serializar_fila(fila)
        json.dumps(serializada)
        rehidratada = _rehidratar_fila(serializada, cliente)

        self.assertAlmostEqual(fila['saldo_por_moneda']['MXN'], 48040.00)
        self.assertAlmostEqual(rep['diferencia_operativo_fiscal'], 48040.00)
        self.assertEqual(rep['estado_vinculo'], 'uuid_coincidente')
        self.assertEqual(
            rehidratada['rep_desglose'][0]['fecha_pago'], date(2026, 7, 3),
        )

    def test_rep_exacto_sin_docto_no_oculta_pago_operativo(self):
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente REP sin DoctoRelacionado')
        venta = self._venta_credito(cliente, '1000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='I',
            subtipo='venta_nacional',
            monto=Money('1000.00', 'MXN'),
            venta=venta,
        )
        pago = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 3),
            monto_pago=Money('1000.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            uuid_rep='REP-SIN-DOCTO',
        )
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-SIN-DOCTO',
            monto=Money('1000.00', 'MXN'),
            venta=venta,
            pago_venta=pago,
            detalle_complemento={
                'pagos': [{'fecha_pago': '2026-07-03', 'doctos': []}],
            },
        )

        fila = conciliacion_cliente(cliente)

        self.assertAlmostEqual(fila['detalle']['cobros_contado']['MXN'], 1000.00)
        self.assertAlmostEqual(fila['saldo_por_moneda']['MXN'], 0.00)

    def test_rep_con_pago_exacto_y_docto_de_otra_venta_sigue_pendiente(self):
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente REP Docto de otra venta')
        venta_pago = self._venta_credito(cliente, '1000.00')
        venta_docto = self._venta_credito(cliente, '2000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='I',
            subtipo='venta_nacional',
            uuid='FACTURA-VENTA-PAGO',
            monto=Money('1000.00', 'MXN'),
            venta=venta_pago,
        )
        factura_docto = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='I',
            subtipo='venta_nacional',
            uuid='FACTURA-OTRA-VENTA',
            monto=Money('2000.00', 'MXN'),
            venta=venta_docto,
        )
        pago = PagoVenta.objects.create(
            venta=venta_pago,
            fecha_pago=date(2026, 7, 3),
            monto_pago=Money('100.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            uuid_rep='REP-DOCTO-CRUZADO',
        )
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-DOCTO-CRUZADO',
            monto=Money('100.00', 'MXN'),
            venta=venta_pago,
            pago_venta=pago,
            detalle_complemento={
                'vinculo_pago': {'estado': 'uuid_coincidente'},
                'pagos': [{
                    'fecha_pago': '2026-07-03',
                    'doctos': [{
                        'uuid': 'FACTURA-OTRA-VENTA',
                        'imp_pagado': '100.00',
                        'saldo_insoluto': '1900.00',
                        'moneda': 'MXN',
                    }],
                }],
            },
        )

        fila = conciliacion_cliente(cliente)
        rep = next(
            item for item in fila['rep_desglose']
            if item['uuid_factura'] == factura_docto.uuid
        )

        self.assertEqual(rep['documento_factura_id'], factura_docto.pk)
        self.assertEqual(rep['estado_vinculo'], 'revision_requerida')
        self.assertEqual(rep['motivo_vinculo'], 'venta_documento_discordante')
        self.assertTrue(rep['requiere_revision'])

    def test_rep_con_pago_exacto_y_docto_no_encontrado_sigue_pendiente(self):
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente REP Docto faltante')
        venta = self._venta_credito(cliente, '1000.00')
        pago = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 3),
            monto_pago=Money('100.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            uuid_rep='REP-DOCTO-FALTANTE',
        )
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-DOCTO-FALTANTE',
            monto=Money('100.00', 'MXN'),
            venta=venta,
            pago_venta=pago,
            detalle_complemento={
                'vinculo_pago': {'estado': 'uuid_coincidente'},
                'pagos': [{
                    'fecha_pago': '2026-07-03',
                    'doctos': [{
                        'uuid': 'FACTURA-ELIMINADA',
                        'imp_pagado': '100.00',
                        'moneda': 'MXN',
                    }],
                }],
            },
        )

        rep = conciliacion_cliente(cliente)['rep_desglose'][0]

        self.assertEqual(rep['estado_vinculo'], 'revision_requerida')
        self.assertEqual(rep['motivo_vinculo'], 'uuid_documento_no_encontrado')
        self.assertTrue(rep['requiere_revision'])

    def test_bga_rep_parcial_muestra_diferencia_y_vinculo_pendiente(self):
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente BGA diferencia REP')
        venta = self._venta_credito(cliente, '446880.00')
        factura = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='I',
            subtipo='venta_nacional',
            uuid='FACTURA-BGA-446880',
            monto=Money('446880.00', 'MXN'),
            moneda='MXN',
            venta=venta,
        )
        PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 7, 3),
            monto_pago=Money('446880.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
            uuid_rep='REP-BGA-UUID-NO-COINCIDENTE',
        )
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='P',
            subtipo='recibo_pago',
            uuid='REP-BGA-UUID',
            fecha_emision=date(2026, 7, 3),
            monto=Money('398840.00', 'MXN'),
            moneda='MXN',
            venta=venta,
            detalle_complemento={
                'vinculo_pago': {'estado': 'no_encontrado'},
                'pagos': [
                    {
                        'fecha_pago': '2026-07-03',
                        'monto': '398840.00',
                        'moneda': 'MXN',
                        'doctos': [
                            {
                                'uuid': 'FACTURA-BGA-446880',
                                'imp_pagado': '398840.00',
                                'saldo_insoluto': '48040.00',
                                'moneda': 'MXN',
                            },
                        ],
                    },
                ],
            },
        )

        fila = conciliacion_cliente(cliente)

        rep = fila['rep_desglose'][0]
        self.assertAlmostEqual(rep['monto_operativo'], 446880.00)
        self.assertAlmostEqual(rep['monto_rep_aplicado'], 398840.00)
        self.assertAlmostEqual(rep['diferencia_operativo_fiscal'], 48040.00)
        self.assertAlmostEqual(rep['imp_saldo_insoluto'], 48040.00)
        self.assertEqual(rep['documento_factura_id'], factura.pk)
        self.assertEqual(rep['folio_rep'], '')
        self.assertEqual(rep['estado_vinculo'], 'revision_requerida')
        self.assertAlmostEqual(fila['saldo_por_moneda']['MXN'], 0.00)

    def test_saldo_conciliado_agrega_ingresos_y_egresos(self):
        cliente = self._cliente('Cliente Conciliación')

        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            monto=Money('10000.00', 'MXN'),
        )
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='ingreso_servicio',
            monto=Money('1000.00', 'MXN'),
        )
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='nota_cargo',
            monto=Money('500.00', 'MXN'),
        )
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='E', subtipo='nota_credito',
            monto=Money('200.00', 'MXN'),
        )
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='P', subtipo='recibo_pago',
            monto=Money('3000.00', 'MXN'),
        )
        self._anticipo(cliente, '1000.00')

        # 10000 producto + 1000 servicio + 500 - 200 - 3000 - 1000 = 7300
        self.assertAlmostEqual(cliente.saldo_conciliado(), 7300.00)

    def test_otros_ingresos_sin_cfdi_suma_al_facturado_y_al_saldo(self):
        """Un ingreso capturado sin CFDI ('otros_ingresos') se comporta como una
        factura: suma al facturado y al saldo conciliado del cliente."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente Otros Ingresos')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='otros_ingresos',
            monto=Money('1500.00', 'MXN'),
        )

        self.assertAlmostEqual(cliente.saldo_conciliado(), 1500.00)
        fila = conciliacion_cliente(cliente)
        self.assertAlmostEqual(
            fila['detalle']['facturado'].get('MXN', 0.0), 1500.00
        )
        self.assertAlmostEqual(fila['saldo_por_moneda'].get('MXN', 0.0), 1500.00)

    def _venta_contado(self, cliente, monto, moneda='MXN',
                       fecha=date(2026, 2, 1)):
        """Venta de contado (PUE): queda pagada al crearse, sin REP."""
        return Ventas.objects.create(
            cliente=cliente,
            sucursal_id=self.sucursal,
            producto=self.producto,
            agente_id=self.agente,
            cuenta=self.cuenta,
            tipo_venta='Nacional',
            tipo_registro='VENTA',
            modalidad_pago='Contado',
            monto=Money(monto, moneda),
            cantidad=Decimal('100.000'),
            fecha_salida_manifiesto=fecha,
            fecha_deposito=fecha,
        )

    def test_venta_contado_facturada_no_genera_saldo(self):
        """Una factura de contado (PUE) no debe aparecer como saldo por cobrar."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente Contado')
        venta = self._venta_contado(cliente, '5000.00', moneda='USD')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_exportacion',
            monto=Money('5000.00', 'USD'), moneda='USD', venta=venta,
        )

        self.assertAlmostEqual(cliente.saldo_conciliado(), 0.0)
        fila = conciliacion_cliente(cliente)
        self.assertAlmostEqual(fila['saldo_por_moneda'].get('USD', 0.0), 0.0)

    def test_desglose_cobros_contado_identifica_ventas_pagos_y_cfdi(self):
        """El detalle de cobros debe explicar el total y su vínculo fiscal."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente con desglose de cobros')

        venta_con_cfdi = self._venta_contado(cliente, '1000.00')
        Ventas.objects.filter(pk=venta_con_cfdi.pk).update(carga='CARGA-CONTADO')
        factura_contado = DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            folio='F-1000', uuid='11111111-1111-1111-1111-111111111111',
            monto=Money('1000.00', 'MXN'), venta=venta_con_cfdi,
        )

        venta_sin_cfdi = self._venta_contado(cliente, '240.00')

        venta_con_pago = self._venta_credito(cliente, '5000.00')
        Ventas.objects.filter(pk=venta_con_pago.pk).update(carga='CARGA-CREDITO')
        factura_credito = DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            folio='F-5000', uuid='22222222-2222-2222-2222-222222222222',
            monto=Money('5000.00', 'MXN'), venta=venta_con_pago,
        )
        pago = PagoVenta.objects.create(
            venta=venta_con_pago,
            fecha_pago=date(2026, 3, 4),
            monto_pago=Money('400.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
        )
        recibo = DocumentoCFDI.objects.create(
            cliente=cliente, tipo='P', subtipo='recibo_pago',
            folio='REP-100', uuid='33333333-3333-3333-3333-333333333333',
            monto=Money('100.00', 'MXN'), venta=venta_con_pago,
            pago_venta=pago,
        )

        fila = conciliacion_cliente(cliente)
        desglose = fila['cobros_contado_desglose']['MXN']
        por_venta = {item['venta_id']: item for item in desglose}

        self.assertAlmostEqual(fila['detalle']['cobros_contado']['MXN'], 1540.00)
        self.assertAlmostEqual(sum(item['monto'] for item in desglose), 1540.00)

        contado = por_venta[venta_con_cfdi.pk]
        self.assertEqual(contado['tipo'], 'venta_contado')
        self.assertEqual(contado['referencia'], 'CARGA-CONTADO')
        self.assertEqual(contado['fechas'], [date(2026, 2, 1)])
        self.assertEqual(contado['moneda'], 'MXN')
        self.assertEqual(contado['documentos_cfdi'][0]['id'], factura_contado.pk)

        sin_cfdi = por_venta[venta_sin_cfdi.pk]
        self.assertEqual(sin_cfdi['documentos_cfdi'], [])

        pago_sin_rep = por_venta[venta_con_pago.pk]
        self.assertEqual(pago_sin_rep['tipo'], 'pago_sin_rep')
        self.assertEqual(pago_sin_rep['referencia'], 'CARGA-CREDITO')
        self.assertEqual(pago_sin_rep['fechas'], [date(2026, 3, 4)])
        self.assertAlmostEqual(pago_sin_rep['monto'], 300.00)
        self.assertEqual(
            {doc['id'] for doc in pago_sin_rep['documentos_cfdi']},
            {factura_credito.pk, recibo.pk},
        )


    def test_venta_credito_pagada_por_rep_no_resta_doble(self):
        """El pago registrado por REP no debe descontarse dos veces."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente REP')
        venta = self._venta_credito(cliente, '8000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            monto=Money('8000.00', 'MXN'), venta=venta,
        )
        pago = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 3, 1),
            monto_pago=Money('8000.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
        )
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='P', subtipo='recibo_pago',
            monto=Money('8000.00', 'MXN'), venta=venta, pago_venta=pago,
        )
        venta.actualizar_estado_cobranza()
        venta.refresh_from_db()

        self.assertAlmostEqual(cliente.saldo_conciliado(), 0.0)
        fila = conciliacion_cliente(cliente)
        self.assertAlmostEqual(fila['saldo_por_moneda'].get('MXN', 0.0), 0.0)


class ConciliacionOrigenTemplateTest(SimpleTestCase):

    def _render_rep_row(self, fila):
        from django.contrib.auth.models import AnonymousUser
        from django.template.loader import render_to_string
        from django.test import RequestFactory, override_settings
        from django.utils import translation

        request = RequestFactory().get('/admin/')
        request.user = AnonymousUser()
        with override_settings(ROOT_URLCONF='ventas.tests'), \
                translation.override('es-MX'):
            return render_to_string(
                'admin/ventas/conciliacion.html',
                {
                    'title': 'Conciliación',
                    'site_title': 'Admin',
                    'filas': [fila],
                    'clientes': [],
                    'monedas': ['MXN'],
                    'estado_saldo_choices': [],
                    'incidencia_choices': [],
                    'fecha_inicio': '',
                    'fecha_fin': '',
                    'selected_cliente_id': '',
                    'selected_moneda': 'MXN',
                    'selected_estado_saldo': '',
                    'selected_incidencia': '',
                },
                request=request,
            )

    def _rep_fila(self, rep):
        cliente = SimpleNamespace(id=88, nombre='Cliente BGA')
        return {
            'cliente': cliente,
            'detalle': {
                'facturado': {'MXN': 446880.00},
                'notas_cargo': {},
                'notas_credito': {},
                'recibos_pago': {'MXN': rep['monto_rep_aplicado']},
                'cobros_contado': {'MXN': 48040.00},
                'anticipos_disponibles': {},
            },
            'cobros_contado_desglose': {
                'MXN': [{
                    'tipo': 'pago_sin_rep',
                    'venta_id': 741,
                    'referencia': 'BGA-VENTA',
                    'fechas': [date(2026, 7, 3)],
                    'monto': 48040.00,
                    'moneda': 'MXN',
                    'monto_operativo': 446880.00,
                    'rep_aplicado': 398840.00,
                    'diferencia_operativo_fiscal': 48040.00,
                    'estado_vinculo': 'revision_requerida',
                    'requiere_revision': True,
                    'fuente_fecha_rep': 'FechaPago',
                    'uuids_rep': [rep['uuid_rep']],
                    'documentos_cfdi': [],
                }],
            },
            'rep_desglose': [rep],
            'rep_desglose_por_moneda': {'MXN': [rep]},
            'pagos_mxn': 446880.00,
            'saldo_por_moneda': {'MXN': 0.00},
            'total_documentos': 2,
            'documentos_sin_venta': 0,
            'sin_venta_detalle': [],
        }

    def test_desglose_bga_muestra_pago_rep_y_referencia_eliminada(self):
        rep = {
            'documento_id': 52,
            'uuid_rep': 'REP-BGA-UUID',
            'folio_rep': '',
            'uuid_factura': 'FACTURA-BGA-UUID',
            'documento_factura_id': 61,
            'venta_id': 741,
            'fecha_pago': date(2026, 7, 3),
            'fecha_fuente': 'FechaPago',
            'es_legacy': False,
            'monto_rep_aplicado': 398840.00,
            'moneda': 'MXN',
            'imp_saldo_insoluto': 48040.00,
            'monto_operativo': 446880.00,
            'moneda_operativa': 'MXN',
            'diferencia_operativo_fiscal': 48040.00,
            'estado_vinculo': 'revision_requerida',
            'motivo_vinculo': 'no_encontrado',
            'requiere_revision': True,
        }

        html = self._render_rep_row(self._rep_fila(rep))

        self.assertIn('Pago operativo', html)
        self.assertIn('REP aplicado', html)
        self.assertIn('Diferencia operativo-fiscal', html)
        self.assertIn('Remanente según REP', html)
        self.assertIn('Revisión requerida', html)
        self.assertIn('UUID no encontrado', html)
        self.assertIn('Folio REP no registrado', html)
        self.assertIn('Fecha de Pago', html)
        self.assertIn('446,880.00', html)
        self.assertIn('398,840.00', html)
        self.assertIn('48,040.00', html)
        self.assertIn('admin/ventas/documentocfdi/61/change/', html)

    def test_historico_marca_fecha_emision_como_respaldo(self):
        rep = {
            'documento_id': 70,
            'uuid_rep': 'REP-HISTORICO',
            'folio_rep': '',
            'uuid_factura': '',
            'documento_factura_id': None,
            'venta_id': None,
            'fecha_pago': date(2026, 3, 15),
            'fecha_fuente': 'fecha_emision',
            'es_legacy': True,
            'monto_rep_aplicado': 250.00,
            'moneda': 'MXN',
            'imp_saldo_insoluto': None,
            'monto_operativo': None,
            'moneda_operativa': '',
            'diferencia_operativo_fiscal': None,
            'estado_vinculo': 'revision_requerida',
            'motivo_vinculo': 'no_encontrado',
            'requiere_revision': True,
        }

        html = self._render_rep_row(self._rep_fila(rep))

        self.assertIn('Fecha de emisión (respaldo)', html)
        self.assertIn('Monto histórico', html)

    def test_cobro_contado_expone_origen_y_avisa_si_no_hay_cfdi(self):
        from django.template.loader import render_to_string
        from django.test import RequestFactory, override_settings
        from django.contrib.auth.models import AnonymousUser

        cliente = SimpleNamespace(id=81, nombre='Cliente trazable')
        fila = {
            'cliente': cliente,
            'detalle': {
                'facturado': {},
                'notas_cargo': {},
                'notas_credito': {},
                'recibos_pago': {},
                'cobros_contado': {'MXN': 48040.00},
                'anticipos_disponibles': {},
            },
            'cobros_contado_desglose': {
                'MXN': [{
                    'tipo': 'venta_contado',
                    'venta_id': 741,
                    'referencia': 'CARGA-SIN-CFDI',
                    'fechas': [date(2026, 2, 1)],
                    'monto': 48040.00,
                    'moneda': 'MXN',
                    'documentos_cfdi': [],
                }],
            },
            'pagos_mxn': 48040.00,
            'saldo_por_moneda': {'MXN': 0.00},
            'total_documentos': 0,
            'documentos_sin_venta': 0,
            'sin_venta_detalle': [],
        }

        with override_settings(ROOT_URLCONF='ventas.tests'):
            request = RequestFactory().get('/admin/')
            request.user = AnonymousUser()
            html = render_to_string(
                'admin/ventas/conciliacion.html',
                {
                    'title': 'Conciliación',
                    'site_title': 'Admin',
                    'filas': [fila],
                    'clientes': [],
                    'monedas': ['MXN', 'USD'],
                    'estado_saldo_choices': [
                        ('deuda', 'Con deuda'),
                        ('favor', 'Saldo a favor'),
                        ('mixto', 'Saldos mixtos'),
                        ('cero', 'Sin saldo'),
                    ],
                    'incidencia_choices': [
                        ('any', 'Cualquier incidencia'),
                        ('cobro_sin_cfdi', 'Cobros sin CFDI vinculado'),
                        ('cfdi_sin_venta', 'CFDI sin venta asociada'),
                    ],
                    'fecha_inicio': '',
                    'fecha_fin': '',
                    'selected_cliente_id': '',
                    'selected_moneda': 'MXN',
                    'selected_estado_saldo': 'deuda',
                    'selected_incidencia': 'any',
                },
                request=request,
            )

        self.assertIn('data-conc-trigger', html)
        self.assertIn('CARGA-SIN-CFDI', html)
        self.assertIn('01/02/2026', html)
        self.assertIn('Sin CFDI vinculado', html)
        self.assertIn('admin/ventas/ventas/741/change/', html)
        self.assertIn('name="moneda"', html)
        self.assertIn('name="estado_saldo"', html)
        self.assertIn('name="incidencia"', html)
        self.assertIn('data-conc-origin-filter', html)


class ConciliacionFiltrosTest(SimpleTestCase):

    def setUp(self):
        self.filas = [
            {
                'cliente': SimpleNamespace(id=1, nombre='Cliente MXN'),
                'detalle': {
                    'facturado': {'MXN': 500.00},
                    'cobros_contado': {'MXN': 300.00},
                    'anticipos_disponibles': {},
                },
                'saldo_por_moneda': {'MXN': 200.00},
                'documentos_sin_venta': 0,
                'cobros_contado_desglose': {
                    'MXN': [{'documentos_cfdi': []}],
                },
            },
            {
                'cliente': SimpleNamespace(id=2, nombre='Cliente USD'),
                'detalle': {
                    'facturado': {'USD': 50.00},
                    'cobros_contado': {},
                    'anticipos_disponibles': {},
                },
                'saldo_por_moneda': {'USD': -50.00},
                'documentos_sin_venta': 1,
                'cobros_contado_desglose': {},
            },
            {
                'cliente': SimpleNamespace(id=3, nombre='Cliente Mixto'),
                'detalle': {
                    'facturado': {'MXN': 200.00, 'USD': 20.00},
                    'cobros_contado': {},
                    'anticipos_disponibles': {},
                },
                'saldo_por_moneda': {'MXN': 100.00, 'USD': -20.00},
                'documentos_sin_venta': 0,
                'cobros_contado_desglose': {
                    'MXN': [{'documentos_cfdi': [{'id': 90}]}],
                },
            },
        ]

    def test_combina_moneda_estado_e_incidencia_sin_recalcular_saldos(self):
        from ventas.services.conciliacion_service import (
            filtrar_filas_conciliacion,
        )

        resultado = filtrar_filas_conciliacion(
            self.filas,
            moneda='MXN',
            estado_saldo='deuda',
            incidencia='cobro_sin_cfdi',
        )

        self.assertEqual([f['cliente'].id for f in resultado], [1])
        self.assertEqual(resultado[0]['saldo_por_moneda'], {'MXN': 200.00})
        self.assertEqual(resultado[0]['detalle']['facturado'], {'MXN': 500.00})

    def test_detecta_saldos_mixtos_y_documentos_sin_venta(self):
        from ventas.services.conciliacion_service import (
            filtrar_filas_conciliacion,
            monedas_disponibles_conciliacion,
        )

        mixtos = filtrar_filas_conciliacion(self.filas, estado_saldo='mixto')
        cfdi_sin_venta = filtrar_filas_conciliacion(
            self.filas, incidencia='cfdi_sin_venta'
        )
        cualquier_incidencia = filtrar_filas_conciliacion(
            self.filas, incidencia='any'
        )

        self.assertEqual([f['cliente'].id for f in mixtos], [3])
        self.assertEqual([f['cliente'].id for f in cfdi_sin_venta], [2])
        self.assertEqual([f['cliente'].id for f in cualquier_incidencia], [1, 2])
        self.assertEqual(
            monedas_disponibles_conciliacion(self.filas), ['MXN', 'USD']
        )


class ConciliacionVistaFiltrosTest(ReporteCobranzaBaseTest):

    def test_vista_aplica_filtros_y_conserva_los_saldos_originales(self):
        from django.contrib.auth.models import AnonymousUser
        from django.core.cache import cache
        from django.test import RequestFactory

        cache.clear()
        cliente = self._cliente('Cliente Vista Filtros')
        Ventas.objects.create(
            cliente=cliente,
            sucursal_id=self.sucursal,
            producto=self.producto,
            agente_id=self.agente,
            cuenta=self.cuenta,
            tipo_venta='Nacional',
            tipo_registro='VENTA',
            modalidad_pago='Contado',
            monto=Money('125.00', 'MXN'),
            cantidad=Decimal('10.000'),
            fecha_salida_manifiesto=date(2026, 2, 1),
            fecha_deposito=date(2026, 2, 1),
        )
        request = RequestFactory().get('/admin/', {
            'moneda': 'MXN',
            'estado_saldo': 'favor',
            'incidencia': 'cobro_sin_cfdi',
        })
        request.user = AnonymousUser()
        model_admin = ClienteAdmin(Cliente, admin.site)

        response = model_admin.conciliacion_view(request)

        self.assertEqual(response.context_data['selected_moneda'], 'MXN')
        self.assertEqual(response.context_data['selected_estado_saldo'], 'favor')
        self.assertEqual(response.context_data['selected_incidencia'], 'cobro_sin_cfdi')
        self.assertEqual(
            [fila['cliente'].pk for fila in response.context_data['filas']],
            [cliente.pk],
        )
        self.assertEqual(
            response.context_data['filas'][0]['saldo_por_moneda'],
            {'MXN': -125.00},
        )

    def test_no_muestra_estado_mixto_al_filtrar_una_moneda(self):
        from django.contrib.auth.models import AnonymousUser
        from django.core.cache import cache
        from django.test import RequestFactory

        cache.clear()
        cliente = self._cliente('Cliente Saldos Mixtos')
        DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='I',
            subtipo='venta_nacional',
            monto=Money('100.00', 'MXN'),
            moneda='MXN',
        )
        Ventas.objects.create(
            cliente=cliente,
            sucursal_id=self.sucursal,
            producto=self.producto,
            agente_id=self.agente,
            cuenta=self.cuenta,
            tipo_venta='Exportación',
            tipo_registro='VENTA',
            modalidad_pago='Contado',
            monto=Money('5.00', 'USD'),
            cantidad=Decimal('1.000'),
            fecha_salida_manifiesto=date(2026, 2, 1),
            fecha_deposito=date(2026, 2, 1),
        )
        request = RequestFactory().get('/admin/', {
            'moneda': 'MXN',
            'estado_saldo': 'mixto',
        })
        request.user = AnonymousUser()
        model_admin = ClienteAdmin(Cliente, admin.site)

        response = model_admin.conciliacion_view(request)

        self.assertEqual(response.context_data['selected_moneda'], 'MXN')
        self.assertEqual(response.context_data['selected_estado_saldo'], '')
        self.assertNotIn(
            'mixto',
            [value for value, _label in response.context_data['estado_saldo_choices']],
        )


class CobradoMxnOrigenTest(ReporteCobranzaBaseTest):
    """
    Documenta el origen de la columna «Cobrado MXN» y por qué no tiene por qué
    coincidir con «Pagos (REP)».

    «Cobrado MXN» (= ``pagos_mxn``) NO sale del CFDI. Es el total de dinero
    realmente cobrado, expresado en pesos:
      - ``PagoVenta.monto_pago_mxn`` (pagos operativos, convertidos con su
        tipo de cambio), y
      - el ``monto_pagado`` de ventas de contado sin pago registrado (PUE),
        convertido con el tipo de cambio de la venta.

    «Pagos (REP)» (= ``detalle['recibos_pago']``) sale del ledger fiscal: suma
    los DocumentoCFDI con subtipo ``recibo_pago``, en su moneda, por el monto
    completo del comprobante. Por eso ambas pueden divergir.
    """

    def _venta_contado_usd(self, cliente, monto, tipo_cambio,
                           fecha=date(2026, 2, 1)):
        venta = Ventas.objects.create(
            cliente=cliente,
            sucursal_id=self.sucursal,
            producto=self.producto,
            agente_id=self.agente,
            cuenta=self.cuenta,
            tipo_venta='Nacional',
            tipo_registro='VENTA',
            modalidad_pago='Contado',
            monto=Money(monto, 'USD'),
            cantidad=Decimal('100.000'),
            fecha_salida_manifiesto=fecha,
            fecha_deposito=fecha,
        )
        Ventas.objects.filter(pk=venta.pk).update(
            tipo_cambio=Decimal(tipo_cambio)
        )
        venta.refresh_from_db()
        return venta

    def test_cobrado_mxn_de_contado_usd_es_equivalencia_fx(self):
        """Caso WORLD PRODUCE: contado en USD -> Cobrado MXN es el equivalente
        en pesos al tipo de cambio de la venta, no un dato del CFDI."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente Contado USD')
        venta = self._venta_contado_usd(cliente, '434000.00', '17.8260')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_exportacion',
            monto=Money('434000.00', 'USD'), moneda='USD', venta=venta,
        )

        fila = conciliacion_cliente(cliente)

        # 434,000 USD x 17.8260 = 7,736,484.00 (aprox. lo visto en pantalla)
        self.assertAlmostEqual(fila['pagos_mxn'], 7736484.00, places=2)
        # No hay ningún recibo de pago (REP) en el ledger fiscal...
        self.assertEqual(fila['detalle']['recibos_pago'], {})
        # ...el cobro de contado vive en dólares, no en pesos.
        self.assertAlmostEqual(
            fila['detalle']['cobros_contado'].get('USD', 0.0), 434000.00
        )

    def test_rep_sin_pagoventa_aparece_en_rep_pero_no_en_cobrado_mxn(self):
        """Un REP importado sin PagoVenta suma en «Pagos (REP)» pero no en
        «Cobrado MXN»: así se explica que la columna REP sea mayor."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente REP Huérfano')
        venta = self._venta_credito(cliente, '9000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            monto=Money('9000.00', 'MXN'), venta=venta,
        )
        # Complemento de pago importado pero sin PagoVenta asociado
        # (importación legacy o venta que ya no está en cobro).
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='P', subtipo='recibo_pago',
            monto=Money('4000.00', 'MXN'), venta=venta,
        )

        fila = conciliacion_cliente(cliente)

        self.assertAlmostEqual(fila['detalle']['recibos_pago']['MXN'], 4000.00)
        self.assertEqual(fila['pagos_mxn'], 0.0)

    def test_pagoventa_topado_al_saldo_deja_cobrado_mxn_bajo_el_rep(self):
        """Si el PagoVenta se topó al saldo (como hace la importación de REP),
        «Cobrado MXN» queda por debajo del monto del comprobante."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente REP Tope')
        venta = self._venta_credito(cliente, '5000.00')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            monto=Money('5000.00', 'MXN'), venta=venta,
        )
        pago = PagoVenta.objects.create(
            venta=venta,
            fecha_pago=date(2026, 3, 1),
            monto_pago=Money('5000.00', 'MXN'),
            cuenta_destino=self.cuenta,
            metodo_pago=PagoVenta.MetodoPago.TRANSFERENCIA,
        )
        # El CFDI (REP) declara 8,000 pero el pago operativo quedó en 5,000.
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='P', subtipo='recibo_pago',
            monto=Money('8000.00', 'MXN'), venta=venta, pago_venta=pago,
        )

        fila = conciliacion_cliente(cliente)

        self.assertAlmostEqual(fila['detalle']['recibos_pago']['MXN'], 8000.00)
        self.assertAlmostEqual(fila['pagos_mxn'], 5000.00)


class PagoVentaFormLabelTest(ReporteCobranzaBaseTest):
    """El selector de «Venta» en el admin de Pagos de Ventas no debe mostrar
    «None» cuando la venta no tiene número de carga."""

    def _etiqueta(self, venta):
        from ventas.forms_banking import PagoVentaForm

        form = PagoVentaForm()
        return dict(form.fields['venta'].choices)[venta.pk]

    def test_venta_sin_carga_usa_folio_interno_en_la_etiqueta(self):
        cliente = self._cliente('Cliente Sin Carga')
        venta = self._venta_credito(cliente, '1000.00')

        etiqueta = self._etiqueta(venta)

        self.assertNotIn('None', etiqueta)
        self.assertIn(cliente.nombre, etiqueta)
        self.assertIn(f'V-{venta.pk}', etiqueta)
        self.assertIn('Saldo:', etiqueta)

    def test_venta_con_carga_conserva_la_referencia(self):
        cliente = self._cliente('Cliente Con Carga')
        venta = self._venta_credito(cliente, '1000.00')
        Ventas.objects.filter(pk=venta.pk).update(carga='CARGA-123')
        venta.refresh_from_db()

        etiqueta = self._etiqueta(venta)

        self.assertIn('CARGA-123', etiqueta)
        self.assertNotIn('None', etiqueta)


class ConciliacionSaldoYCacheTest(ReporteCobranzaBaseTest):
    """El saldo conciliado del cliente debe venir de una sola fuente
    (saldo_por_moneda) y la conciliación global debe cachearse por rango."""

    def test_saldo_conciliado_es_la_suma_del_saldo_por_moneda(self):
        """Cliente multimoneda: el saldo total es la suma del desglose."""
        from ventas.services.conciliacion_service import saldo_por_moneda

        cliente = self._cliente('Cliente Saldo Unificado')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            monto=Money('1000.00', 'MXN'),
        )
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_exportacion',
            monto=Money('200.00', 'USD'), moneda='USD',
        )

        saldos = saldo_por_moneda(cliente)

        self.assertAlmostEqual(saldos.get('MXN'), 1000.00)
        self.assertAlmostEqual(saldos.get('USD'), 200.00)
        self.assertAlmostEqual(cliente.saldo_conciliado(), 1200.00)

    def test_saldo_conciliado_coincide_con_conciliacion_cliente(self):
        """saldo_conciliado() y conciliacion_cliente() no deben divergir."""
        from ventas.services.conciliacion_service import conciliacion_cliente

        cliente = self._cliente('Cliente Saldo Consistente')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='venta_nacional',
            monto=Money('5000.00', 'MXN'),
        )
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='P', subtipo='recibo_pago',
            monto=Money('2000.00', 'MXN'),
        )
        self._anticipo(cliente, '500.00')

        fila = conciliacion_cliente(cliente)
        esperado = round(sum(fila['saldo_por_moneda'].values()), 2)

        self.assertAlmostEqual(cliente.saldo_conciliado(), esperado)

    def test_conciliacion_global_filtra_por_cliente(self):
        """``conciliacion_global`` puede limitarse a un cliente (filtro)."""
        from ventas.services.conciliacion_service import conciliacion_global

        cliente_a = self._cliente('Cliente Filtro A')
        self._cliente('Cliente Filtro B')

        filas = conciliacion_global(cliente_id=cliente_a.pk)

        self.assertEqual([f['cliente'].pk for f in filas], [cliente_a.pk])

    def test_conciliacion_global_cachea_por_rango(self):
        """La segunda llamada con el mismo rango no recalcula por cliente: solo
        reevalúa la lista de clientes (1 consulta) y rehidrata desde el cache."""
        from django.core.cache import cache
        from django.test import override_settings
        from ventas.services.conciliacion_service import conciliacion_global

        caches_locmem = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        }
        self._cliente('Cliente Cache Conciliacion')

        with override_settings(CACHES=caches_locmem):
            cache.clear()
            conciliacion_global()  # primera: calcula y cachea
            with self.assertNumQueries(1):  # solo la consulta de clientes
                conciliacion_global()

    def test_conciliacion_global_rehidrata_desde_cache(self):
        """Al leer del cache, la fila conserva cliente, tipos (fecha/monto) y el
        desglose de documentos sin vincular."""
        from django.core.cache import cache
        from django.test import override_settings
        from ventas.services.conciliacion_service import conciliacion_global

        caches_locmem = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        }
        cliente = self._cliente('Cliente Cache Detalle')
        DocumentoCFDI.objects.create(
            cliente=cliente, tipo='I', subtipo='nota_cargo',
            monto=Money('300.00', 'MXN'), fecha_emision=date(2026, 3, 10),
        )

        with override_settings(CACHES=caches_locmem):
            cache.clear()
            primera = conciliacion_global()
            segunda = conciliacion_global()

        calculada = next(f for f in primera if f['cliente'].pk == cliente.pk)
        cacheada = next(f for f in segunda if f['cliente'].pk == cliente.pk)

        self.assertEqual(cacheada['cliente'].nombre, cliente.nombre)
        grupos = cacheada['sin_venta_detalle']
        self.assertEqual(len(grupos), 1)
        doc = grupos[0]['documentos'][0]
        self.assertEqual(doc['fecha'], date(2026, 3, 10))
        self.assertAlmostEqual(doc['monto'], 300.00)
        self.assertEqual(
            cacheada['saldo_por_moneda'], calculada['saldo_por_moneda']
        )

    def test_fila_serializada_conserva_fechas_y_cfdi_del_desglose(self):
        """El detalle de cobros sobrevive la serialización JSON de caché."""
        from ventas.services.conciliacion_service import (
            _rehidratar_fila,
            _serializar_fila,
            conciliacion_cliente,
        )

        cliente = self._cliente('Cliente Cache Cobros')
        venta = Ventas.objects.create(
            cliente=cliente,
            sucursal_id=self.sucursal,
            producto=self.producto,
            agente_id=self.agente,
            cuenta=self.cuenta,
            tipo_venta='Nacional',
            tipo_registro='VENTA',
            modalidad_pago='Contado',
            monto=Money('600.00', 'MXN'),
            cantidad=Decimal('100.000'),
            fecha_salida_manifiesto=date(2026, 2, 1),
            fecha_deposito=date(2026, 2, 1),
        )
        documento = DocumentoCFDI.objects.create(
            cliente=cliente,
            tipo='I',
            subtipo='venta_nacional',
            folio='CACHE-600',
            uuid='44444444-4444-4444-4444-444444444444',
            fecha_emision=date(2026, 2, 1),
            monto=Money('600.00', 'MXN'),
            venta=venta,
        )

        serializada = _serializar_fila(conciliacion_cliente(cliente))
        origen_json = serializada['cobros_contado_desglose']['MXN'][0]

        self.assertEqual(origen_json['fechas'], ['2026-02-01'])
        self.assertEqual(
            origen_json['documentos_cfdi'][0]['fecha_emision'], '2026-02-01'
        )
        self.assertEqual(origen_json['documentos_cfdi'][0]['id'], documento.pk)

        rehidratada = _rehidratar_fila(serializada, cliente)
        origen = rehidratada['cobros_contado_desglose']['MXN'][0]
        self.assertEqual(origen['fechas'], [date(2026, 2, 1)])
        self.assertEqual(
            origen['documentos_cfdi'][0]['fecha_emision'], date(2026, 2, 1)
        )


# =============================================================================
# Formulario de confirmación de importación individual
# =============================================================================

class CFDIConfirmFormTest(ReporteCobranzaBaseTest):

    def _payload(self, **overrides):
        data = {
            'monto': '1000.00',
            'moneda_venta': 'MXN',
            'tipo_cambio': '1.0000',
            'tipo_venta': 'Nacional',
            'modalidad_pago': 'Contado',
            'cantidad': '10.000',
            'fecha_salida_manifiesto': '2026-01-01',
            'fecha_deposito': '2026-01-01',
            'sucursal_id': self.sucursal.pk,
            'tipo_registro': 'VENTA',
            'producto': self.producto.pk,
            'cliente': self._cliente('Cliente Confirm Form').pk,
        }
        data.update(overrides)
        return data

    def test_requiere_cliente_o_crear_cliente(self):
        form = CFDIConfirmForm(self._payload(cliente=None))
        self.assertFalse(form.is_valid())
        self.assertIn('cliente', form.errors)

    def test_crear_cliente_requiere_pais(self):
        form = CFDIConfirmForm(self._payload(
            cliente=None,
            crear_cliente='on',
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('pais_cliente', form.errors)

    def test_acepta_crear_cliente_con_pais(self):
        form = CFDIConfirmForm(self._payload(
            cliente=None,
            crear_cliente='on',
            pais_cliente=self.pais.pk,
        ))
        self.assertTrue(form.is_valid(), form.errors)


# =============================================================================
# Análisis de Ventas (balances) — caracterización para el refactor
# =============================================================================

class VentasBalancesContextTest(ReporteCobranzaBaseTest):
    """Fija el comportamiento de ``build_ventas_balances_context`` antes de
    simplificar la función."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def _request(self, **params):
        from django.http import QueryDict

        q = QueryDict('', mutable=True)
        for key, value in params.items():
            q[key] = value
        return SimpleNamespace(GET=q)

    def _context(self, **params):
        from ventas.views import build_ventas_balances_context

        return build_ventas_balances_context(self._request(**params))

    def test_totales_y_agrupacion_mensual(self):
        cliente = self._cliente('Cliente Balances Mes')
        self._venta_credito(cliente, '1000.00', fecha=date(2026, 1, 10))
        self._venta_credito(cliente, '2000.00', fecha=date(2026, 2, 10))

        ctx = self._context(
            cliente_id=str(cliente.pk), year='2026', periodo='mensual',
        )

        self.assertAlmostEqual(ctx['total_ventas'], 3000.00)
        self.assertEqual(ctx['numero_transacciones'], 2)
        self.assertEqual(len(ctx['balances']), 2)
        self.assertAlmostEqual(ctx['balances'][0]['total_ventas'], 1000.00)
        self.assertAlmostEqual(ctx['balances'][1]['total_ventas'], 2000.00)
        self.assertAlmostEqual(ctx['balances'][1]['acumulado'], 3000.00)

    def test_filtra_por_cliente(self):
        cliente_a = self._cliente('Cliente Balances A')
        cliente_b = self._cliente('Cliente Balances B')
        self._venta_credito(cliente_a, '1000.00', fecha=date(2026, 1, 5))
        self._venta_credito(cliente_b, '9999.00', fecha=date(2026, 1, 5))

        ctx = self._context(
            cliente_id=str(cliente_a.pk), year='2026', periodo='mensual',
        )

        self.assertAlmostEqual(ctx['total_ventas'], 1000.00)
        self.assertEqual(
            [b['cliente_nombre'] for b in ctx['balances']],
            ['Cliente Balances A'],
        )

    def test_agrupacion_diaria(self):
        cliente = self._cliente('Cliente Balances Dia')
        self._venta_credito(cliente, '500.00', fecha=date(2026, 3, 5))
        self._venta_credito(cliente, '700.00', fecha=date(2026, 3, 5))

        ctx = self._context(
            cliente_id=str(cliente.pk), periodo='diario', tipo_fecha='rango',
            fecha_inicio='2026-03-01', fecha_fin='2026-03-31',
        )

        self.assertAlmostEqual(ctx['total_ventas'], 1200.00)
        self.assertEqual(len(ctx['balances']), 1)
        self.assertAlmostEqual(ctx['balances'][0]['total_ventas'], 1200.00)
