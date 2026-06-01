# ========== STAGE 1: Build CSS con Node.js 20 Alpine ==========
FROM node:20-alpine AS node-builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY tailwind.config.js postcss.config.js ./
COPY static/css/ ./static/css/
COPY templates ./templates
COPY app/templates ./app/templates
COPY auditoria/templates ./auditoria/templates 2>/dev/null || true
COPY catalogo/templates ./catalogo/templates 2>/dev/null || true
COPY gastos/templates ./gastos/templates 2>/dev/null || true
COPY ventas/templates ./ventas/templates 2>/dev/null || true
COPY capital_inversiones/templates ./capital_inversiones/templates 2>/dev/null || true
COPY reportes/templates ./reportes/templates 2>/dev/null || true

RUN npm run build:css

# ========== STAGE 2: Python 3.12 + Gunicorn ==========
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

# Copiar CSS compilado desde stage anterior
COPY --from=node-builder /app/static/css/output.css ./static/css/output.css

# Crear directorios necesarios
RUN mkdir -p /app/static/static-only /app/media /app/logs && \
    mkdir -p /app/media/bancos /app/media/catalogo /app/media/clientes /app/media/paises /app/media/productores /app/media/temp_documents /app/media/temp_invoices

# Dar permisos al script de entrada (ya copiado con COPY . .)
RUN chmod +x /app/entrypoint.sh

# Cambiar permisos ANTES de ejecutar collectstatic
RUN chown -R appuser:appuser /app

# Cambiar al usuario no privilegiado ANTES de ejecutar comandos de Django
USER appuser

# Exponer el puerto que usará la aplicación
EXPOSE 8000

# Comando para correr la aplicación en modo producción con Gunicorn
CMD ["/app/entrypoint.sh"]