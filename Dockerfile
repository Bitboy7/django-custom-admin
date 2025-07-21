# Usar una imagen base oficial de Python 3.12
FROM python:3.12-slim

# Configurar variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Instalar las dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    libmariadb-dev \
    pkg-config \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no privilegiado
RUN adduser --disabled-password --gecos '' appuser

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar los archivos de requerimientos
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copiar el resto del código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/static/static-only /app/media /app/logs

# Dar permisos al script de entrada (ya copiado con COPY . .)
RUN chmod +x /app/entrypoint.sh

# Cambiar permisos
RUN chown -R appuser:appuser /app

# Cambiar al usuario no privilegiado
USER appuser

# Exponer el puerto que usará la aplicación
EXPOSE 8000

# Comando para correr la aplicación en modo producción con Gunicorn
CMD ["/app/entrypoint.sh"]