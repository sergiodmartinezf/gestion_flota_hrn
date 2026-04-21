import os
import csv
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from django.utils.dateparse import parse_date
from flota.models import (
    Usuario, CuentaPresupuestaria, Proveedor, Vehiculo,
    Presupuesto, OrdenCompra, Mantenimiento, normalizar_estado_oc
)
from django.db.models.signals import pre_save, post_save, post_delete
from flota.signals import (
    validar_cierre_administrativo_mantenimiento,
    actualizar_presupuesto_orden_compra,
    actualizar_presupuesto_al_borrar_mantenimiento
)


class Command(BaseCommand):
    help = 'Carga completa desde archivos CSV finales (usuario.csv, cuenta_presupuestaria.csv, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_dir',
            type=str,
            help='Directorio donde están los archivos CSV (por defecto: ./datos)',
            default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datos')
        )

    def handle(self, *args, **options):
        csv_dir = options['csv_dir']
        self.stdout.write(f'📂 Buscando CSVs en: {csv_dir}')

        csv_files = {
            Usuario: 'usuario.csv',
            CuentaPresupuestaria: 'cuenta_presupuestaria.csv',
            Proveedor: 'proveedor.csv',
            Vehiculo: 'vehiculo.csv',
            Presupuesto: 'presupuesto.csv',
            OrdenCompra: 'orden_compra.csv',
            Mantenimiento: 'mantenimiento.csv',
        }

        # Verificar existencia de archivos
        for model, filename in csv_files.items():
            path = os.path.join(csv_dir, filename)
            if not os.path.exists(path):
                self.stdout.write(self.style.ERROR(f'❌ No se encuentra: {path}'))
                self.stdout.write(self.style.WARNING(
                    '   Asegúrate de que los archivos CSV estén en la carpeta: ' + csv_dir
                ))
                return

        # -----------------------------------------------------------------
        # Desconectar todas las señales que modifican datos
        # -----------------------------------------------------------------
        self.stdout.write(self.style.WARNING('🔌 Desconectando señales...'))
        pre_save.disconnect(validar_cierre_administrativo_mantenimiento, sender=Mantenimiento)
        post_save.disconnect(actualizar_presupuesto_orden_compra, sender=OrdenCompra)
        post_delete.disconnect(actualizar_presupuesto_orden_compra, sender=OrdenCompra)
        post_delete.disconnect(actualizar_presupuesto_al_borrar_mantenimiento, sender=Mantenimiento)

        # Desactivar auto_now_add en campos que lo tengan
        self._patch_auto_now_add(Usuario, 'creado_en')
        self._patch_auto_now_add(Vehiculo, 'creado_en')

        # Limpieza completa
        self.stdout.write(self.style.WARNING('🧹 Limpiando tablas existentes...'))
        Mantenimiento.objects.all().delete()
        OrdenCompra.objects.all().delete()
        Presupuesto.objects.all().delete()
        Vehiculo.objects.all().delete()
        Proveedor.objects.all().delete()
        CuentaPresupuestaria.objects.all().delete()
        Usuario.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✅ Tablas limpiadas.'))

        with transaction.atomic():
            self.cargar_usuarios(os.path.join(csv_dir, csv_files[Usuario]))
            self.cargar_cuentas(os.path.join(csv_dir, csv_files[CuentaPresupuestaria]))
            self.cargar_proveedores(os.path.join(csv_dir, csv_files[Proveedor]))
            self.cargar_vehiculos(os.path.join(csv_dir, csv_files[Vehiculo]))
            self.cargar_presupuestos(os.path.join(csv_dir, csv_files[Presupuesto]))
            self.cargar_ordenes_compra(os.path.join(csv_dir, csv_files[OrdenCompra]))
            self.cargar_mantenimientos(os.path.join(csv_dir, csv_files[Mantenimiento]))

        # -----------------------------------------------------------------
        # Reconectar señales y restaurar auto_now_add
        # -----------------------------------------------------------------
        self.stdout.write(self.style.WARNING('🔌 Reconectando señales...'))
        pre_save.connect(validar_cierre_administrativo_mantenimiento, sender=Mantenimiento)
        post_save.connect(actualizar_presupuesto_orden_compra, sender=OrdenCompra)
        post_delete.connect(actualizar_presupuesto_orden_compra, sender=OrdenCompra)
        post_delete.connect(actualizar_presupuesto_al_borrar_mantenimiento, sender=Mantenimiento)

        self._restore_auto_now_add(Usuario, 'creado_en')
        self._restore_auto_now_add(Vehiculo, 'creado_en')

        self.stdout.write(self.style.SUCCESS('🎉 Carga CSV completada.'))
        self.reset_sequences()
        self.stdout.write(self.style.SUCCESS('🎯 Proceso finalizado exitosamente.'))

    # -----------------------------------------------------------------
    # Métodos auxiliares para parchear auto_now_add
    # -----------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_auto_now_add = {}

    def _patch_auto_now_add(self, model, field_name):
        """Desactiva temporalmente auto_now_add de un campo y guarda el valor original."""
        field = model._meta.get_field(field_name)
        self._saved_auto_now_add[(model, field_name)] = field.auto_now_add
        field.auto_now_add = False

    def _restore_auto_now_add(self, model, field_name):
        """Restaura auto_now_add al valor original."""
        field = model._meta.get_field(field_name)
        original = self._saved_auto_now_add.get((model, field_name), False)
        field.auto_now_add = original

    # -----------------------------------------------------------------
    # Métodos de parseo robustos
    # -----------------------------------------------------------------
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

    # -----------------------------------------------------------------
    # Métodos de carga (sin cambios respecto al original)
    # -----------------------------------------------------------------
    def cargar_usuarios(self, filepath):
        self.stdout.write('📁 Cargando Usuarios...')
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
        self.stdout.write(self.style.SUCCESS(f'   ✅ {Usuario.objects.count()} usuarios.'))

    def cargar_cuentas(self, filepath):
        self.stdout.write('📁 Cargando Cuentas Presupuestarias...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                CuentaPresupuestaria.objects.create(
                    id=self._parse_int(row['id']),
                    codigo=row['codigo'],
                    nombre=row['nombre'],
                    descripcion=row['descripcion'],
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {CuentaPresupuestaria.objects.count()} cuentas.'))

    def cargar_proveedores(self, filepath):
        self.stdout.write('📁 Cargando Proveedores...')
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
        self.stdout.write(self.style.SUCCESS(f'   ✅ {Proveedor.objects.count()} proveedores.'))

    def cargar_vehiculos(self, filepath):
        self.stdout.write('📁 Cargando Vehículos...')
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
        self.stdout.write(self.style.SUCCESS(f'   ✅ {Vehiculo.objects.count()} vehículos.'))

    def cargar_presupuestos(self, filepath):
        self.stdout.write('📁 Cargando Presupuestos...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Presupuesto.objects.create(
                    id=self._parse_int(row['id']),
                    anio=self._parse_int(row['anio']),
                    tipo_presupuesto=row['tipo_presupuesto'],
                    cuenta=CuentaPresupuestaria.objects.get(id=self._parse_int(row['cuenta_id'])),
                    monto_asignado=self._parse_int(row['monto_asignado']),
                    monto_ejecutado=self._parse_int(row['monto_ejecutado']),
                    activo=self._parse_bool(row['activo']),
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {Presupuesto.objects.count()} presupuestos.'))

    def cargar_ordenes_compra(self, filepath):
        self.stdout.write('📁 Cargando Órdenes de Compra...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vehiculo = None
                vid = row['vehiculo_id']
                if not self._es_nulo(vid):
                    vid_int = self._parse_int(vid)
                    if vid_int > 0:
                        try:
                            vehiculo = Vehiculo.objects.get(id=vid_int)
                        except Vehiculo.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f'   ⚠️ Vehículo ID {vid_int} no encontrado para OC {row["nro_oc"]}. Se asignará null.'
                            ))

                cuenta = None
                cid = row['cuenta_presupuestaria_id']
                if not self._es_nulo(cid):
                    cuenta = CuentaPresupuestaria.objects.get(id=self._parse_int(cid))

                proveedor = Proveedor.objects.get(id=self._parse_int(row['proveedor_id']))

                presupuesto = None
                pid = row.get('presupuesto_id')
                if not self._es_nulo(pid):
                    pid_int = self._parse_int(pid)
                    if pid_int > 0:
                        presupuesto = Presupuesto.objects.filter(id=pid_int).first()

                OrdenCompra.objects.create(
                    id=self._parse_int(row['id']),
                    nro_oc=row['nro_oc'],
                    descripcion=row['descripcion'],
                    fecha_emision=self._parse_date(row['fecha_emision']),
                    monto_neto=self._parse_int(row['monto_neto']),
                    impuesto=self._parse_int(row['impuesto']),
                    monto_total=self._parse_int(row['monto_total']),
                    id_licitacion=row['id_licitacion'],
                    folio_sigfe=row['folio_sigfe'],
                    estado=normalizar_estado_oc(row['estado']),
                    archivo_adjunto=None,
                    tipo_adquisicion=row['tipo_adquisicion'],
                    cuenta_presupuestaria=cuenta,
                    orden_trabajo_id=None,
                    presupuesto=presupuesto,
                    proveedor=proveedor,
                    vehiculo=vehiculo,
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {OrdenCompra.objects.count()} órdenes de compra.'))

    def cargar_mantenimientos(self, filepath):
        self.stdout.write('📁 Cargando Mantenimientos...')
        # Nota: las señales ya están desconectadas globalmente, no necesitamos desconectar aquí
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vehiculo = Vehiculo.objects.get(id=self._parse_int(row['vehiculo_id']))
                proveedor = Proveedor.objects.get(id=self._parse_int(row['proveedor_id']))
                oc = None
                ocid = row['orden_compra_id']
                if not self._es_nulo(ocid):
                    oc = OrdenCompra.objects.get(id=self._parse_int(ocid))
                cuenta = None
                cid = row['cuenta_presupuestaria_id']
                if not self._es_nulo(cid):
                    cuenta = CuentaPresupuestaria.objects.get(id=self._parse_int(cid))

                Mantenimiento.objects.create(
                    id=self._parse_int(row['id']),
                    tipo_mantencion=row['tipo_mantencion'],
                    fecha_ingreso=self._parse_date(row['fecha_ingreso']),
                    fecha_salida=self._parse_date(row['fecha_salida']),
                    fecha_programada=self._parse_date(row['fecha_programada']),
                    km_al_ingreso=self._parse_int(row['km_al_ingreso']),
                    descripcion_trabajo=row['descripcion_trabajo'],
                    estado=row['estado'],
                    nro_factura=row['nro_factura'] or None,
                    archivo_adjunto=None,
                    orden_compra=oc,
                    costo_estimado=self._parse_int(row['costo_estimado']),
                    costo_mano_obra=self._parse_int(row['costo_mano_obra']),
                    costo_repuestos=self._parse_int(row['costo_repuestos']),
                    costo_total_real=self._parse_int(row['costo_total_real']),
                    vehiculo=vehiculo,
                    orden_trabajo=None,
                    proveedor=proveedor,
                    cuenta_presupuestaria=cuenta,
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {Mantenimiento.objects.count()} mantenimientos.'))

    def reset_sequences(self):
        """Resetea las secuencias de todas las tablas con AutoField (PostgreSQL)."""
        self.stdout.write(self.style.WARNING('\n🔄 Reseteando secuencias...'))
        with connection.cursor() as cursor:
            tablas = [
                'usuario',
                'cuenta_presupuestaria',
                'proveedor',
                'vehiculo',
                'presupuesto',
                'orden_compra',
                'mantenimiento',
            ]
            for tabla in tablas:
                cursor.execute(
                    f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                    f"(SELECT COALESCE(MAX(id), 1) FROM {tabla}));"
                )
        self.stdout.write(self.style.SUCCESS('   ✅ Secuencias actualizadas.'))
        