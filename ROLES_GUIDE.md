# Sistema de Gestión de Roles y Permisos

## Descripción General

El sistema implementa un control de acceso basado en roles (RBAC) usando los grupos de Django. Cada usuario puede tener un rol que determina qué partes del sistema puede acceder.

## Roles Disponibles

### 1. **Administrador**

- **Descripción**: Acceso completo al sistema
- **Permisos**: Todos los permisos, incluyendo gestión de usuarios
- **Acceso a**: Toda la aplicación

### 2. **Gerente**

- **Descripción**: Acceso a reportes y gestión de datos
- **Permisos**: Ver todas las secciones, editar gastos y ventas limitadamente
- **Acceso a**: Catálogos, gastos, ventas (vista y edición limitada)

### 3. **Contador**

- **Descripción**: Gestión completa de gastos y finanzas
- **Permisos**: Control total sobre módulo de gastos
- **Acceso a**: Gastos (completo), catálogos (vista), ventas (vista)

### 4. **Vendedor**

- **Descripción**: Gestión de ventas y clientes
- **Permisos**: Control total sobre módulo de ventas
- **Acceso a**: Ventas (completo), catálogos (vista limitada)

### 5. **Operador**

- **Descripción**: Acceso de solo lectura
- **Permisos**: Solo visualización de datos
- **Acceso a**: Vista de catálogos, gastos y ventas (solo lectura)

## Comandos de Gestión

### Configurar Roles Iniciales

```bash
python manage.py setup_roles --create-roles
```

### Asignar Rol a Usuario

```bash
python manage.py setup_roles --assign-role <username> <rol>
```

Ejemplo:

```bash
python manage.py setup_roles --assign-role juan Contador
python manage.py setup_roles --assign-role maria Vendedor
```

### Listar Roles Disponibles

```bash
python manage.py setup_roles --list-roles
```

### Ver Rol de Usuario

```bash
python manage.py setup_roles --show-user-role <username>
```

## Configuración Manual desde el Admin

### Crear Usuario con Rol:

1. Accede al admin de Django como Administrador
2. Ve a "Administración" > "Usuarios"
3. Crea un nuevo usuario o edita uno existente
4. En la sección "Permisos", asigna el usuario al grupo correspondiente
5. Guarda los cambios

### Modificar Permisos de un Rol:

1. Ve a "Administración" > "Grupos"
2. Selecciona el grupo/rol que quieres modificar
3. Agrega o quita permisos según necesites
4. Guarda los cambios

## Seguridad Implementada

### Restricciones de Acceso:

- **Gestión de Usuarios**: Solo Administradores
- **Navegación**: Menús se ocultan según permisos
- **Operaciones**: Validación en modelos admin
- **URLs**: Protección a nivel de vista

### Validaciones:

- Un usuario solo puede tener un rol a la vez
- Los permisos se validan tanto en frontend como backend
- Las operaciones críticas requieren confirmación

## Mejores Prácticas

### Al Crear Usuarios:

1. Siempre asigna un rol apropiado
2. Usa el principio de menor privilegio
3. Revisa periódicamente los accesos

### Mantenimiento:

1. Ejecuta `setup_roles --create-roles` después de cambios
2. Documenta cambios en permisos personalizados
3. Haz backup antes de modificaciones masivas

## Personalización

Para agregar nuevos roles o modificar permisos, edita el archivo `app/permissions.py` en la clase `RoleManager.ROLES`.

### Ejemplo de Nuevo Rol:

```python
'Supervisor': {
    'description': 'Supervisión de operaciones',
    'permissions': [
        'catalogo.view_productor',
        'gastos.view_gastos',
        'ventas.view_ventas',
        # Agrega más permisos según necesites
    ]
}
```

## Troubleshooting

### Problema: Usuario no puede acceder a ninguna sección

**Solución**: Verifica que tiene un rol asignado y que los permisos están configurados

### Problema: Menú no se actualiza después de cambiar rol

**Solución**: El usuario debe cerrar sesión y volver a iniciar

### Problema: Error al ejecutar comandos

**Solución**: Asegúrate de que las migraciones están aplicadas y la base de datos está actualizada

## Comandos Útiles

```bash
# Crear superusuario inicial
python manage.py createsuperuser

# Configurar todos los roles
python manage.py setup_roles --create-roles

# Ver todos los usuarios y sus roles
python manage.py shell -c "
from django.contrib.auth.models import User
from app.permissions import RoleManager
for user in User.objects.all():
    role = RoleManager.get_user_role(user)
    print(f'{user.username}: {role or \"Sin rol\"}')
"
```
