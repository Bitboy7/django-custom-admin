"""
Suite de Pruebas de Seguridad — django-custom-admin
====================================================
Cubre las categorías OWASP Top 10 más relevantes para esta aplicación:

  A01 — Control de Acceso Deficiente
  A02 — Fallas Criptográficas (validación en upload)
  A04 — Diseño Inseguro (CSRF, formularios)
  A05 — Configuración de Seguridad Deficiente (headers, cookies)
  A07 — Fallas de Autenticación e Identificación (RBAC)
  A08 — Fallos de Integridad de Software (upload de archivos)

Ejecución:
    python manage.py test app.tests.test_security --verbosity=2
"""
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import translation


# ---------------------------------------------------------------------------
# Clase base con configuración de idioma para i18n_patterns
# ---------------------------------------------------------------------------

class BaseSecurityTest(TestCase):
    """Configura la traducción a inglés para resolver URLs con i18n_patterns."""

    def setUp(self):
        translation.activate('en')

    def tearDown(self):
        translation.deactivate()


# ---------------------------------------------------------------------------
# A01 — Control de Acceso: Autenticación requerida en endpoints protegidos
# ---------------------------------------------------------------------------

class AuthEnforcementTests(BaseSecurityTest):
    """
    Verifica que todos los endpoints protegidos redirijan a login
    cuando el usuario no está autenticado.

    Hallazgos relacionados: C-01 (ventas sin @login_required).
    """

    def _assert_requires_login(self, url, method='get', data=None):
        """Helper: la URL debe retornar 302 para usuarios no autenticados."""
        fn = getattr(self.client, method)
        kwargs = {'data': data} if data else {}
        response = fn(url, **kwargs)
        self.assertEqual(
            response.status_code, 302,
            f"[SEGURIDAD] {url} retornó {response.status_code} sin autenticación. "
            f"Debe retornar 302 → login."
        )

    # --- App core ---

    def test_balances_requiere_login(self):
        self._assert_requires_login('/en/balances/')

    def test_manual_requiere_login(self):
        self._assert_requires_login('/en/manual/')

    def test_export_full_report_requiere_admin(self):
        self._assert_requires_login('/en/export-full-report/', method='post')

    # --- Gastos ---

    def test_gastos_compras_requiere_login(self):
        self._assert_requires_login('/en/compras/')

    def test_gastos_ingresar_factura_requiere_login(self):
        self._assert_requires_login('/en/ingresar-factura/')

    def test_gastos_guardar_factura_requiere_login(self):
        self._assert_requires_login('/en/guardar-gasto-factura/', method='post')

    def test_gastos_guardar_estado_cuenta_requiere_login(self):
        self._assert_requires_login('/en/guardar-gastos-estado-cuenta/', method='post')

    # --- Capital Inversiones ---

    def test_capital_dashboard_requiere_login(self):
        self._assert_requires_login('/en/capital-inversiones/dashboard/')

    def test_capital_reporte_sucursal_requiere_login(self):
        self._assert_requires_login('/en/capital-inversiones/reporte/sucursal/')

    def test_capital_reporte_categoria_requiere_login(self):
        self._assert_requires_login('/en/capital-inversiones/reporte/categoria/')

    def test_capital_reporte_rendimientos_requiere_login(self):
        self._assert_requires_login('/en/capital-inversiones/reporte/rendimientos/')

    def test_capital_api_balance_mensual_requiere_login(self):
        self._assert_requires_login('/en/capital-inversiones/api/balance-mensual/')

    def test_capital_api_distribucion_requiere_login(self):
        self._assert_requires_login('/en/capital-inversiones/api/distribucion-categorias/')

    # --- Admin ---

    def test_admin_requiere_autenticacion(self):
        response = self.client.get('/en/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.get('Location', '').lower())

    def test_admin_password_change_requiere_login(self):
        response = self.client.get('/en/admin/password_change/')
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# A01 — Línea base: Módulo ventas actualmente sin @login_required
# (HALLAZGO CRÍTICO C-01 del informe de seguridad)
# ---------------------------------------------------------------------------

class VentasAuthBaselineTests(BaseSecurityTest):
    """
    Documenta el estado actual de las vistas de ventas que no tienen
    @login_required. Estos tests registran el hallazgo C-01.

    NOTA: Cuando se corrija el hallazgo C-01 (agregar @login_required),
    estos tests DEBEN actualizarse para verificar que retornan 302 → login.
    """

    def setUp(self):
        super().setUp()
        # No re-lanzar excepciones del servidor; queremos ver el código HTTP real
        self.client.raise_request_exception = False

    def test_ventas_anticipos_lista_sin_login(self):
        """
        HALLAZGO C-01: lista_anticipos es accesible sin autenticación.
        Estado actual: retorna 200. Estado esperado tras corrección: 302.
        """
        response = self.client.get('/en/ventas/anticipos/')
        self.assertNotIn(
            response.status_code, [401, 403],
            "HALLAZGO C-01: lista_anticipos no requiere autenticación."
        )
        # Cuando se corrija, cambiar a: self.assertEqual(response.status_code, 302)

    def test_ventas_balances_sin_login(self):
        """
        HALLAZGO C-01: ventas_balances es accesible sin autenticación.
        """
        response = self.client.get('/en/ventas/balances/')
        self.assertNotIn(response.status_code, [401, 403])

    def test_ventas_reporte_cobranza_sin_login(self):
        """
        HALLAZGO C-01: reporte_cobranza_global es accesible sin autenticación.
        """
        response = self.client.get('/en/ventas/reporte-cobranza/')
        self.assertNotIn(response.status_code, [401, 403])

    def test_ventas_crear_anticipo_sin_login(self):
        """
        HALLAZGO C-01: crear_anticipo (GET) no requiere autenticación.
        """
        response = self.client.get('/en/ventas/anticipos/crear/')
        self.assertNotIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# A01 — Línea base: Módulo catálogo público
# ---------------------------------------------------------------------------

class CatalogoPublicBaselineTests(BaseSecurityTest):
    """
    Documenta que el catálogo es actualmente público.
    Hallazgo M-02 del informe de seguridad.
    """

    def setUp(self):
        super().setUp()
        self.client.raise_request_exception = False

    def test_catalogo_list_es_publico(self):
        """HALLAZGO M-02: /catalogo/ es accesible sin autenticación."""
        response = self.client.get('/en/catalogo/')
        self.assertNotIn(
            response.status_code, [401, 403],
            "Línea base: catálogo actualmente público. Ver hallazgo M-02."
        )


# ---------------------------------------------------------------------------
# A04/A10 — Protección CSRF en endpoints POST
# ---------------------------------------------------------------------------

class CSRFProtectionTests(BaseSecurityTest):
    """
    Verifica que la protección CSRF esté activa en endpoints que modifican datos.
    Usa Client(enforce_csrf_checks=True) para simular un atacante externo.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='csrf_tester',
            password='TestPass123!'
        )

    def setUp(self):
        super().setUp()
        self.csrf_client = Client(enforce_csrf_checks=True)
        self.csrf_client.force_login(self.user)

    def test_csrf_guardar_gasto_factura(self):
        """POST sin token CSRF a guardar-gasto-factura debe retornar 403."""
        response = self.csrf_client.post('/en/guardar-gasto-factura/', {})
        self.assertEqual(response.status_code, 403,
                         "CSRF debe estar activo en guardar-gasto-factura")

    def test_csrf_crear_anticipo(self):
        """POST sin token CSRF a crear anticipo debe retornar 403."""
        response = self.csrf_client.post('/en/ventas/anticipos/crear/', {})
        self.assertEqual(response.status_code, 403,
                         "CSRF debe estar activo en crear_anticipo")

    def test_csrf_guardar_estado_cuenta(self):
        """POST sin token CSRF a guardar-gastos-estado-cuenta retorna 403."""
        response = self.csrf_client.post('/en/guardar-gastos-estado-cuenta/', {})
        self.assertEqual(response.status_code, 403,
                         "CSRF debe estar activo en guardar_gastos_estado_cuenta")

    def test_csrf_export_full_report(self):
        """POST sin token CSRF a export-full-report debe retornar 403."""
        response = self.csrf_client.post('/en/export-full-report/', {})
        self.assertIn(response.status_code, [403, 302],
                      "CSRF debe bloquear la exportación sin token")

    def test_csrf_cookie_presente_en_login(self):
        """La cookie CSRF debe generarse en la página de login del admin."""
        client = Client()
        response = client.get('/en/admin/login/')
        self.assertIn(
            'csrftoken', response.cookies,
            "La cookie csrftoken debe estar presente en la página de login"
        )


# ---------------------------------------------------------------------------
# A07 — Control de acceso basado en roles (RBAC)
# ---------------------------------------------------------------------------

class RBACTests(BaseSecurityTest):
    """
    Verifica que el sistema de roles prevenga acceso no autorizado entre roles.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username='super_rbac',
            password='SuperPass123!'
        )
        # Operador: usuario autenticado sin is_staff
        cls.operador = User.objects.create_user(
            username='operador_rbac',
            password='TestPass123!',
            is_staff=False,
            is_superuser=False
        )
        # Vendedor: is_staff True sin superuser
        cls.vendedor = User.objects.create_user(
            username='vendedor_rbac',
            password='TestPass123!',
            is_staff=True,
            is_superuser=False
        )

    def test_operador_no_accede_a_admin(self):
        """Usuario sin is_staff no puede acceder al dashboard de admin."""
        self.client.force_login(self.operador)
        response = self.client.get('/en/admin/')
        # El admin redirige a login si no es staff
        self.assertIn(response.status_code, [302, 403])
        if response.status_code == 302:
            self.assertIn('login', response.get('Location', '').lower())

    def test_vendedor_no_puede_exportar_reporte_completo(self):
        """Staff sin is_admin no puede exportar el reporte completo."""
        self.client.force_login(self.vendedor)
        response = self.client.post('/en/export-full-report/')
        self.assertIn(
            response.status_code, [302, 403],
            "Exportación de reporte completo debe requerir is_admin"
        )

    def test_superuser_puede_acceder_al_admin(self):
        """El superusuario sí debe acceder al panel de admin."""
        self.client.force_login(self.superuser)
        response = self.client.get('/en/admin/')
        self.assertEqual(response.status_code, 200)

    def test_superuser_puede_acceder_a_capital(self):
        """El superusuario debe acceder al dashboard de capital inversiones."""
        self.client.force_login(self.superuser)
        response = self.client.get('/en/capital-inversiones/dashboard/')
        self.assertIn(response.status_code, [200, 302],
                      "Superusuario debe poder acceder al dashboard de capital")

    def test_operador_puede_acceder_a_endpoints_con_login(self):
        """
        Usuario autenticado (aunque sin permisos específicos) accede a vistas
        que solo requieren @login_required.
        """
        self.client.force_login(self.operador)
        response = self.client.get('/en/balances/')
        # Con @login_required, cualquier usuario autenticado debería pasar
        self.assertNotEqual(
            response.status_code, 302,
            "Usuario autenticado debe poder acceder a vistas con @login_required"
        )


