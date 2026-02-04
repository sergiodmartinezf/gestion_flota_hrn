"""
Comando: python manage.py crear_proveedores_base
Crea los proveedores base Kaufmann y Arriagada si no existen (siempre se tienen).
"""
from django.core.management.base import BaseCommand
from flota.models import Proveedor


class Command(BaseCommand):
    help = 'Crea proveedores base Kaufmann y Arriagada si no existen.'

    def handle(self, *args, **options):
        proveedores_base = [
            {'nombre_fantasia': 'Kaufmann', 'rut_empresa': '76000000-0'},
            {'nombre_fantasia': 'Arriagada', 'rut_empresa': '76000001-9'},
        ]
        for datos in proveedores_base:
            prov, created = Proveedor.objects.get_or_create(
                rut_empresa=datos['rut_empresa'],
                defaults={
                    'nombre_fantasia': datos['nombre_fantasia'],
                    'es_taller': True,
                    'es_arrendador': False,
                    'es_proveedor_base': True,
                    'activo': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Proveedor creado: {prov.nombre_fantasia}'))
            else:
                # Marcar como proveedor base si ya existía
                if not prov.es_proveedor_base:
                    prov.es_proveedor_base = True
                    prov.save()
                    self.stdout.write(self.style.WARNING(f'Proveedor actualizado (es_proveedor_base): {prov.nombre_fantasia}'))
                else:
                    self.stdout.write(f'Proveedor ya existe: {prov.nombre_fantasia}')
