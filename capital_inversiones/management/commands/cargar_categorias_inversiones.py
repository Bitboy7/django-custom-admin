from django.core.management.base import BaseCommand
from capital_inversiones.models import CatInversion


class Command(BaseCommand):
    help = 'Carga categorías de inversión predeterminadas'

    def handle(self, *args, **options):
        categorias = [
            {
                'nombre': 'Capital de Trabajo',
                'descripcion': 'Inversión destinada al capital operativo de la empresa'
            },
            {
                'nombre': 'Activos Fijos',
                'descripcion': 'Inversión en maquinaria, equipo, inmuebles y otros activos fijos'
            },
            {
                'nombre': 'Inversión Financiera',
                'descripcion': 'Inversión en instrumentos financieros, acciones, bonos, fondos de inversión'
            },
            {
                'nombre': 'Inversión Inmobiliaria',
                'descripcion': 'Compra de propiedades, terrenos y bienes raíces'
            },
            {
                'nombre': 'Reinversión de Utilidades',
                'descripcion': 'Utilidades generadas que se reinvierten en el negocio'
            },
            {
                'nombre': 'Aportación de Socios',
                'descripcion': 'Capital aportado por los socios o accionistas'
            },
            {
                'nombre': 'Investigación y Desarrollo',
                'descripcion': 'Inversión en I+D, innovación y desarrollo de nuevos productos'
            },
            {
                'nombre': 'Expansión de Negocio',
                'descripcion': 'Inversión para apertura de nuevas sucursales o expansión del negocio'
            },
            {
                'nombre': 'Tecnología e Infraestructura',
                'descripcion': 'Inversión en sistemas, software, hardware y tecnología'
            },
            {
                'nombre': 'Capacitación y Desarrollo',
                'descripcion': 'Inversión en capacitación del personal y desarrollo organizacional'
            },
        ]
        
        created_count = 0
        existing_count = 0
        
        for cat_data in categorias:
            categoria, created = CatInversion.objects.get_or_create(
                nombre=cat_data['nombre'],
                defaults={'descripcion': cat_data['descripcion']}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Categoría creada: {categoria.nombre}')
                )
            else:
                existing_count += 1
                self.stdout.write(
                    self.style.WARNING(f'○ Categoría ya existe: {categoria.nombre}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Resumen ==='
                f'\nCategorías creadas: {created_count}'
                f'\nCategorías existentes: {existing_count}'
                f'\nTotal: {created_count + existing_count}'
            )
        )
