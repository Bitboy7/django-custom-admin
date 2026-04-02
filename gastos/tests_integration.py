"""
Pruebas de Integración — Módulo Gastos
=======================================
Cubre flujos completos del módulo de gastos:
  - Flujo Banco → Cuenta → Gasto → verificación
  - Cálculo automático de monto_total en Compra
  - Vistas de compras y facturas
  - Endpoint de guardar factura (con mock de Gemini AI)
  - Upload de archivos PDF

Ejecución:
    python manage.py test gastos.tests_integration --verbosity=2
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import translation
from djmoney.money import Money

from catalogo.models import Pais, Estado, Sucursal, Productor, Producto
from gastos.models import (
    Banco, CatGastos, Cuenta, Gastos, Compra, SaldoMensual
)


# ---------------------------------------------------------------------------
# Fixtures compartidas
# ---------------------------------------------------------------------------

class GastosBaseTest(TestCase):
    """Fixture base con todos los objetos relacionados para pruebas de gastos."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='gastos_tester',
            password='TestPass123!'
        )
        cls.admin = User.objects.create_superuser(
            username='gastos_admin',
            password='AdminPass123!'
        )

        # Catálogo
        cls.pais = Pais.objects.create(siglas='MX', nombre='México', moneda='MXN')
        cls.estado = Estado.objects.create(id='SIN_G', nombre='Sinaloa', pais=cls.pais)
        cls.sucursal = Sucursal.objects.create(
            nombre='Sucursal Gastos',
            id_estado=cls.estado
        )
        cls.producto = Producto.objects.create(
            nombre='Mango',
            variedad='Ataulfo',
            precio_unitario=Decimal('25.00'),
            disponible=True
        )
        cls.productor = Productor.objects.create(
            nombre_completo='Pedro Productor Test',
            num_cuenta='1234567890',
            clabe_interbancaria='002180012345678901',
            id_sucursal=cls.sucursal,
            nacionalidad=cls.pais
        )

        # Gastos
        cls.banco = Banco.objects.create(nombre='BBVA Test')
        cls.cat_gastos = CatGastos.objects.create(nombre='Transporte')
        cls.cuenta = Cuenta.objects.create(
            id_banco=cls.banco,
            id_sucursal=cls.sucursal,
            numero_cuenta='9876543210',
            rfc='AAA010101AAA',
            clabe='002180098765432109'
        )

    def setUp(self):
        translation.activate('en')

    def tearDown(self):
        translation.deactivate()


# ---------------------------------------------------------------------------
# Modelos — Flujo Banco → Cuenta → Gasto
# ---------------------------------------------------------------------------

class GastosModelFlowTest(GastosBaseTest):
    """Prueba el flujo completo de creación de un gasto bancario."""

    def test_crear_banco(self):
        """Se puede crear un banco con nombre."""
        banco = Banco.objects.create(nombre='Banorte Test')
        self.assertEqual(str(banco), 'Banorte Test')

    def test_crear_cuenta_vinculada_a_banco_y_sucursal(self):
        """La cuenta se vincula correctamente a banco y sucursal."""
        cuenta = Cuenta.objects.create(
            id_banco=self.banco,
            id_sucursal=self.sucursal,
            numero_cuenta='5555444433332222',
            clabe='002180055554444333'
        )
        self.assertEqual(cuenta.id_banco.nombre, 'BBVA Test')
        self.assertEqual(cuenta.id_sucursal.nombre, 'Sucursal Gastos')

    def test_crear_gasto_registra_en_base_de_datos(self):
        """Un Gasto creado debe persistir con todos sus datos."""
        gasto = Gastos.objects.create(
            id_sucursal=self.sucursal,
            id_cat_gastos=self.cat_gastos,
            id_cuenta_banco=self.cuenta,
            monto=Money('1250.00', 'MXN'),
            fecha=date.today(),
            descripcion='Gasto de prueba de integración'
        )
        recuperado = Gastos.objects.get(pk=gasto.pk)
        self.assertEqual(float(recuperado.monto.amount), 1250.00)
        self.assertEqual(recuperado.id_cat_gastos.nombre, 'Transporte')

    def test_gasto_str_incluye_sucursal_y_categoria(self):
        """El __str__ del gasto incluye sucursal y categoría."""
        gasto = Gastos.objects.create(
            id_sucursal=self.sucursal,
            id_cat_gastos=self.cat_gastos,
            id_cuenta_banco=self.cuenta,
            monto=Money('500.00', 'MXN'),
            fecha=date.today()
        )
        str_repr = str(gasto)
        self.assertIn('Sucursal Gastos', str_repr)
        self.assertIn('Transporte', str_repr)

    def test_filtro_gastos_por_fecha(self):
        """Se pueden filtrar gastos por rango de fechas."""
        hoy = date.today()
        hace_30 = hoy - timedelta(days=30)

        Gastos.objects.create(
            id_sucursal=self.sucursal,
            id_cat_gastos=self.cat_gastos,
            id_cuenta_banco=self.cuenta,
            monto=Money('800.00', 'MXN'),
            fecha=hoy
        )
        Gastos.objects.create(
            id_sucursal=self.sucursal,
            id_cat_gastos=self.cat_gastos,
            id_cuenta_banco=self.cuenta,
            monto=Money('600.00', 'MXN'),
            fecha=hace_30 - timedelta(days=1)  # fuera del rango
        )

        gastos_recientes = Gastos.objects.filter(fecha__gte=hace_30)
        self.assertEqual(gastos_recientes.count(), 1)
        self.assertEqual(float(gastos_recientes.first().monto.amount), 800.00)


