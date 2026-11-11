from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.test import RequestFactory, TestCase, override_settings
from django.urls import include, path

from .models import LogActividad


def _admin_test_view(request, *args, **kwargs):
    return HttpResponse()


_admin_test_patterns = [
    path('auth/user/', _admin_test_view, name='auth_user_changelist'),
    path(
        'auth/user/<int:object_id>/delete/',
        _admin_test_view,
        name='auth_user_delete',
    ),
]
urlpatterns = [
    path(
        'es/admin/',
        include((_admin_test_patterns, 'admin'), namespace='admin'),
    ),
    path(
        'en/admin/',
        include((_admin_test_patterns, 'admin'), namespace='admin_en'),
    ),
]


class AuditRequestContextTest(TestCase):
    def test_contexto_actor_se_restaura_con_token(self):
        from .request_context import (
            get_audit_actor,
            reset_audit_actor,
            set_audit_actor,
        )

        usuario = User.objects.create_user(username='actor-contexto')

        token = set_audit_actor(usuario)
        self.assertEqual(get_audit_actor(), usuario)

        reset_audit_actor(token)
        self.assertIsNone(get_audit_actor())


class AuditDeletionSignalTest(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(username='actor-borrado')
        self.factory = RequestFactory()

    def _request(self, path):
        request = self.factory.post(path)
        request.user = self.actor
        return request

    def test_ruta_inexistente_no_registra_error_de_auditoria(self):
        from unittest.mock import patch

        from .admin_middleware import AdminAuditMiddleware

        def not_found(request):
            return HttpResponseNotFound()

        with patch('auditoria.admin_middleware.logger.error') as log_error:
            response = AdminAuditMiddleware(not_found)(
                self._request('/es/ruta-que-no-existe/')
            )

        self.assertEqual(response.status_code, 404)
        log_error.assert_not_called()

    def test_eliminacion_localizada_y_masiva_registra_actor(self):
        from .admin_middleware import AdminAuditMiddleware

        usuario_individual = User.objects.create_user(username='borrar-individual')
        usuario_individual_id = usuario_individual.pk

        def eliminar_individual(request):
            usuario_individual.delete()
            return HttpResponseRedirect('/es/admin/auth/user/')

        with override_settings(ROOT_URLCONF='auditoria.tests'):
            AdminAuditMiddleware(eliminar_individual)(self._request(
                f'/es/admin/auth/user/{usuario_individual_id}/delete/'
            ))

        log_individual = LogActividad.objects.get(
            tipo_accion='delete',
            modelo_afectado='auth.User',
            objeto_id=str(usuario_individual_id),
        )
        self.assertEqual(log_individual.usuario_id, self.actor.pk)
        self.assertIn('borrar-individual', log_individual.descripcion)

        usuarios_masivos = [
            User.objects.create_user(username='borrar-masivo-1'),
            User.objects.create_user(username='borrar-masivo-2'),
        ]
        ids = [usuario.pk for usuario in usuarios_masivos]

        def eliminar_masivo(request):
            User.objects.filter(pk__in=ids).delete()
            return HttpResponseRedirect('/en/admin/auth/user/')

        with override_settings(ROOT_URLCONF='auditoria.tests'):
            AdminAuditMiddleware(eliminar_masivo)(
                self._request('/en/admin/auth/user/')
            )

        for usuario, usuario_id in zip(usuarios_masivos, ids):
            with self.subTest(usuario=usuario.username):
                logs = LogActividad.objects.filter(
                    tipo_accion='delete',
                    modelo_afectado='auth.User',
                    objeto_id=str(usuario_id),
                )
                self.assertEqual(logs.count(), 1)
                self.assertEqual(logs.get().usuario_id, self.actor.pk)
