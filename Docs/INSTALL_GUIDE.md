# INSTALACIÓN RÁPIDA - Módulo Capital e Inversiones

## Ejecutar Script de Instalación

```powershell
.\install_capital_inversiones.ps1
```

## O Manualmente:

### 1. Crear Migraciones

```powershell
python manage.py makemigrations capital_inversiones
```

### 2. Aplicar Migraciones

```powershell
python manage.py migrate capital_inversiones
```

### 3. Cargar Categorías Predeterminadas

```powershell
python manage.py cargar_categorias_inversiones
```

### 4. Iniciar Servidor

```powershell
python manage.py runserver
```

### 5. Acceder al Admin

```
http://localhost:8000/admin/capital_inversiones/
```

## Archivos Creados

```
capital_inversiones/
├── __init__.py
├── apps.py
├── models.py (3 modelos)
├── admin.py (completo con Import/Export)
├── views.py (6 vistas)
├── urls.py
├── forms.py
├── tests.py
├── services/
│   ├── __init__.py
│   └── inversiones_service.py
├── migrations/
│   └── __init__.py
└── management/
    └── commands/
        └── cargar_categorias_inversiones.py

Docs/
├── CAPITAL_INVERSIONES_MODULE.md (Guía completa)
├── CAPITAL_INVERSIONES_ARCHITECTURE_DECISION.md (Decisión arquitectónica)
└── CAPITAL_INVERSIONES_SUMMARY.md (Resumen ejecutivo)

install_capital_inversiones.ps1 (Script de instalación)
```

## URLs Disponibles

- Dashboard: `/capital-inversiones/dashboard/`
- Reporte Sucursal: `/capital-inversiones/reporte/sucursal/`
- Reporte Categoría: `/capital-inversiones/reporte/categoria/`
- Reporte Rendimientos: `/capital-inversiones/reporte/rendimientos/`
- API Balance: `/capital-inversiones/api/balance-mensual/`
- API Distribución: `/capital-inversiones/api/distribucion-categorias/`

## Verificación

```powershell
# Verificar que todo está bien
python manage.py check

# Ejecutar tests
python manage.py test capital_inversiones
```

## Listo! ✅

El módulo está completamente funcional y listo para usar.
