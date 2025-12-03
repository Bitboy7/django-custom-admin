#!/usr/bin/env python
"""
Script temporal para generar migraciones sin cargar los services que requieren Redis
"""
import os
import sys
import django

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    
    # No cargar los services automáticamente
    os.environ["SKIP_CACHE_SERVICES"] = "1"
    
    django.setup()
    
    from django.core.management import execute_from_command_line
    
    # Generar las migraciones para ventas
    execute_from_command_line(['manage.py', 'makemigrations', 'ventas'])