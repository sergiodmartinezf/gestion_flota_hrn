from django.core.management.base import BaseCommand
from flota.models import Usuario, Proveedor, Vehiculo


class Command(BaseCommand):
    help = 'Crea datos iniciales para el sistema (proveedores de ejemplo)'

    def handle(self, *args, **options):
        # Crear proveedores de ejemplo
        proveedores = [
            {
                'rut_empresa': '12345678-9',
                'nombre_fantasia': 'Taller Mecánico Osorno',
                'giro': 'Servicios de mantenimiento vehicular',
                'telefono': '+56 9 1234 5678',
                'email_contacto': 'contacto@tallerosorno.cl',
            },
            {
                'rut_empresa': '98765432-1',
                'nombre_fantasia': 'Resmed',
                'giro': 'Arriendo de ambulancias',
                'telefono': '+56 9 8765 4321',
                'email_contacto': 'contacto@resmed.cl',
            },
        ]
        
        for prov_data in proveedores:
            proveedor, created = Proveedor.objects.get_or_create(
                rut_empresa=prov_data['rut_empresa'],
                defaults=prov_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Proveedor creado: {proveedor.nombre_fantasia}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Proveedor ya existe: {proveedor.nombre_fantasia}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Datos iniciales creados exitosamente')
        )

