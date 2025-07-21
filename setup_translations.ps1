# Script de configuración para desarrollo local con soporte de traducciones
# Uso: .\setup_translations.ps1

Write-Host "🌐 Configurando soporte de traducciones para desarrollo local..." -ForegroundColor Green

# Verificar si estamos en el entorno virtual
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️ No se detectó un entorno virtual activo. Activando venv..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
}

# Crear directorios de locale si no existen
Write-Host "📁 Creando estructura de directorios de traducción..." -ForegroundColor Cyan
$languages = @("es", "en", "fr", "de", "pt")
foreach ($lang in $languages) {
    $dir = "locale\$lang\LC_MESSAGES"
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✓ Creado: $dir" -ForegroundColor Green
    }
}

# Compilar traducciones usando nuestro script Python personalizado
Write-Host "🔧 Compilando traducciones..." -ForegroundColor Cyan
python compile_messages.py

# Habilitar LocaleMiddleware en settings.py
Write-Host "⚙️ Habilitando middleware de localización..." -ForegroundColor Cyan
$settingsPath = "app\settings.py"
$content = Get-Content $settingsPath -Raw
$content = $content -replace '# "django\.middleware\.locale\.LocaleMiddleware",  # Middleware para soporte multiidioma - Temporalmente deshabilitado', '"django.middleware.locale.LocaleMiddleware",  # Middleware para soporte multiidioma'
Set-Content -Path $settingsPath -Value $content

Write-Host "✅ Configuración de traducciones completada!" -ForegroundColor Green
Write-Host "💡 Ahora puedes iniciar el servidor con: python manage.py runserver" -ForegroundColor Yellow
Write-Host "🌍 Las traducciones estarán disponibles en el admin de Django" -ForegroundColor Yellow
