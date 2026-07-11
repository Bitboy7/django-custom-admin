@echo off
setlocal
cd /d "%~dp0"

REM Inicia Django y mantiene sus logs en una terminal independiente.
start "Django development server" cmd /k "title Django development server && cd /d ""%~dp0"" && call venv\Scripts\activate.bat && echo [Django] Servidor iniciando en http://localhost:8000/ && python manage.py runserver"

REM Worker persistente: procesa los comprobantes OCR pendientes.
start "Django OCR worker" cmd /k "title Django OCR worker && cd /d ""%~dp0"" && call venv\Scripts\activate.bat && echo. && echo [OCR] Worker iniciado. Esperando comprobantes pendientes... && echo [OCR] Mantenga esta ventana abierta mientras usa OCR. && echo. && python -u manage.py process_receipt_ocr --loop --sleep 2"

timeout /t 3 /nobreak >nul
start "" http://localhost:8000/es/admin/

endlocal
