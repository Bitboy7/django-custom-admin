"""
Pruebas de Integración — Módulo Capital Inversiones
====================================================
Cubre flujos completos del módulo de inversiones:
  - Flujo CatInversion → Inversion → RendimientoInversion
  - Cálculo automático de porcentaje de rendimiento (ROI)
  - Dashboard y reportes (GET views)
  - APIs JSON de balance mensual y distribución por categorías
  - Validación de tipos de movimiento (ENTRADA/SALIDA)

Ejecución:
    python manage.py test capital_inversiones.tests_integration --verbosity=2
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import translation
from djmoney.money import Money

from catalogo.models import Pais, Estado, Sucursal
from gastos.models import Banco, Cuenta
from capital_inversiones.models import CatInversion, Inversion, RendimientoInversion


# ---------------------------------------------------------------------------
# Fixture base compartida
# ---------------------------------------------------------------------------

class CapitalBaseTest(TestCase):
    """Fixture base con todos los objetos relacionados para pruebas de capital."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='capital_tester',
            password='TestPass123!'
        )
        cls.admin = User.objects.create_superuser(
            username='capital_admin',
            password='AdminPass123!'
        )

        # Catálogo
        cls.pais = Pais.objects.create(siglas='MX', nombre='México', moneda='MXN')
        cls.estado = Estado.objects.create(id='SIN_C', nombre='Sinaloa', pais=cls.pais)
        cls.sucursal_a = Sucursal.objects.create(
            nombre='Sucursal Alpha', id_estado=cls.estado
        )
        cls.sucursal_b = Sucursal.objects.create(
            nombre='Sucursal Beta', id_estado=cls.estado
        )

        # Cuenta bancaria
        cls.banco = Banco.objects.create(nombre='Banco Capital Test')
        cls.cuenta = Cuenta.objects.create(
            id_banco=cls.banco,
            id_sucursal=cls.sucursal_a,
            numero_cuenta='0000111122223333'
        )

        # Categorías de inversión
        cls.cat_capital_trabajo = CatInversion.objects.create(
            nombre='Capital de Trabajo',
            descripcion='Operaciones corrientes',
            activa=True
        )
        cls.cat_activos_fijos = CatInversion.objects.create(
            nombre='Activos Fijos',
            descripcion='Inversión en maquinaria y equipo',
            activa=True
        )
        cls.cat_socios = CatInversion.objects.create(
            nombre='Aportación de Socios',
            descripcion='Capital social',
            activa=True
        )

    def setUp(self):
        translation.activate('en')

    def tearDown(self):
        translation.deactivate()


# ---------------------------------------------------------------------------
# Modelo CatInversion
# ---------------------------------------------------------------------------

class CatInversionModelTest(CapitalBaseTest):
    """Prueba el modelo de categorías de inversión."""

    def test_crear_categoria_inversion(self):
        """Se puede crear una categoría de inversión con nombre único."""
        cat = CatInversion.objects.create(
            nombre='Inversión Inmobiliaria',
            activa=True
        )
        self.assertEqual(str(cat), 'Inversión Inmobiliaria')

    def test_categoria_str_retorna_nombre(self):
        """El __str__ retorna el nombre de la categoría."""
        self.assertEqual(str(self.cat_capital_trabajo), 'Capital de Trabajo')

    def test_categorias_ordenadas_por_nombre(self):
        """Las categorías deben estar ordenadas alfabéticamente por nombre."""
        categorias = list(CatInversion.objects.values_list('nombre', flat=True))
        self.assertEqual(categorias, sorted(categorias))

    def test_categoria_activa_por_defecto(self):
        """Una categoría nueva está activa por defecto."""
        cat = CatInversion.objects.create(nombre='Nueva Categoria Test')
        self.assertTrue(cat.activa)


# ---------------------------------------------------------------------------
# Modelo Inversion — Flujo de creación
# ---------------------------------------------------------------------------