# ---------------------------------------------------------------------------
# A05 — Headers de seguridad HTTP
# ---------------------------------------------------------------------------

class SecurityHeadersTests(BaseSecurityTest):
    """
    Verifica que los headers de seguridad HTTP estén presentes en las respuestas.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            username='admin_headers',
            password='AdminPass123!'
        )

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin_user)

    def test_x_frame_options_en_admin(self):
        """
        X-Frame-Options debe estar presente para prevenir clickjacking.
        Configurado en settings.py: X_FRAME_OPTIONS = 'DENY'.
        """
        response = self.client.get('/en/admin/')
        x_frame = response.get('X-Frame-Options', '')
        self.assertIn(
            x_frame.upper(), ['DENY', 'SAMEORIGIN'],
            f"X-Frame-Options ausente o incorrecto. Valor: '{x_frame}'"
        )

    def test_x_content_type_options_en_admin(self):
        """
        X-Content-Type-Options: nosniff debe estar presente.
        Previene ataques de MIME-sniffing.
        """
        response = self.client.get('/en/admin/')
        nosniff = response.get('X-Content-Type-Options', '')
        self.assertEqual(
            nosniff, 'nosniff',
            f"X-Content-Type-Options: nosniff ausente. Valor actual: '{nosniff}'"
        )

    def test_sin_content_type_incorrecto_en_api(self):
        """La API de conversión de moneda debe retornar application/json."""
        response = self.client.get('/api/currency-conversion/')
        content_type = response.get('Content-Type', '')
        # Si la respuesta es JSON, debe declararlo correctamente
        if response.status_code == 200:
            self.assertIn('json', content_type.lower(),
                          "La API de moneda debe retornar Content-Type: application/json")

    def test_respuesta_no_expone_django_version_header(self):
        """
        La cabecera Server no debe exponer la versión exacta de Django/Python.
        (Información válida solo si hay middleware que la inyecte.)
        """
        response = self.client.get('/en/admin/')
        server_header = response.get('X-Powered-By', '')
        self.assertEqual(server_header, '',
                         "X-Powered-By no debe exponer tecnología del stack")


# ---------------------------------------------------------------------------
# A08 — Validación de archivos en upload
# ---------------------------------------------------------------------------

class FileUploadSecurityTests(BaseSecurityTest):
    """
    Verifica que el endpoint de upload de facturas rechace archivos no válidos.
    Hallazgo relacionado: M-05 del informe de seguridad.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='upload_tester',
            password='TestPass123!'
        )

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    _mock_invoice_result = {
        'proveedor': 'Proveedor Test', 'rfc': 'TEST000000', 'fecha': '2024-01-01',
        'total': '100.00', 'concepto': 'Servicio', 'moneda': 'MXN',
        'tipo_cambio': '1.0', 'iva': '16.00', 'subtotal': '84.00',
        'numero_factura': 'F-001', 'uuid': '', 'metodo_pago': 'PUE',
        'forma_pago': '03', 'uso_cfdi': 'G01', 'error': None,
    }

    def _post_fake_file(self, name, content, content_type):
        fake_file = SimpleUploadedFile(name, content, content_type=content_type)
        mock_result = MagicMock(return_value=self._mock_invoice_result)
        with patch('gastos.views.reconocer_factura_pdf', mock_result):
            return self.client.post(
                '/en/ingresar-factura/',
                {'documento_pdf': fake_file, 'tipo_documento': 'factura'},
                follow=False
            )

    def test_servidor_no_crashea_con_exe(self):
        """
        Un archivo .exe disfrazado no debe generar un error 500.
        El servidor debe rechazarlo con 200 (formulario con error) o 400.
        """
        response = self._post_fake_file('exploit.exe', b'MZ\x90\x00', 'application/octet-stream')
        self.assertNotEqual(
            response.status_code, 500,
            "El servidor no debe crashear con un archivo ejecutable"
        )

    def test_servidor_no_crashea_con_script(self):
        """Un archivo JavaScript no debe crashear el servidor."""
        response = self._post_fake_file('evil.js', b'alert(1)', 'text/javascript')
        self.assertNotEqual(response.status_code, 500)

    def test_servidor_no_crashea_con_archivo_vacio(self):
        """Un archivo PDF vacío (0 bytes) no debe generar error 500."""
        response = self._post_fake_file('empty.pdf', b'', 'application/pdf')
        self.assertNotEqual(response.status_code, 500)

    def test_servidor_no_crashea_con_texto_plano(self):
        """Un archivo .txt no debe generar error 500 en el endpoint de facturas."""
        response = self._post_fake_file('nota.txt', b'Este no es un PDF', 'text/plain')
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# A03 — Inyección: SQL Injection via parámetros GET
# ---------------------------------------------------------------------------

