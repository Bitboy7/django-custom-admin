"""
Pruebas del generador de contraseñas en el cambio de contraseña del admin.
"""
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.utils import translation


class AdminPasswordGeneratorTests(TestCase):
    def setUp(self):
        translation.activate('es')
        self.admin = User.objects.create_superuser(
            username='admin_generator',
            email='admin@example.com',
            password='testpass123',
        )
        self.admin.groups.add(Group.objects.create(name='Administrador'))
        self.target = User.objects.create_user(
            username='usuario_objetivo',
            password='testpass123',
        )
        self.client.force_login(self.admin)
        self.url = f'/es/admin/auth/user/{self.target.pk}/password/'

    def tearDown(self):
        translation.deactivate()

    def test_pagina_de_cambio_de_password_muestra_generador(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('data-password-generator', html)
        self.assertIn('password-generator.js', html)

    def test_generador_usa_criptografia_del_navegador(self):
        static_path = finders.find('js/password-generator.js')
        self.assertIsNotNone(static_path)

        source = Path(static_path).read_text(encoding='utf-8')
        self.assertIn('crypto.getRandomValues', source)
        self.assertNotIn('Math.random', source)
