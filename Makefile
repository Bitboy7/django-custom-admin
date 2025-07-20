# Makefile para el proyecto Django - Agrícola de la Costa

.PHONY: help build up down logs shell migrate collectstatic backup restore clean

# Variables
COMPOSE_FILE = docker-compose.yml
COMPOSE_DEV_FILE = docker-compose.dev.yml
SERVICE_NAME = web
DB_SERVICE = db

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Comandos de desarrollo
dev-build: ## Construir contenedores para desarrollo
	docker-compose -f $(COMPOSE_DEV_FILE) build

dev-up: ## Iniciar entorno de desarrollo
	docker-compose -f $(COMPOSE_DEV_FILE) up -d

dev-down: ## Detener entorno de desarrollo
	docker-compose -f $(COMPOSE_DEV_FILE) down

dev-logs: ## Ver logs del entorno de desarrollo
	docker-compose -f $(COMPOSE_DEV_FILE) logs -f

# Comandos de producción
build: ## Construir contenedores para producción
	docker-compose -f $(COMPOSE_FILE) build

up: ## Iniciar entorno de producción
	docker-compose -f $(COMPOSE_FILE) up -d

up-with-nginx: ## Iniciar entorno de producción con Nginx
	docker-compose -f $(COMPOSE_FILE) --profile with-nginx up -d

down: ## Detener entorno de producción
	docker-compose -f $(COMPOSE_FILE) down

logs: ## Ver logs de producción
	docker-compose -f $(COMPOSE_FILE) logs -f

# Comandos de gestión
shell: ## Acceder al shell del contenedor web
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) bash

shell-dev: ## Acceder al shell del contenedor web (desarrollo)
	docker-compose -f $(COMPOSE_DEV_FILE) exec $(SERVICE_NAME) bash

migrate: ## Ejecutar migraciones
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python manage.py migrate

migrate-dev: ## Ejecutar migraciones (desarrollo)
	docker-compose -f $(COMPOSE_DEV_FILE) exec $(SERVICE_NAME) python manage.py migrate

collectstatic: ## Recopilar archivos estáticos
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python manage.py collectstatic --noinput

superuser: ## Crear superusuario
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python manage.py createsuperuser

superuser-dev: ## Crear superusuario (desarrollo)
	docker-compose -f $(COMPOSE_DEV_FILE) exec $(SERVICE_NAME) python manage.py createsuperuser

setup-roles: ## Configurar roles del sistema
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python manage.py setup_roles --create-roles

# Comandos de base de datos
backup: ## Crear backup de la base de datos
	@echo "Creando backup de la base de datos..."
	docker-compose -f $(COMPOSE_FILE) exec $(DB_SERVICE) mysqldump -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup creado: backup_$(shell date +%Y%m%d_%H%M%S).sql"

backup-dev: ## Crear backup de la base de datos (desarrollo)
	@echo "Creando backup de la base de datos de desarrollo..."
	docker-compose -f $(COMPOSE_DEV_FILE) exec $(DB_SERVICE) mysqldump -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} > backup_dev_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restaurar backup de la base de datos (especificar BACKUP_FILE=archivo.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Especifica el archivo: make restore BACKUP_FILE=backup.sql"; exit 1; fi
	docker-compose -f $(COMPOSE_FILE) exec -T $(DB_SERVICE) mysql -u root -p${DB_ROOT_PASSWORD} ${DB_NAME} < $(BACKUP_FILE)

# Comandos de limpieza
clean: ## Limpiar contenedores, volúmenes e imágenes no utilizados
	docker system prune -f
	docker volume prune -f

clean-all: ## Limpiar todo incluyendo imágenes
	docker-compose -f $(COMPOSE_FILE) down -v --rmi all
	docker-compose -f $(COMPOSE_DEV_FILE) down -v --rmi all
	docker system prune -af

# Comandos de monitoreo
status: ## Mostrar estado de los contenedores
	docker-compose -f $(COMPOSE_FILE) ps

status-dev: ## Mostrar estado de los contenedores (desarrollo)
	docker-compose -f $(COMPOSE_DEV_FILE) ps

logs-web: ## Ver logs solo del servicio web
	docker-compose -f $(COMPOSE_FILE) logs -f $(SERVICE_NAME)

logs-db: ## Ver logs solo de la base de datos
	docker-compose -f $(COMPOSE_FILE) logs -f $(DB_SERVICE)

# Comandos de instalación
install: build migrate setup-roles collectstatic ## Instalación completa de producción
	@echo "✅ Instalación de producción completada"

install-dev: dev-build migrate-dev ## Instalación completa de desarrollo
	@echo "✅ Instalación de desarrollo completada"
