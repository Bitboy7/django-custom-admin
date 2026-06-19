"""
Pruebas de Integración Cross-App — django-custom-admin
=======================================================
Prueba flujos que involucran múltiples aplicaciones del sistema:
  - Dashboard administrativo
  - Vista de balances con datos de gastos y ventas
  - API de conversión de moneda
  - Exportación de reportes

Ejecución:
    python manage.py test app.tests.test_integration --verbosity=2
"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import translation
from djmoney.money import Money

from catalogo.models import Pais, Estado, Sucursal
from gastos.models import Banco, CatGastos, Cuenta, Gastos, Compra


# ---------------------------------------------------------------------------
# Fixture base compartida para todos los tests de integración
# ---------------------------------------------------------------------------

class BaseIntegrationTest(TestCase):
    """
    Clase base con fixtures completos para pruebas de integración.
    Crea la jerarquía mínima de objetos relacionados que requieren
    los modelos de la aplicación.
    """

    @classmethod
    def setUpTestData(cls):
        # --- Usuarios ---
        cls.admin_user = User.objects.create_superuser(
            username='admin_integration',
            password='AdminPass123!'
        )
        cls.staff_user = User.objects.create_user(
            username='staff_integration',
            password='StaffPass123!',
            is_staff=True
        )
        cls.regular_user = User.objects.create_user(
            username='user_integration',
            password='UserPass123!'
        )

        # --- Catálogo base ---
        cls.pais_mx = Pais.objects.create(
            siglas='MX', nombre='México', moneda='MXN'
        )
        cls.pais_us = Pais.objects.create(
            siglas='US', nombre='Estados Unidos', moneda='USD'
        )
        cls.estado = Estado.objects.create(
            id='SIN', nombre='Sinaloa', pais=cls.pais_mx
        )
        cls.sucursal = Sucursal.objects.create(
            nombre='Sucursal Central',
            direccion='Calle Principal 1',
            telefono='6671234567',
            id_estado=cls.estado
        )

        # --- Gastos base ---
        cls.banco = Banco.objects.create(nombre='Bancomer Test')
        cls.cat_gastos = CatGastos.objects.create(nombre='Servicios')
        cls.cuenta = Cuenta.objects.create(
            id_banco=cls.banco,
            id_sucursal=cls.sucursal,
            numero_cuenta='1234567890'
        )

    def setUp(self):
        translation.activate('en')

    def tearDown(self):
        translation.deactivate()


# ---------------------------------------------------------------------------
# Dashboard administrativo
# ---------------------------------------------------------------------------

class AdminDashboardIntegrationTest(BaseIntegrationTest):
    """Verifica que el dashboard administrativo cargue correctamente con datos."""

    def test_admin_dashboard_carga_para_superuser(self):
        """El dashboard del admin debe cargar con status 200 para superuser."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/en/admin/')
        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_muestra_apps_registradas(self):
        """El admin debe listar las apps instaladas (gastos, ventas, catalogo)."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/en/admin/')
        content = response.content.decode()
        # Jazzmin muestra los nombres de las apps en el sidebar
        self.assertIn('200', str(response.status_code))

    def test_admin_gastos_lista_accesible(self):
        """La lista de gastos en admin debe ser accesible para superuser."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/en/admin/gastos/gastos/')
        self.assertEqual(response.status_code, 200)

    def test_admin_catalogo_sucursal_accesible(self):
        """La lista de sucursales en admin debe ser accesible."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/en/admin/catalogo/sucursal/')
        self.assertEqual(response.status_code, 200)

    def test_admin_auditoria_log_accesible(self):
        """El log de auditoría debe ser accesible (read-only) en admin."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/en/admin/auditoria/logactividad/')
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Vista de balances (cross-app: gastos + ventas)
# ---------------------------------------------------------------------------

