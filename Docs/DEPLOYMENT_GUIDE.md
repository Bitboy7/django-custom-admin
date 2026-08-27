# Guía de Despliegue - Agrícola de la Costa

## 🚀 Guía de Despliegue en Producción

Esta guía te ayudará a desplegar el sistema de gestión de Agrícola de la Costa en un entorno de producción usando Docker.

## 📋 Prerrequisitos

- Docker Engine 20.10+
- Docker Compose 2.0+
- Al menos 2GB de RAM disponible
- 10GB de espacio en disco

## ⚙️ Configuración Inicial

### 1. Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp .env-example .env

# Editar las variables (¡IMPORTANTE!)
nano .env
```

**Variables críticas para producción:**

```env
# Seguridad
SECRET_KEY=tu_clave_super_secreta_aqui
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com

# Base de datos
DB_NAME=agricola_costa_prod
DB_USER=agricola_user
DB_PASSWORD=contraseña_muy_segura
DB_ROOT_PASSWORD=root_password_seguro

# SSL (si usas HTTPS)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Cloudflare R2 (archivos subidos)
R2_ACCOUNT_ID=tu_account_id_de_cloudflare
R2_ACCESS_KEY_ID=tu_access_key_de_r2
R2_SECRET_ACCESS_KEY=tu_secret_key_de_r2
R2_BUCKET_NAME=agricola-media
R2_SIGNED_URL_EXPIRE=3600
```

El token de R2 debe tener permisos de lectura y escritura sobre el bucket. Los
PDF, XML, comprobantes e imágenes se almacenan como objetos privados; Django
genera URLs firmadas temporales. Para un endpoint jurisdiccional de R2, define
`R2_ENDPOINT_URL` y este reemplazará al endpoint construido con `R2_ACCOUNT_ID`.

### 2. Configurar Dominio y DNS

Asegúrate de que tu dominio apunte a la IP del servidor:

```
A    tu-dominio.com      → IP_DEL_SERVIDOR
A    www.tu-dominio.com  → IP_DEL_SERVIDOR
```

## 🏭 Despliegue en Producción

### Opción 1: Usando PowerShell (Windows)

```powershell
# Instalación completa
.\deploy.ps1 -Action install

# Comandos individuales
.\deploy.ps1 -Action build
.\deploy.ps1 -Action up
.\deploy.ps1 -Action logs
```

### Opción 2: Usando Make (Linux/Mac)

```bash
# Instalación completa
make install

# Comandos individuales
make build
make up
make logs
```

### Opción 3: Docker Compose Directo

```bash
# 1. Construir imágenes
docker-compose build

# 2. Iniciar servicios
docker-compose up -d

# 3. Verificar estado
docker-compose ps

# 4. Ver logs
docker-compose logs -f
```

## 🔧 Post-Instalación

### Verificar Servicios

```bash
# Estado de contenedores
docker-compose ps

# Logs del sistema
docker-compose logs web

# Healthcheck
curl -f http://localhost:8000/admin/
```

### Configuración Inicial

```bash
# Acceder al contenedor
docker-compose exec web bash

# Crear superusuario adicional
python manage.py createsuperuser

# Verificar configuración
python manage.py check --deploy
```

## 🌐 Configuración con Nginx (Recomendado)

### Iniciar con Nginx

```bash
# Usar el perfil con nginx
docker-compose --profile with-nginx up -d
```

### Configurar SSL con Let's Encrypt

```bash
# Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com

# Actualizar variables de entorno
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 📊 Monitoreo y Mantenimiento

### Logs del Sistema

```bash
# Logs en tiempo real
docker-compose logs -f

# Logs específicos
docker-compose logs web
docker-compose logs db
docker-compose logs nginx
```

### Backups Automáticos

```bash
# Backup manual
make backup

# Configurar backup automático (crontab)
0 2 * * * cd /path/to/project && make backup
```

### Actualizaciones

```bash
# 1. Backup antes de actualizar
make backup

# 2. Detener servicios
docker-compose down

# 3. Actualizar código
git pull origin main

# 4. Reconstruir y reiniciar
docker-compose build
docker-compose up -d

# 5. Aplicar migraciones
docker-compose exec web python manage.py migrate
```

## 🔒 Seguridad en Producción

### Firewall

```bash
# Permitir solo puertos necesarios
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### Monitoreo de Seguridad

- Revisar logs regularmente
- Mantener Docker actualizado
- Usar contraseñas fuertes
- Configurar fail2ban
- Implementar monitoreo de recursos

## 🚨 Solución de Problemas

### Contenedor web no inicia

```bash
# Ver logs detallados
docker-compose logs web

# Verificar configuración
docker-compose config

# Reconstruir imagen
docker-compose build --no-cache web
```

### Base de datos no conecta

```bash
# Verificar estado de MySQL
docker-compose logs db

# Probar conexión manual
docker-compose exec db mysql -u root -p

# Verificar variables de entorno
docker-compose exec web env | grep DB_
```

### Archivos estáticos no cargan

```bash
# Recopilar archivos estáticos
docker-compose exec web python manage.py collectstatic --noinput

# Verificar permisos
docker-compose exec web ls -la /app/static/
```

### Problemas de memoria

```bash
# Verificar uso de recursos
docker stats

# Ajustar workers de Gunicorn en entrypoint.sh
--workers 2  # Reducir si hay poca RAM
```

## 📈 Escalabilidad

### Múltiples Workers

Editar `entrypoint.sh`:

```bash
# Calcular workers: (2 x CPU cores) + 1
--workers 5
```

### Load Balancer

Para múltiples instancias, usar:

```yaml
# docker-compose.scale.yml
services:
  web:
    deploy:
      replicas: 3
```

### Base de Datos Externa

Para producción a gran escala:

```env
DB_HOST=tu-mysql-servidor.com
DB_PORT=3306
```

## 🎯 Checklist de Producción

- [ ] Variables de entorno configuradas
- [ ] SECRET_KEY único y seguro
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS configurado
- [ ] Base de datos con contraseñas seguras
- [ ] SSL configurado (si aplica)
- [ ] Backup configurado
- [ ] Monitoreo implementado
- [ ] Firewall configurado
- [ ] Logs rotando correctamente
- [ ] Healthchecks funcionando

## 📞 Soporte

Para problemas específicos:

1. Revisar logs: `docker-compose logs`
2. Verificar configuración: `docker-compose config`
3. Consultar documentación en `/Docs`
4. Contactar al equipo de desarrollo
