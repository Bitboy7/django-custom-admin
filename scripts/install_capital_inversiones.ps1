# Script de instalacion del modulo Capital e Inversiones
# Ejecutar desde la raiz del proyecto Django

Write-Host "=== INSTALACION MODULO CAPITAL E INVERSIONES ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar que estamos en el directorio correcto
if (-not (Test-Path "manage.py")) {
    Write-Host "[ERROR] No se encuentra manage.py" -ForegroundColor Red
    Write-Host "Por favor ejecuta este script desde la raiz del proyecto Django" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Directorio correcto verificado" -ForegroundColor Green
Write-Host ""

# 2. Crear migraciones
Write-Host "Paso 1: Creando migraciones..." -ForegroundColor Yellow
python manage.py makemigrations capital_inversiones

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Error al crear migraciones" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Migraciones creadas" -ForegroundColor Green
Write-Host ""

# 3. Aplicar migraciones
Write-Host "Paso 2: Aplicando migraciones..." -ForegroundColor Yellow
python manage.py migrate capital_inversiones

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Error al aplicar migraciones" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Migraciones aplicadas" -ForegroundColor Green
Write-Host ""

# 4. Cargar categorias predeterminadas
Write-Host "Paso 3: Cargando categorias predeterminadas..." -ForegroundColor Yellow
python manage.py cargar_categorias_inversiones

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ADVERTENCIA] Error al cargar categorias" -ForegroundColor Yellow
    Write-Host "Puedes cargarlas manualmente mas tarde con:" -ForegroundColor Yellow
    Write-Host "  python manage.py cargar_categorias_inversiones" -ForegroundColor Cyan
}
else {
    Write-Host "[OK] Categorias cargadas" -ForegroundColor Green
}

Write-Host ""

# 5. Verificar instalacion
Write-Host "Paso 4: Verificando instalacion..." -ForegroundColor Yellow
python manage.py check

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ADVERTENCIA] Hay advertencias o errores en la configuracion" -ForegroundColor Yellow
}
else {
    Write-Host "[OK] Verificacion completa" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== INSTALACION COMPLETADA ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Iniciar el servidor: python manage.py runserver" -ForegroundColor White
Write-Host "  2. Acceder al admin: http://localhost:8000/admin/" -ForegroundColor White
Write-Host "  3. Navegar a: Capital e Inversiones" -ForegroundColor White
Write-Host ""
Write-Host "Documentacion:" -ForegroundColor Yellow
Write-Host "  - Docs/CAPITAL_INVERSIONES_MODULE.md" -ForegroundColor White
Write-Host "  - Docs/CAPITAL_INVERSIONES_ARCHITECTURE_DECISION.md" -ForegroundColor White
Write-Host ""
Write-Host "URLs disponibles:" -ForegroundColor Yellow
Write-Host "  - Dashboard: /capital-inversiones/dashboard/" -ForegroundColor White
Write-Host "  - Reporte Sucursal: /capital-inversiones/reporte/sucursal/" -ForegroundColor White
Write-Host "  - Reporte Categoria: /capital-inversiones/reporte/categoria/" -ForegroundColor White
Write-Host "  - Reporte Rendimientos: /capital-inversiones/reporte/rendimientos/" -ForegroundColor White
Write-Host ""
Write-Host "[OK] Listo para usar!" -ForegroundColor Green