class InversionModelFlowTest(CapitalBaseTest):
    """Prueba el flujo de creación y consulta de inversiones."""

    def test_crear_inversion_salida(self):
        """Se puede crear una inversión de tipo SALIDA (inversión real)."""
        inversion = Inversion.objects.create(
            id_sucursal=self.sucursal_a,
            id_cat_inversion=self.cat_capital_trabajo,
            id_cuenta_banco=self.cuenta,
            tipo_movimiento=Inversion.TipoMovimiento.SALIDA,
            monto=Money('500000.00', 'MXN'),
            fecha=date.today(),
            descripcion='Inversión de capital de trabajo Q1'
        )
        recuperada = Inversion.objects.get(pk=inversion.pk)
        self.assertEqual(float(recuperada.monto.amount), 500000.00)
        self.assertEqual(recuperada.tipo_movimiento, 'SALIDA')

    def test_crear_inversion_entrada(self):
        """Se puede crear una inversión de tipo ENTRADA (recuperación de capital)."""
        inversion = Inversion.objects.create(
            id_sucursal=self.sucursal_b,
            id_cat_inversion=self.cat_socios,
            id_cuenta_banco=self.cuenta,
            tipo_movimiento=Inversion.TipoMovimiento.ENTRADA,
            monto=Money('200000.00', 'MXN'),
            fecha=date.today()
        )
        self.assertEqual(inversion.tipo_movimiento, 'ENTRADA')

    def test_inversion_str_incluye_tipo_sucursal_categoria(self):
        """El __str__ incluye tipo, sucursal y categoría."""
        inversion = Inversion.objects.create(
            id_sucursal=self.sucursal_a,
            id_cat_inversion=self.cat_activos_fijos,
            id_cuenta_banco=self.cuenta,
            tipo_movimiento=Inversion.TipoMovimiento.SALIDA,
            monto=Money('150000.00', 'MXN'),
            fecha=date.today()
        )
        str_repr = str(inversion)
        self.assertIn('SALIDA', str_repr)
        self.assertIn('Sucursal Alpha', str_repr)
        self.assertIn('Activos Fijos', str_repr)

    def test_filtrar_inversiones_por_sucursal(self):
        """Se pueden filtrar inversiones por sucursal."""
        Inversion.objects.create(
            id_sucursal=self.sucursal_a, id_cat_inversion=self.cat_capital_trabajo,
            id_cuenta_banco=self.cuenta, tipo_movimiento='SALIDA',
            monto=Money('100000.00', 'MXN'), fecha=date.today()
        )
        Inversion.objects.create(
            id_sucursal=self.sucursal_b, id_cat_inversion=self.cat_capital_trabajo,
            id_cuenta_banco=self.cuenta, tipo_movimiento='SALIDA',
            monto=Money('80000.00', 'MXN'), fecha=date.today()
        )
        solo_alpha = Inversion.objects.filter(id_sucursal=self.sucursal_a)
        self.assertEqual(solo_alpha.count(), 1)
        self.assertEqual(float(solo_alpha.first().monto.amount), 100000.00)

    def test_filtrar_inversiones_por_rango_de_fechas(self):
        """Se pueden filtrar inversiones por rango de fechas."""
        hoy = date.today()
        hace_60 = hoy - timedelta(days=60)

        Inversion.objects.create(
            id_sucursal=self.sucursal_a, id_cat_inversion=self.cat_capital_trabajo,
            id_cuenta_banco=self.cuenta, tipo_movimiento='SALIDA',
            monto=Money('300000.00', 'MXN'), fecha=hoy
        )
        Inversion.objects.create(
            id_sucursal=self.sucursal_a, id_cat_inversion=self.cat_capital_trabajo,
            id_cuenta_banco=self.cuenta, tipo_movimiento='SALIDA',
            monto=Money('250000.00', 'MXN'), fecha=hace_60 - timedelta(days=1)
        )

        recientes = Inversion.objects.filter(fecha__gte=hace_60)
        self.assertEqual(recientes.count(), 1)


# ---------------------------------------------------------------------------
# Modelo RendimientoInversion — Cálculo automático de ROI
# ---------------------------------------------------------------------------

