# Script de despliegue para Windows PowerShell
# Agrícola de la Costa - Sistema de Gestión

param(
    [string]$Action = "help",
    [string]$Environment = "production"
)

function Show-Help {
    Write-Host "=== Script de Despliegue - Agrícola de la Costa ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Uso: .\deploy.ps1 -Action <accion> [-Environment <entorno>]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Acciones disponibles:" -ForegroundColor Cyan
    Write-Host "  build        - Construir contenedores"
    Write-Host "  up           - Iniciar servicios"
    Write-Host "  down         - Detener servicios"
    Write-Host "  logs         - Ver logs"
    Write-Host "  migrate      - Ejecutar migraciones"
    Write-Host "  backup       - Crear backup de BD"
    Write-Host "  shell        - Acceder al contenedor"
    Write-Host "  clean        - Limpiar sistema Docker"
    Write-Host "  install      - Instalación completa"
    Write-Host ""
    Write-Host "Entornos:" -ForegroundColor Cyan
    Write-Host "  production   - Entorno de producción (por defecto)"
    Write-Host "  development  - Entorno de desarrollo"
    Write-Host ""
    Write-Host "Ejemplos:"
    Write-Host "  .\deploy.ps1 -Action install"
    Write-Host "  .\deploy.ps1 -Action up -Environment development"
    Write-Host "  .\deploy.ps1 -Action logs"
}

function Get-ComposeFile {
    if ($Environment -eq "development") {
        return "docker-compose.dev.yml"
    }
    return "docker-compose.yml"
}

function Build-Services {
    $composeFile = Get-ComposeFile
    Write-Host "🔨 Construyendo servicios con $composeFile..." -ForegroundColor Yellow
    docker-compose -f $composeFile build
}

function Start-Services {
    $composeFile = Get-ComposeFile
    Write-Host "🚀 Iniciando servicios con $composeFile..." -ForegroundColor Green
    docker-compose -f $composeFile up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Servicios iniciados correctamente" -ForegroundColor Green
        Write-Host "🌐 Aplicación disponible en: http://localhost:8000/admin" -ForegroundColor Cyan
    }
}

function Stop-Services {
    $composeFile = Get-ComposeFile
    Write-Host "🛑 Deteniendo servicios..." -ForegroundColor Red
    docker-compose -f $composeFile down
}

function Show-Logs {
    $composeFile = Get-ComposeFile
    Write-Host "📋 Mostrando logs..." -ForegroundColor Cyan
    docker-compose -f $composeFile logs -f
}

function Run-Migrations {
    $composeFile = Get-ComposeFile
    Write-Host "🔄 Ejecutando migraciones..." -ForegroundColor Yellow
    docker-compose -f $composeFile exec web python manage.py migrate
}

function Create-Backup {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "backup_$timestamp.sql"
    
    Write-Host "💾 Creando backup: $backupFile..." -ForegroundColor Yellow
    
    # Cargar variables de entorno
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^([^#][^=]+)=(.+)$") {
                $name = $matches[1]
                $value = $matches[2]
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
    
    $dbName = $env:DB_NAME
    $dbRootPassword = $env:DB_ROOT_PASSWORD
    
    docker-compose -f docker-compose.yml exec db mysqldump -u root -p$dbRootPassword $dbName > $backupFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Backup creado: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "❌ Error al crear backup" -ForegroundColor Red
    }
}

function Access-Shell {
    $composeFile = Get-ComposeFile
    Write-Host "🖥️ Accediendo al shell del contenedor..." -ForegroundColor Cyan
    docker-compose -f $composeFile exec web bash
}

function Clean-System {
    Write-Host "🧹 Limpiando sistema Docker..." -ForegroundColor Yellow
    docker system prune -f
    docker volume prune -f
    Write-Host "✅ Limpieza completada" -ForegroundColor Green
}

function Full-Install {
    Write-Host "🔧 Instalación completa del sistema..." -ForegroundColor Green
    
    # Verificar que existe el archivo .env
    if (-not (Test-Path ".env")) {
        Write-Host "⚠️ No se encontró el archivo .env" -ForegroundColor Yellow
        Write-Host "📋 Copiando .env.example a .env..." -ForegroundColor Cyan
        Copy-Item ".env-example" ".env"
        Write-Host "⚠️ IMPORTANTE: Edita el archivo .env con tus configuraciones antes de continuar" -ForegroundColor Red
        Read-Host "Presiona Enter cuando hayas configurado el archivo .env"
    }
    
    Build-Services
    Start-Services
    
    Write-Host "⏳ Esperando a que los servicios estén listos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Run-Migrations
    
    Write-Host "🔐 Configurando roles del sistema..." -ForegroundColor Yellow
    docker-compose -f (Get-ComposeFile) exec web python manage.py setup_roles --create-roles
    
    Write-Host "📦 Recopilando archivos estáticos..." -ForegroundColor Yellow
    docker-compose -f (Get-ComposeFile) exec web python manage.py collectstatic --noinput
    
    Write-Host "✅ Instalación completada" -ForegroundColor Green
    Write-Host "🌐 Aplicación disponible en: http://localhost:8000/admin" -ForegroundColor Cyan
    Write-Host "👤 Usuario por defecto: admin / admin123" -ForegroundColor Yellow
}

# Ejecutar acción
switch ($Action.ToLower()) {
    "help" { Show-Help }
    "build" { Build-Services }
    "up" { Start-Services }
    "down" { Stop-Services }
    "logs" { Show-Logs }
    "migrate" { Run-Migrations }
    "backup" { Create-Backup }
    "shell" { Access-Shell }
    "clean" { Clean-System }
    "install" { Full-Install }
    default { 
        Write-Host "❌ Acción no reconocida: $Action" -ForegroundColor Red
        Show-Help 
    }
}