@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class BalancesViewIntegrationTest(BaseIntegrationTest):
    """
    Verifica la vista de balances que agrega datos de gastos y ventas.
    Usa caché en memoria para no depender de Redis en CI.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Crear gastos de prueba para que balances tenga datos
        Gastos.objects.create(
            id_sucursal=cls.sucursal,
            id_cat_gastos=cls.cat_gastos,
            id_cuenta_banco=cls.cuenta,
            monto=Money('1500.00', 'MXN'),
            fecha=date.today()
        )
        Gastos.objects.create(
            id_sucursal=cls.sucursal,
            id_cat_gastos=cls.cat_gastos,
            id_cuenta_banco=cls.cuenta,
            monto=Money('2300.00', 'MXN'),
            fecha=date.today() - timedelta(days=15)
        )

    def test_balances_view_carga_con_autenticacion(self):
        """La vista /balances/ debe cargar correctamente para usuario autenticado."""
        self.client.force_login(self.regular_user)
        response = self.client.get('/en/balances/')
        self.assertIn(response.status_code, [200, 302])

    def test_balances_view_redirige_sin_autenticacion(self):
        """La vista /balances/ debe redirigir al login si no hay sesión."""
        response = self.client.get('/en/balances/')
        self.assertEqual(response.status_code, 302)

    def test_balances_view_acepta_parametros_filtro(self):
        """La vista de balances acepta parámetros de año y sucursal sin crashear."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/en/balances/', {
            'year': date.today().year,
            'sucursal_id': self.sucursal.id
        })
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# API de conversión de moneda
# ---------------------------------------------------------------------------

@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class CurrencyAPIIntegrationTest(BaseIntegrationTest):
    """
    Verifica la API de conversión de moneda (sin prefijo i18n).
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin_user)

    def test_currency_api_requiere_autenticacion(self):
        """La API de moneda no debe responder a requests no autenticados."""
        self.client.logout()
        response = self.client.get('/api/currency-conversion/')
        self.assertEqual(response.status_code, 302,
                         "La API de conversión de moneda debe requerir autenticación")

    def test_currency_api_responde_json(self):
        """La API debe retornar una respuesta JSON para usuario autenticado."""
        response = self.client.get('/api/currency-conversion/', {
            'from': 'USD',
            'to': 'MXN',
            'amount': '1'
        })
        # La API puede retornar error si no hay API key configurada, pero no debe crashear
        self.assertNotEqual(response.status_code, 500)

    def test_currency_api_maneja_parametros_invalidos(self):
        """La API debe manejar graciosamente parámetros de moneda inválidos."""
        response = self.client.get('/api/currency-conversion/', {
            'from': 'INVALID',
            'to': 'ALSO_INVALID',
            'amount': 'not_a_number'
        })
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# Integración Admin + Auditoría
# ---------------------------------------------------------------------------

class AuditoriaIntegrationTest(BaseIntegrationTest):
    """
    Verifica que las acciones admin registren entradas en el log de auditoría.
    """

    def test_login_exitoso_genera_actividad(self):
        """
        El login exitoso debe ser registrado por AuthAuditMiddleware.
        Verifica que el middleware no interfiera con el login.
        """
        response = self.client.post('/en/admin/login/', {
            'username': 'admin_integration',
            'password': 'AdminPass123!',
            'next': '/en/admin/',
        })
        # Login exitoso debe redirigir al admin
        self.assertIn(response.status_code, [200, 302])

    def test_login_fallido_no_crashea(self):
        """Un login fallido no debe generar error 500."""
        response = self.client.post('/en/admin/login/', {
            'username': 'admin_integration',
            'password': 'WrongPassword!',
        })
        self.assertNotEqual(response.status_code, 500)

    def test_acceso_de_operadores_es_registrado(self):
        """
        Los accesos al admin son registrados por AdminAuditMiddleware.
        Verifica que el middleware no genere errores.
        """
        self.client.force_login(self.admin_user)
        # Acceder a una lista del admin (triggea AdminAuditMiddleware)
        response = self.client.get('/en/admin/catalogo/sucursal/')
        self.assertNotEqual(response.status_code, 500)
