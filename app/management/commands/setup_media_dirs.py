"""
Comando de Django para crear directorios de media necesarios
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Crea los directorios de media necesarios para la aplicación'

    def handle(self, *args, **options):
        """Crear directorios de media"""
        
        media_dirs = [
            'bancos',
            'catalogo', 
            'clientes',
            'paises',
            'productores',
            'temp_documents',
            'temp_invoices'
        ]
        
        created_count = 0
        error_count = 0
        
        # Crear directorio base de media
        try:
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            self.stdout.write(f'📁 Directorio base de media: {settings.MEDIA_ROOT}')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al crear directorio base: {e}')
            )
            error_count += 1
        
        # Crear subdirectorios
        for dir_name in media_dirs:
            dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
            try:
                os.makedirs(dir_path, exist_ok=True)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Creado: {dir_path}')
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ Error al crear {dir_path}: {e}')
                )
        
        # Resumen
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'📊 Resumen:')
        self.stdout.write(f'   Directorios procesados: {len(media_dirs)}')
        self.stdout.write(f'   Creados exitosamente: {created_count}')
        if error_count > 0:
            self.stdout.write(f'   Errores: {error_count}')
        
        if error_count == 0:
            self.stdout.write(
                self.style.SUCCESS('\n🎉 Todos los directorios de media están listos!')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'\n⚠️ Se completó con {error_count} errores')
            )