class RendimientoInversionROITest(CapitalBaseTest):
    """
    Prueba el cálculo automático de porcentaje de rendimiento (ROI).
    El modelo override save() para calcular: (monto_rendimiento / monto_inversion) × 100
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Inversión base: 1,000,000 MXN (tipo SALIDA, requerido por limit_choices_to)
        cls.inversion_base = Inversion.objects.create(
            id_sucursal=cls.sucursal_a,
            id_cat_inversion=cls.cat_capital_trabajo,
            id_cuenta_banco=cls.cuenta,
            tipo_movimiento=Inversion.TipoMovimiento.SALIDA,
            monto=Money('1000000.00', 'MXN'),
            fecha=date.today()
        )

    def test_rendimiento_calcula_porcentaje_automaticamente(self):
        """
        El porcentaje de rendimiento debe calcularse en save():
        monto_rendimiento / monto_inversion × 100
        """
        rendimiento = RendimientoInversion.objects.create(
            inversion=self.inversion_base,
            fecha_rendimiento=date.today(),
            monto_rendimiento=Money('50000.00', 'MXN'),  # 5% de 1,000,000
            tipo_rendimiento='Interés'
        )
        # 50,000 / 1,000,000 × 100 = 5.00%
        self.assertAlmostEqual(float(rendimiento.porcentaje_rendimiento), 5.00, places=1)

    def test_rendimiento_alto_roi(self):
        """Rendimiento del 20% se calcula correctamente."""
        rendimiento = RendimientoInversion.objects.create(
            inversion=self.inversion_base,
            fecha_rendimiento=date.today() - timedelta(days=30),
            monto_rendimiento=Money('200000.00', 'MXN'),  # 20% de 1,000,000
            tipo_rendimiento='Dividendo'
        )
        self.assertAlmostEqual(float(rendimiento.porcentaje_rendimiento), 20.00, places=1)

    def test_rendimiento_str_incluye_categoria_y_monto(self):
        """El __str__ del rendimiento incluye categoría y monto."""
        rendimiento = RendimientoInversion.objects.create(
            inversion=self.inversion_base,
            fecha_rendimiento=date.today(),
            monto_rendimiento=Money('30000.00', 'MXN'),
            tipo_rendimiento='Ganancia de Capital'
        )
        str_repr = str(rendimiento)
        self.assertIn('Capital de Trabajo', str_repr)
        self.assertIn('30,000', str_repr)

    def test_multiples_rendimientos_por_inversion(self):
        """Una inversión puede tener múltiples rendimientos registrados."""
        for mes in range(1, 4):
            RendimientoInversion.objects.create(
                inversion=self.inversion_base,
                fecha_rendimiento=date(date.today().year, mes, 1),
                monto_rendimiento=Money(f'{mes * 10000}.00', 'MXN'),
                tipo_rendimiento='Interés Mensual'
            )
        rendimientos = RendimientoInversion.objects.filter(inversion=self.inversion_base)
        self.assertEqual(rendimientos.count(), 3)


# ---------------------------------------------------------------------------
# Vistas del módulo de Capital Inversiones
# ---------------------------------------------------------------------------

@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CapitalViewsTest(CapitalBaseTest):
    """Prueba las vistas del módulo de capital inversiones."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Datos de inversiones para las vistas
        hoy = date.today()
        cls.inv_1 = Inversion.objects.create(
            id_sucursal=cls.sucursal_a,
            id_cat_inversion=cls.cat_capital_trabajo,
            id_cuenta_banco=cls.cuenta,
            tipo_movimiento=Inversion.TipoMovimiento.SALIDA,
            monto=Money('750000.00', 'MXN'),
            fecha=hoy.replace(day=1)
        )
        cls.inv_2 = Inversion.objects.create(
            id_sucursal=cls.sucursal_b,
            id_cat_inversion=cls.cat_activos_fijos,
            id_cuenta_banco=cls.cuenta,
            tipo_movimiento=Inversion.TipoMovimiento.SALIDA,
            monto=Money('1200000.00', 'MXN'),
            fecha=hoy.replace(day=1)
        )
        RendimientoInversion.objects.create(
            inversion=cls.inv_1,
            fecha_rendimiento=hoy,
            monto_rendimiento=Money('37500.00', 'MXN'),
            tipo_rendimiento='Interés'
        )

    def _login(self):
        self.client.force_login(self.user)

    def test_dashboard_requiere_autenticacion(self):
        """El dashboard de capital inversiones requiere autenticación."""
        response = self.client.get('/en/capital-inversiones/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_carga_para_usuario_autenticado(self):
        """El dashboard carga correctamente para usuario autenticado."""
        self._login()
        today = date.today()
        response = self.client.get('/en/capital-inversiones/dashboard/', {
            'fecha_inicio': today.replace(day=1).isoformat(),
            'fecha_fin': today.isoformat()
        })
        self.assertIn(response.status_code, [200, 302],
                      "El dashboard debe cargar sin error")

    def test_dashboard_sin_parametros_usa_mes_actual(self):
        """El dashboard usa el mes actual cuando no hay parámetros de fecha."""
        self._login()
        response = self.client.get('/en/capital-inversiones/dashboard/')
        self.assertNotEqual(response.status_code, 500)

    def test_reporte_por_sucursal_carga(self):
        """El reporte acumulado por sucursal no genera error."""
        self._login()
        response = self.client.get('/en/capital-inversiones/reporte/sucursal/')
        self.assertNotEqual(response.status_code, 500)

    def test_reporte_por_categoria_carga(self):
        """El reporte acumulado por categoría no genera error."""
        self._login()
        response = self.client.get('/en/capital-inversiones/reporte/categoria/')
        self.assertNotEqual(response.status_code, 500)

    def test_reporte_rendimientos_carga(self):
        """El reporte de rendimientos no genera error."""
        self._login()
        response = self.client.get('/en/capital-inversiones/reporte/rendimientos/')
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# APIs JSON del módulo de Capital
# ---------------------------------------------------------------------------

@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CapitalAPITest(CapitalBaseTest):
    """
    Prueba las APIs JSON del módulo de capital inversiones.
    Estas APIs alimentan las gráficas del dashboard.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        today = date.today()
        # Crear inversiones en múltiples meses para la API de balance mensual
        for i in range(3):
            mes = today.month - i if today.month - i > 0 else today.month
            Inversion.objects.create(
                id_sucursal=cls.sucursal_a,
                id_cat_inversion=cls.cat_capital_trabajo,
                id_cuenta_banco=cls.cuenta,
                tipo_movimiento=Inversion.TipoMovimiento.SALIDA,
                monto=Money(f'{(i + 1) * 100000}.00', 'MXN'),
                fecha=date(today.year, mes, 1)
            )

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_api_balance_mensual_requiere_autenticacion(self):
        """La API de balance mensual requiere autenticación."""
        self.client.logout()
        response = self.client.get('/en/capital-inversiones/api/balance-mensual/')
        self.assertEqual(response.status_code, 302)

    def test_api_balance_mensual_retorna_respuesta(self):
        """La API de balance mensual retorna una respuesta sin error."""
        today = date.today()
        response = self.client.get(
            '/en/capital-inversiones/api/balance-mensual/',
            {
                'fecha_inicio': date(today.year, 1, 1).isoformat(),
                'fecha_fin': today.isoformat()
            }
        )
        self.assertNotEqual(response.status_code, 500)

    def test_api_balance_mensual_sin_parametros(self):
        """La API maneja graciosamente la ausencia de parámetros de fecha."""
        response = self.client.get('/en/capital-inversiones/api/balance-mensual/')
        self.assertNotEqual(response.status_code, 500)

    def test_api_distribucion_categorias_retorna_respuesta(self):
        """La API de distribución por categorías retorna una respuesta sin error."""
        response = self.client.get(
            '/en/capital-inversiones/api/distribucion-categorias/'
        )
        self.assertNotEqual(response.status_code, 500)

    def test_api_distribucion_categorias_requiere_autenticacion(self):
        """La API de distribución requiere autenticación."""
        self.client.logout()
        response = self.client.get('/en/capital-inversiones/api/distribucion-categorias/')
        self.assertEqual(response.status_code, 302)

    def test_api_balance_mensual_con_payload_sql(self):
        """
        Las APIs JSON no son vulnerables a SQL injection en parámetros de fecha.
        (A03 — Inyección)
        """
        response = self.client.get(
            '/en/capital-inversiones/api/balance-mensual/',
            {'fecha_inicio': "' OR '1'='1", 'fecha_fin': "1; DROP TABLE--"}
        )
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# Admin Capital Inversiones
# ---------------------------------------------------------------------------

class CapitalAdminTest(CapitalBaseTest):
    """Prueba los admin views del módulo de capital inversiones."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_admin_inversiones_lista_carga(self):
        """La lista de inversiones en admin carga correctamente."""
        response = self.client.get('/en/admin/capital_inversiones/inversion/')
        self.assertEqual(response.status_code, 200)

    def test_admin_cat_inversion_lista_carga(self):
        """La lista de categorías de inversión carga correctamente."""
        response = self.client.get('/en/admin/capital_inversiones/catinversion/')
        self.assertEqual(response.status_code, 200)

    def test_admin_rendimientos_lista_carga(self):
        """La lista de rendimientos carga correctamente."""
        response = self.client.get('/en/admin/capital_inversiones/rendimientoinversion/')
        self.assertEqual(response.status_code, 200)

    def test_admin_inversiones_filtro_tipo(self):
        """El filtro por tipo de movimiento en admin no genera error."""
        response = self.client.get(
            '/en/admin/capital_inversiones/inversion/',
            {'tipo_movimiento': 'SALIDA'}
        )
        self.assertNotEqual(response.status_code, 500)