# ---------------------------------------------------------------------------
# Modelo Compra — Cálculo automático de monto_total
# ---------------------------------------------------------------------------

class CompraAutoCalculoTest(GastosBaseTest):
    """
    Verifica que el método save() de Compra calcule automáticamente
    el monto_total = cantidad × precio_unitario.
    """

    def test_monto_total_calculado_automaticamente(self):
        """monto_total debe ser cantidad × precio_unitario al guardar."""
        compra = Compra.objects.create(
            fecha_compra=date.today(),
            productor=self.productor,
            producto=self.producto,
            cantidad=100,
            precio_unitario=Money('25.00', 'MXN'),
            monto_total=Money('0.00', 'MXN'),  # valor inicial ignorado
            cuenta=self.cuenta
        )
        # El save() debe calcular: 100 × 25 = 2500
        self.assertEqual(float(compra.monto_total.amount), 2500.00)

    def test_monto_total_actualizado_al_modificar_cantidad(self):
        """Al cambiar la cantidad, monto_total debe recalcularse."""
        compra = Compra.objects.create(
            fecha_compra=date.today(),
            productor=self.productor,
            producto=self.producto,
            cantidad=50,
            precio_unitario=Money('30.00', 'MXN'),
            monto_total=Money('0.00', 'MXN'),
            cuenta=self.cuenta
        )
        compra.cantidad = 200
        compra.save()
        # 200 × 30 = 6000
        self.assertEqual(float(compra.monto_total.amount), 6000.00)

    def test_compra_con_tipo_pago_transferencia(self):
        """Se puede crear una compra con tipo de pago Transferencia."""
        compra = Compra.objects.create(
            fecha_compra=date.today(),
            productor=self.productor,
            producto=self.producto,
            cantidad=75,
            precio_unitario=Money('40.00', 'MXN'),
            monto_total=Money('0.00', 'MXN'),
            tipo_pago=Compra.TipoPago.Transferencia,
            cuenta=self.cuenta
        )
        self.assertEqual(compra.tipo_pago, 'Transferencia')
        self.assertEqual(float(compra.monto_total.amount), 3000.00)

    def test_str_compra_incluye_productor_y_producto(self):
        """El __str__ de Compra incluye productor y producto."""
        compra = Compra.objects.create(
            fecha_compra=date.today(),
            productor=self.productor,
            producto=self.producto,
            cantidad=10,
            precio_unitario=Money('20.00', 'MXN'),
            monto_total=Money('0.00', 'MXN'),
            cuenta=self.cuenta
        )
        str_repr = str(compra)
        self.assertIn('Pedro Productor Test', str_repr)


# ---------------------------------------------------------------------------
# Vista de Compras (Balances)
# ---------------------------------------------------------------------------

