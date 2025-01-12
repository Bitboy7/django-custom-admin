@echo off
cd C:\Users\dev-y\Documents\django-custom-admin

REM Ejecutar el servidor de desarrollo de Django
start poetry run py .\manage.py runserver

REM Esperar unos segundos para asegurarse de que el servidor se inicie
timeout /t 5 /nobreak

REM Abrir el navegador en la dirección especificada
start http://localhost:8000/admin

REM Mantener la ventana abierta
pause