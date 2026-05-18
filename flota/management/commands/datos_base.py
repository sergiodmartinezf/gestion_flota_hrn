import os
import csv
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from django.utils.dateparse import parse_date
from flota.models import (
    Usuario, CuentaPresupuestaria, Proveedor, Vehiculo,
)


class Command(BaseCommand):
    help = 'Carga Usuarios, Cuentas Presupuestarias, Proveedores y Vehículos desde CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_dir',
            type=str,
            default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datos')
        )

    def handle(self, *args, **options):
        csv_dir = options['csv_dir']
        self.stdout.write(f'Buscando CSVs en: {csv_dir}')

        csv_files = {
            Usuario: 'usuario.csv',
            CuentaPresupuestaria: 'cuenta_presupuestaria.csv',
            Proveedor: 'proveedor.csv',
            Vehiculo: 'vehiculo.csv',
        }

        # Validar existencia de archivos
        for model, filename in csv_files.items():
            path = os.path.join(csv_dir, filename)
            if not os.path.exists(path):
                self.stdout.write(self.style.ERROR(f'No se encuentra: {path}'))
                return

        # Parche para evitar auto_now_add
        self._patch_auto_now_add(Usuario, 'creado_en')
        self._patch_auto_now_add(Vehiculo, 'creado_en')

        self.stdout.write(self.style.WARNING('Limpiando tablas existentes...'))
        Vehiculo.objects.all().delete()
        Proveedor.objects.all().delete()
        CuentaPresupuestaria.objects.all().delete()
        Usuario.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Tablas limpiadas.'))

        with transaction.atomic():
            self.cargar_usuarios(os.path.join(csv_dir, csv_files[Usuario]))
            self.cargar_cuentas(os.path.join(csv_dir, csv_files[CuentaPresupuestaria]))
            self.cargar_proveedores(os.path.join(csv_dir, csv_files[Proveedor]))
            self.cargar_vehiculos(os.path.join(csv_dir, csv_files[Vehiculo]))

        self._restore_auto_now_add(Usuario, 'creado_en')
        self._restore_auto_now_add(Vehiculo, 'creado_en')

        self.stdout.write(self.style.SUCCESS('Carga CSV completada.'))
        self.reset_sequences()
        self.stdout.write(self.style.SUCCESS('Proceso finalizado.'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_auto_now_add = {}

    def _patch_auto_now_add(self, model, field_name):
        if field_name is None:
            return
        field = model._meta.get_field(field_name)
        self._saved_auto_now_add[(model, field_name)] = field.auto_now_add
        field.auto_now_add = False

    def _restore_auto_now_add(self, model, field_name):
        if field_name is None:
            return
        field = model._meta.get_field(field_name)
        original = self._saved_auto_now_add.get((model, field_name), False)
        field.auto_now_add = original

    def _es_nulo(self, valor):
        if valor is None:
            return True
        s = valor.strip()
        return s == '' or s.upper() == 'NULL'

    def _parse_bool(self, value):
        if self._es_nulo(value):
            return False
        return value.strip().lower() in ('true', '1', 'yes', 't', 'verdadero')

    def _parse_int(self, value):
        if self._es_nulo(value):
            return 0
        try:
            valor_limpio = value.strip().replace('.', '')
            return int(float(valor_limpio))
        except ValueError:
            return 0

    def _parse_date(self, value):
        if self._es_nulo(value):
            return None
        fecha_str = value.strip().split(' ')[0]
        return parse_date(fecha_str) or datetime.strptime(fecha_str, '%Y-%m-%d').date()

    def _parse_datetime(self, value):
        if self._es_nulo(value):
            return None
        try:
            dt = datetime.fromisoformat(value.strip().replace(' ', 'T'))
        except (ValueError, TypeError):
            dt = datetime.combine(self._parse_date(value), time.min)
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

    def cargar_usuarios(self, filepath):
        self.stdout.write('Cargando Usuarios...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Usuario.objects.create(
                    id=self._parse_int(row['id']),
                    password=row['password'],
                    last_login=self._parse_datetime(row['last_login']),
                    rut=row['rut'],
                    nombre=row['nombre'],
                    apellido=row['apellido'],
                    email=row['email'],
                    rol=row['rol'],
                    activo=self._parse_bool(row['activo']),
                    creado_en=self._parse_datetime(row['creado_en']),
                )
        self.stdout.write(self.style.SUCCESS(f'{Usuario.objects.count()} usuarios.'))

    def cargar_cuentas(self, filepath):
        self.stdout.write('Cargando Cuentas Presupuestarias...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                CuentaPresupuestaria.objects.create(
                    id=self._parse_int(row['id']),
                    codigo=row['codigo'],
                    nombre=row['nombre'],
                    descripcion=row['descripcion'],
                )
        self.stdout.write(self.style.SUCCESS(f'{CuentaPresupuestaria.objects.count()} cuentas.'))

    def cargar_proveedores(self, filepath):
        self.stdout.write('Cargando Proveedores...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Proveedor.objects.create(
                    id=self._parse_int(row['id']),
                    rut_empresa=row['rut_empresa'],
                    nombre_fantasia=row['nombre_fantasia'],
                    telefono=row['telefono'],
                    email_contacto=row['email_contacto'],
                    es_taller=self._parse_bool(row['es_taller']),
                    es_arrendador=self._parse_bool(row['es_arrendador']),
                    es_proveedor_base=self._parse_bool(row['es_proveedor_base']),
                    activo=self._parse_bool(row['activo']),
                )
        self.stdout.write(self.style.SUCCESS(f'{Proveedor.objects.count()} proveedores.'))

    def cargar_vehiculos(self, filepath):
        self.stdout.write('Cargando Vehículos...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Vehiculo.objects.create(
                    id=self._parse_int(row['id']),
                    patente=row['patente'],
                    marca=row['marca'],
                    modelo=row['modelo'],
                    vin=row['vin'],
                    nro_motor=row['nro_motor'],
                    anio_adquisicion=self._parse_int(row['anio_adquisicion']),
                    vida_util=self._parse_int(row['vida_util']),
                    kilometraje_actual=self._parse_int(row['kilometraje_actual']),
                    umbral_mantencion=self._parse_int(row['umbral_mantencion']),
                    tipo_carroceria=row['tipo_carroceria'],
                    clase_ambulancia=row['clase_ambulancia'] or None,
                    es_samu=self._parse_bool(row['es_samu']),
                    establecimiento=row['establecimiento'],
                    criticidad=row['criticidad'],
                    es_backup=self._parse_bool(row['es_backup']),
                    estado=row['estado'],
                    tipo_propiedad=row['tipo_propiedad'],
                    creado_en=self._parse_datetime(row['creado_en']),
                )
        self.stdout.write(self.style.SUCCESS(f'{Vehiculo.objects.count()} vehículos.'))

    def reset_sequences(self):
        self.stdout.write(self.style.WARNING('\n Reseteando secuencias...'))
        with connection.cursor() as cursor:
            tablas = ['usuario', 'cuenta_presupuestaria', 'proveedor', 'vehiculo']
            for tabla in tablas:
                cursor.execute(
                    f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                    f"(SELECT COALESCE(MAX(id), 1) FROM {tabla}));"
                )
        self.stdout.write(self.style.SUCCESS('Secuencias actualizadas.'))
        