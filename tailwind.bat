@echo off
REM Tailwind CSS Helper Script para Windows
REM Uso: tailwind.bat [comando]

if "%1"=="" goto help
if "%1"=="install" goto install
if "%1"=="build" goto build
if "%1"=="watch" goto watch
if "%1"=="clean" goto clean
if "%1"=="help" goto help

:help
echo.
echo Tailwind CSS — Helper Script
echo.
echo Uso: tailwind.bat [comando]
echo.
echo Comandos:
echo   install    - Instalar dependencias npm (primera vez)
echo   build      - Compilar CSS (una sola vez)
echo   watch      - Monitorear cambios (desarrollo)
echo   clean      - Limpiar node_modules y output.css
echo   help       - Mostrar esta ayuda
echo.
goto :eof

:install
echo Instalando dependencias npm...
call npm install
echo.
echo ✓ npm install completado
echo.
goto :eof

:build
echo Compilando CSS...
call npm run build:css
echo.
echo ✓ CSS compilado en static/css/output.css
echo.
goto :eof

:watch
echo Monitoreando cambios de CSS...
echo Presiona Ctrl+C para salir.
echo.
call npm run watch:css
goto :eof

:clean
echo Limpiando...
if exist node_modules (
    echo Eliminando node_modules...
    rmdir /s /q node_modules
)
if exist static\css\output.css (
    echo Eliminando output.css...
    del static\css\output.css
)
if exist package-lock.json (
    echo Eliminando package-lock.json...
    del package-lock.json
)
echo.
echo ✓ Limpieza completada
echo.
goto :eof
