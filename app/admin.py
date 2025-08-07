from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html

from django.contrib.auth.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.contrib.admin import ModelAdmin
from .permissions import RoleManager, can_manage_users


class RoleFilter(SimpleListFilter):
    """Filtro para usuarios por rol"""
    title = 'Rol'
    parameter_name = 'role'

    def lookups(self, request, model_admin):
        return [(role, role) for role in RoleManager.ROLES.keys()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(groups__name=self.value())
        return queryset


# Desregistrar los modelos User y Group por defecto
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Formularios cargados desde `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    
    # Configuración de la lista
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'last_login')
    list_filter = ('is_active', 'is_staff', 'is_superuser', RoleFilter, 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Fieldsets mejorados
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups'),
            'description': 'Asigna el usuario a un grupo para darle un rol específico'
        }),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'groups'),
        }),
    )
    
    def get_role(self, obj):
        """Muestra el rol del usuario"""
        role = RoleManager.get_user_role(obj)
        if role:
            color_map = {
                'Administrador': '#dc3545',  # Rojo
                'Gerente': '#fd7e14',       # Naranja
                'Contador': '#198754',      # Verde
                'Vendedor': '#0d6efd',      # Azul
                'Operador': '#6c757d',      # Gris
            }
            color = color_map.get(role, '#6c757d')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, role
            )
        return format_html('<span style="color: #dc3545;">Sin rol</span>')
    
    get_role.short_description = 'Rol'
    get_role.admin_order_field = 'groups__name'
    
    def has_module_permission(self, request):
        """Solo administradores pueden gestionar usuarios"""
        return can_manage_users(request.user)
    
    def has_add_permission(self, request):
        return can_manage_users(request.user)
    
    def has_change_permission(self, request, obj=None):
        return can_manage_users(request.user)
    
    def has_delete_permission(self, request, obj=None):
        return can_manage_users(request.user)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    list_display = ('name', 'get_user_count', 'get_permission_count')
    search_fields = ('name',)
    
    def get_user_count(self, obj):
        """Muestra la cantidad de usuarios en el grupo"""
        count = obj.user_set.count()
        return format_html('<strong>{}</strong> usuarios', count)
    
    get_user_count.short_description = 'Usuarios'
    
    def get_permission_count(self, obj):
        """Muestra la cantidad de permisos del grupo"""
        count = obj.permissions.count()
        return format_html('<strong>{}</strong> permisos', count)
    
    get_permission_count.short_description = 'Permisos'
    
    def has_module_permission(self, request):
        """Solo administradores pueden gestionar grupos"""
        return can_manage_users(request.user)
    
    def has_add_permission(self, request):
        return can_manage_users(request.user)
    
    def has_change_permission(self, request, obj=None):
        return can_manage_users(request.user)
    
    def has_delete_permission(self, request, obj=None):
        return can_manage_users(request.user)
