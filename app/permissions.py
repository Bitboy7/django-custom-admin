"""
Sistema de gestión de roles y permisos personalizado
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class RoleManager:
    """Gestiona roles predefinidos en el sistema"""
    
    ROLES = {
        'Administrador': {
            'description': 'Acceso completo al sistema',
            'permissions': ['*']  # Todos los permisos
        },
        'Gerente': {
            'description': 'Acceso a reportes y gestión de datos',
            'permissions': [
                # Permisos de vista para todas las apps
                'catalogo.view_pais',
                'catalogo.view_estado', 
                'catalogo.view_sucursal',
                'catalogo.view_productor',
                'catalogo.view_producto',
                'gastos.view_banco',
                'gastos.view_cuenta',
                'gastos.view_catgastos',
                'gastos.view_gastos',
                'gastos.view_compra',
                'gastos.view_saldomensual',
                'ventas.view_cliente',
                'ventas.view_agente',
                'ventas.view_ventas',
                'ventas.view_anticipo',
                # Permisos de edición limitados
                'gastos.add_gastos',
                'gastos.change_gastos',
                'ventas.add_ventas',
                'ventas.change_ventas',
                'ventas.add_anticipo',
                'ventas.change_anticipo',
            ]
        },
        'Contador': {
            'description': 'Gestión de gastos y finanzas',
            'permissions': [
                # Gastos completo
                'gastos.view_banco',
                'gastos.add_banco',
                'gastos.change_banco',
                'gastos.view_cuenta',
                'gastos.add_cuenta',
                'gastos.change_cuenta',
                'gastos.view_catgastos',
                'gastos.add_catgastos',
                'gastos.change_catgastos',
                'gastos.view_gastos',
                'gastos.add_gastos',
                'gastos.change_gastos',
                'gastos.delete_gastos',
                'gastos.view_compra',
                'gastos.add_compra',
                'gastos.change_compra',
                'gastos.view_saldomensual',
                'gastos.add_saldomensual',
                'gastos.change_saldomensual',
                # Solo vista en otras areas
                'catalogo.view_productor',
                'catalogo.view_producto',
                'ventas.view_ventas',
            ]
        },
        'Vendedor': {
            'description': 'Gestión de ventas y clientes',
            'permissions': [
                # Ventas completo
                'ventas.view_cliente',
                'ventas.add_cliente',
                'ventas.change_cliente',
                'ventas.view_agente',
                'ventas.add_agente',
                'ventas.change_agente',
                'ventas.view_ventas',
                'ventas.add_ventas',
                'ventas.change_ventas',
                'ventas.view_anticipo',
                'ventas.add_anticipo',
                'ventas.change_anticipo',
                # Solo vista en catálogo
                'catalogo.view_pais',
                'catalogo.view_sucursal',
                'catalogo.view_producto',
            ]
        },
        'Operador': {
            'description': 'Acceso de solo lectura',
            'permissions': [
                # Solo permisos de vista
                'catalogo.view_pais',
                'catalogo.view_estado',
                'catalogo.view_sucursal',
                'catalogo.view_productor',
                'catalogo.view_producto',
                'gastos.view_gastos',
                'gastos.view_compra',
                'ventas.view_ventas',
                'ventas.view_cliente',
            ]
        }
    }
    
    @classmethod
    def create_roles(cls):
        """Crea todos los roles predefinidos"""
        for role_name, role_data in cls.ROLES.items():
            group, created = Group.objects.get_or_create(name=role_name)
            
            if role_data['permissions'] == ['*']:
                # Administrador - todos los permisos
                permissions = Permission.objects.all()
            else:
                # Otros roles - permisos específicos
                permissions = Permission.objects.filter(
                    codename__in=[p.split('.')[-1] for p in role_data['permissions']],
                    content_type__app_label__in=[p.split('.')[0] for p in role_data['permissions']]
                )
            
            group.permissions.set(permissions)
            
            if created:
                print(f"✓ Rol '{role_name}' creado exitosamente")
            else:
                print(f"✓ Rol '{role_name}' actualizado")
    
    @classmethod
    def assign_role(cls, user, role_name):
        """Asigna un rol a un usuario"""
        if role_name not in cls.ROLES:
            raise ValueError(f"Rol '{role_name}' no existe")
        
        group = Group.objects.get(name=role_name)
        user.groups.clear()  # Limpia roles anteriores
        user.groups.add(group)
        return f"Rol '{role_name}' asignado a {user.username}"
    
    @classmethod
    def get_user_role(cls, user):
        """Obtiene el rol actual del usuario"""
        groups = user.groups.all()
        if groups:
            return groups.first().name
        return None


def has_role(user, role_name):
    """Verifica si un usuario tiene un rol específico"""
    return user.groups.filter(name=role_name).exists()


def can_manage_users(user):
    """Verifica si el usuario puede gestionar otros usuarios"""
    return has_role(user, 'Administrador')


def can_view_reports(user):
    """Verifica si el usuario puede ver reportes"""
    allowed_roles = ['Administrador', 'Gerente', 'Contador']
    return any(has_role(user, role) for role in allowed_roles)
