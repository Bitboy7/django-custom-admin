"""
Comando para configurar roles y permisos del sistema
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.permissions import RoleManager


class Command(BaseCommand):
    help = 'Configura los roles y permisos del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-roles',
            action='store_true',
            help='Crea todos los roles predefinidos',
        )
        parser.add_argument(
            '--assign-role',
            nargs=2,
            metavar=('USERNAME', 'ROLE'),
            help='Asigna un rol a un usuario específico',
        )
        parser.add_argument(
            '--list-roles',
            action='store_true',
            help='Lista todos los roles disponibles',
        )
        parser.add_argument(
            '--show-user-role',
            metavar='USERNAME',
            help='Muestra el rol actual de un usuario',
        )

    def handle(self, *args, **options):
        if options['create_roles']:
            self.stdout.write(
                self.style.SUCCESS('Creando roles del sistema...')
            )
            RoleManager.create_roles()
            self.stdout.write(
                self.style.SUCCESS('✓ Roles configurados exitosamente')
            )

        elif options['assign_role']:
            username, role = options['assign_role']
            try:
                user = User.objects.get(username=username)
                message = RoleManager.assign_role(user, role)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {message}')
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Error: Usuario "{username}" no encontrado')
                )
            except ValueError as e:
                self.stdout.write(
                    self.style.ERROR(f'Error: {e}')
                )

        elif options['list_roles']:
            self.stdout.write(
                self.style.SUCCESS('Roles disponibles en el sistema:')
            )
            for role_name, role_data in RoleManager.ROLES.items():
                self.stdout.write(f'• {role_name}: {role_data["description"]}')

        elif options['show_user_role']:
            username = options['show_user_role']
            try:
                user = User.objects.get(username=username)
                role = RoleManager.get_user_role(user)
                if role:
                    self.stdout.write(
                        self.style.SUCCESS(f'Usuario "{username}" tiene el rol: {role}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Usuario "{username}" no tiene rol asignado')
                    )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Error: Usuario "{username}" no encontrado')
                )

        else:
            self.stdout.write(
                self.style.WARNING(
                    'Uso: python manage.py setup_roles --help para ver las opciones disponibles'
                )
            )