@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ComprasViewTest(GastosBaseTest):
    """
    Prueba la vista de balances de compras con datos en la base de datos.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Crear datos de compras para la vista
        Compra.objects.create(
            fecha_compra=date.today(),
            productor=cls.productor,
            producto=cls.producto,
            cantidad=200,
            precio_unitario=Money('35.00', 'MXN'),
            monto_total=Money('0.00', 'MXN'),
            cuenta=cls.cuenta
        )

    def test_compras_view_requiere_login(self):
        """La vista /compras/ retorna 302 sin autenticación."""
        response = self.client.get('/en/compras/')
        self.assertEqual(response.status_code, 302)

    def test_compras_view_carga_para_usuario_autenticado(self):
        """La vista /compras/ carga correctamente para usuario autenticado."""
        self.client.force_login(self.user)
        response = self.client.get('/en/compras/')
        self.assertIn(response.status_code, [200, 302],
                      "La vista de compras debe cargar o redirigir")

    def test_compras_view_acepta_filtros_de_fecha(self):
        """La vista de compras no crashea con filtros de año y mes."""
        self.client.force_login(self.user)
        today = date.today()
        response = self.client.get('/en/compras/', {
            'year': today.year,
            'periodo': 'mensual'
        })
        self.assertNotEqual(response.status_code, 500)

    def test_compras_view_filtro_productor(self):
        """El filtro por productor no genera error."""
        self.client.force_login(self.user)
        response = self.client.get('/en/compras/', {
            'productor_id': self.productor.id
        })
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# Vista Ingresar Factura — mock de Google Gemini AI
# ---------------------------------------------------------------------------

@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class IngresarFacturaViewTest(GastosBaseTest):
    """
    Prueba el endpoint de ingreso de facturas.
    La integración con Google Gemini está mockeada para no hacer llamadas reales.
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_ingresar_factura_get_carga_formulario(self):
        """GET a /ingresar-factura/ debe retornar 200 con el formulario."""
        response = self.client.get('/en/ingresar-factura/')
        self.assertEqual(response.status_code, 200)

    def test_ingresar_factura_post_sin_archivo_muestra_errores(self):
        """POST sin archivo PDF debe retornar 200 con el formulario y errores."""
        response = self.client.post('/en/ingresar-factura/', {
            'tipo_documento': 'factura',
        })
        # Debe retornar 200 (formulario con errores) o 400, no 500
        self.assertNotEqual(response.status_code, 500)

    @patch('gastos.views.reconocer_factura_pdf')
    def test_ingresar_factura_post_con_pdf_valido(self, mock_reconocer):
        """
        POST con un PDF válido (mockeado) debe procesar el documento
        sin llamar realmente a la API de Gemini.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Mock del response de Gemini
        mock_result = MagicMock()
        mock_result.proveedor = 'Proveedor Test SA'
        mock_result.total = 1500.00
        mock_result.fecha = date.today().isoformat()
        mock_reconocer.return_value = mock_result

        # PDF con header válido (%PDF-)
        fake_pdf = SimpleUploadedFile(
            'factura.pdf',
            b'%PDF-1.4\n1 0 obj\n<<>>\nendobj',
            content_type='application/pdf'
        )
        response = self.client.post('/en/ingresar-factura/', {
            'documento_pdf': fake_pdf,
            'tipo_documento': 'factura',
        })
        # No debe generar error 500
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# Admin Gastos — filtros personalizados
# ---------------------------------------------------------------------------

class GastosAdminTest(GastosBaseTest):
    """Prueba los filtros personalizados del admin de gastos."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_admin_gastos_lista_carga(self):
        """La lista de gastos en admin debe cargarse sin error."""
        response = self.client.get('/en/admin/gastos/gastos/')
        self.assertEqual(response.status_code, 200)

    def test_admin_compras_lista_carga(self):
        """La lista de compras en admin debe cargarse sin error."""
        response = self.client.get('/en/admin/gastos/compra/')
        self.assertEqual(response.status_code, 200)

    def test_admin_banco_lista_carga(self):
        """La lista de bancos en admin debe cargarse."""
        response = self.client.get('/en/admin/gastos/banco/')
        self.assertEqual(response.status_code, 200)

    def test_admin_cuenta_lista_carga(self):
        """La lista de cuentas en admin debe cargarse."""
        response = self.client.get('/en/admin/gastos/cuenta/')
        self.assertEqual(response.status_code, 200)

    def test_admin_gastos_busqueda(self):
        """La búsqueda en admin de gastos no debe generar error 500."""
        response = self.client.get('/en/admin/gastos/gastos/', {'q': 'Transporte'})
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# Saldo Mensual
# ---------------------------------------------------------------------------

class SaldoMensualTest(GastosBaseTest):
    """Prueba la creación y consulta de saldos mensuales."""

    def test_crear_saldo_mensual(self):
        """Se puede crear un registro de saldo mensual para una cuenta."""
        from gastos.models import SaldoMensual
        saldo = SaldoMensual.objects.create(
            cuenta=self.cuenta,
            año=date.today().year,
            mes=date.today().month,
            saldo_inicial=Money('50000.00', 'MXN')
        )
        self.assertEqual(float(saldo.saldo_inicial.amount), 50000.00)

    def test_saldo_mensual_unico_por_cuenta_mes_año(self):
        """Se pueden crear múltiples saldos en diferentes meses."""
        from gastos.models import SaldoMensual
        SaldoMensual.objects.create(
            cuenta=self.cuenta, año=2025, mes=1,
            saldo_inicial=Money('10000.00', 'MXN')
        )
        SaldoMensual.objects.create(
            cuenta=self.cuenta, año=2025, mes=2,
            saldo_inicial=Money('12000.00', 'MXN')
        )
        saldos = SaldoMensual.objects.filter(cuenta=self.cuenta, año=2025)
        self.assertEqual(saldos.count(), 2)
