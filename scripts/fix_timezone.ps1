# Script para solucionar el error de timezone en MySQL
# Ejecutar como: .\fix_timezone.ps1

Write-Host "=== Solucionando problema de timezone en MySQL ===" -ForegroundColor Cyan

# Leer credenciales de .env
$envPath = ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Variable -Name $key -Value $value -Scope Script
        }
    }
    
    Write-Host "`nConectando a MySQL..." -ForegroundColor Yellow
    Write-Host "Host: $DB_HOST"
    Write-Host "Database: $DB_NAME"
    Write-Host "User: $DB_USER"
    
    # Configurar timezone a UTC en MySQL
    $sqlCommand = "SET GLOBAL time_zone = '+00:00'; SELECT @@global.time_zone, @@session.time_zone;"
    
    Write-Host "`nEjecutando comando SQL para configurar timezone..." -ForegroundColor Yellow
    
    # Intentar ejecutar el comando
    try {
        mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD -e $sqlCommand
        
        Write-Host "`n✅ Timezone configurado exitosamente a UTC (+00:00)" -ForegroundColor Green
        Write-Host "`nReinicia el servidor Django para aplicar los cambios." -ForegroundColor Cyan
        
    } catch {
        Write-Host "`n❌ Error al conectar a MySQL. Verifica:" -ForegroundColor Red
        Write-Host "   1. MySQL está corriendo"
        Write-Host "   2. Las credenciales en .env son correctas"
        Write-Host "   3. El usuario tiene permisos SUPER para SET GLOBAL"
        Write-Host "`nAlternativa: Ejecuta manualmente:" -ForegroundColor Yellow
        Write-Host "   mysql -u root -p"
        Write-Host "   SET GLOBAL time_zone = '+00:00';" -ForegroundColor White
    }
    
} else {
    Write-Host "❌ Archivo .env no encontrado" -ForegroundColor Red
    Write-Host "`nEjecuta manualmente:" -ForegroundColor Yellow
    Write-Host "   mysql -u root -p" -ForegroundColor White
    Write-Host "   SET GLOBAL time_zone = '+00:00';" -ForegroundColor White
}

Write-Host "`n==================================================" -ForegroundColor Cyan
