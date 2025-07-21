# Script de inicializacion para desarrollo con gettext
# Este script configura el entorno y compila las traducciones

Write-Host "Configurando entorno para traducciones..." -ForegroundColor Green

# Configurar PATH para gettext
$gettextPath = "C:\Program Files (x86)\GnuWin32\bin"
if (Test-Path $gettextPath) {
    $env:PATH = "$gettextPath;$env:PATH"
    Write-Host "Gettext anadido al PATH" -ForegroundColor Green
} else {
    Write-Host "Gettext no encontrado, usando compilador Python personalizado..." -ForegroundColor Yellow
}

# Verificar entorno virtual
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activando entorno virtual..." -ForegroundColor Cyan
    & ".\venv\Scripts\Activate.ps1"
}

# Compilar traducciones
Write-Host "Compilando traducciones..." -ForegroundColor Cyan
try {
    # Intentar usar gettext nativo primero
    python manage.py compilemessages 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Traducciones compiladas con gettext nativo" -ForegroundColor Green
    } else {
        throw "Error con gettext"
    }
} catch {
    Write-Host "Usando compilador personalizado..." -ForegroundColor Yellow
    python compile_messages.py
}

# Verificar configuracion
Write-Host "Verificando configuracion de Django..." -ForegroundColor Cyan
python manage.py check

if ($LASTEXITCODE -eq 0) {
    Write-Host "Entorno listo!" -ForegroundColor Green
    Write-Host "Para iniciar el servidor: python manage.py runserver" -ForegroundColor Yellow
    Write-Host "Panel admin: http://localhost:8000/admin/" -ForegroundColor Yellow
    Write-Host "Dashboard: http://localhost:8000/" -ForegroundColor Yellow
} else {
    Write-Host "Hay errores de configuracion. Revisa los mensajes anteriores." -ForegroundColor Red
}
