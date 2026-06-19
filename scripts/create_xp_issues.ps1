# Script para crear issues de GitHub para cada iteracion XP del modulo ventas
# Uso: powershell -ExecutionPolicy Bypass -File scripts/create_xp_issues.ps1

$repo = "Bitboy7/django-custom-admin"

$iterations = @(
    @{
        Title = "[XP] Iteracion 0 - Foundation (Spike)"
        Labels = "xp,ventas,iteration,foundation"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i0.md"
    },
    @{
        Title = "[XP] Iteracion 1 - Catalogo de Clientes (US-01, US-10)"
        Labels = "xp,ventas,iteration,clientes"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i1.md"
    },
    @{
        Title = "[XP] Iteracion 2 - Ventas de Contado (US-02)"
        Labels = "xp,ventas,iteration,ventas-contado"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i2.md"
    },
    @{
        Title = "[XP] Iteracion 3 - Ventas a Credito (US-03)"
        Labels = "xp,ventas,iteration,credito"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i3.md"
    },
    @{
        Title = "[XP] Iteracion 4 - Pagos con Integridad Transaccional (US-04, US-15)"
        Labels = "xp,ventas,iteration,pagos,transaccional"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i4.md"
    },
    @{
        Title = "[XP] Iteracion 5 - Anticipos y Aplicacion (US-05)"
        Labels = "xp,ventas,iteration,anticipos"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i5.md"
    },
    @{
        Title = "[XP] Iteracion 6 - Reporte de Cobranza Global (US-06)"
        Labels = "xp,ventas,iteration,reportes,cobranza"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i6.md"
    },
    @{
        Title = "[XP] Iteracion 7 - Importacion CFDI (US-07)"
        Labels = "xp,ventas,iteration,cfdi,importacion"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i7.md"
    },
    @{
        Title = "[XP] Iteracion 8 - Estado de Cuenta y Configuracion (US-08, US-12)"
        Labels = "xp,ventas,iteration,estado-cuenta,configuracion"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i8.md"
    },
    @{
        Title = "[XP] Iteracion 9 - Aging y Cache (US-09, US-14)"
        Labels = "xp,ventas,iteration,aging,cache"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i9.md"
    },
    @{
        Title = "[XP] Iteracion 10 - Exportacion y Polish (US-13)"
        Labels = "xp,ventas,iteration,exportacion,polish"
        BodyFile = "C:\Users\dev-y\Documents\django-custom-admin\scripts\issue_i10.md"
    }
)

$results = @()

foreach ($iteration in $iterations) {
    if (-not (Test-Path $iteration.BodyFile)) {
        Write-Host "ERROR: No existe $($iteration.BodyFile)" -ForegroundColor Red
        continue
    }

    $cmd = "gh issue create --repo `"$repo`" --title `"$($iteration.Title)`" --body-file `"$($iteration.BodyFile)`" --label `"$($iteration.Labels)`""
    Write-Host "Ejecutando: $cmd"

    $output = Invoke-Expression $cmd
    $results += $output
    Write-Host "Creado: $output" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "=== RESUMEN DE ISSUES CREADOS ===" -ForegroundColor Cyan
$results | ForEach-Object { Write-Host $_ }