class SQLInjectionTests(BaseSecurityTest):
    """
    Verifica que la aplicación no sea vulnerable a SQL injection via parámetros URL.
    Django ORM parametriza automáticamente las consultas, pero es buena práctica
    confirmar que no crashea ante inputs maliciosos.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='sqli_tester',
            password='TestPass123!'
        )

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    SQL_PAYLOADS = [
        "' OR '1'='1",
        "1; DROP TABLE ventas_ventas; --",
        "' UNION SELECT null,null,null --",
        "1' AND SLEEP(5) --",
    ]

    def test_balances_view_sqlinjection_params(self):
        """Los parámetros GET de /balances/ no deben causar error 500 ante SQL injection."""
        for payload in self.SQL_PAYLOADS:
            with self.subTest(payload=payload):
                response = self.client.get('/en/balances/', {'sucursal': payload})
                self.assertNotEqual(
                    response.status_code, 500,
                    f"Error 500 con payload SQL: {payload!r}"
                )

    def test_capital_dashboard_sqlinjection_params(self):
        """Los parámetros de fecha en /capital-inversiones/dashboard/ son seguros."""
        for payload in self.SQL_PAYLOADS:
            with self.subTest(payload=payload):
                response = self.client.get(
                    '/en/capital-inversiones/dashboard/',
                    {'fecha_inicio': payload, 'fecha_fin': payload}
                )
                self.assertNotEqual(response.status_code, 500,
                                    f"Error 500 con payload SQL en capital: {payload!r}")

    def test_api_currency_conversion_sqlinjection(self):
        """La API de conversión de moneda no debe fallar con payloads SQL."""
        for payload in self.SQL_PAYLOADS:
            with self.subTest(payload=payload):
                response = self.client.get(
                    '/api/currency-conversion/',
                    {'from': payload, 'to': payload, 'amount': payload}
                )
                self.assertNotEqual(response.status_code, 500)
