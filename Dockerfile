# Usar una imagen base oficial de Python
FROM python:3.9-slim

# Instalar las dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar los archivos de requerimientos
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn
RUN pip install gunicorn

# Copiar el resto del código de la aplicación
COPY . .

# Compilar los archivos estáticos de Django
RUN python manage.py collectstatic --noinput

# Exponer el puerto que usará la aplicación
EXPOSE 8000

# Comando para correr la aplicación en modo producción con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "django_custom_admin.wsgi:application"]