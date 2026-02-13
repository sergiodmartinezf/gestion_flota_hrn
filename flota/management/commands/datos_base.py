import os
import csv
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from flota.models import (
    Usuario, CuentaPresupuestaria, Proveedor, Vehiculo,
    Presupuesto, OrdenCompra, Mantenimiento, normalizar_estado_oc
)

class Command(BaseCommand):
    help = 'Carga completa desde archivos CSV (ubicados junto a este script) + correcciones.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_dir',
            type=str,
            help='Directorio donde están los archivos CSV (por defecto: el mismo directorio de este script)',
            default=os.path.dirname(os.path.abspath(__file__))
        )

    def handle(self, *args, **options):
        csv_dir = options['csv_dir']
        self.stdout.write(f'📂 Buscando CSVs en: {csv_dir}')

        csv_files = {
            Usuario: 'data-1770918596484.csv',
            CuentaPresupuestaria: 'data-1770918621301.csv',
            Proveedor: 'data-1770918667631.csv',
            Vehiculo: 'data-1770918639716.csv',
            Presupuesto: 'data-1770918701535.csv',
            OrdenCompra: 'data-1770918685061.csv',
            Mantenimiento: 'data-1770918718887.csv',
        }

        for model, filename in csv_files.items():
            path = os.path.join(csv_dir, filename)
            if not os.path.exists(path):
                self.stdout.write(self.style.ERROR(f'❌ No se encuentra: {path}'))
                self.stdout.write(self.style.WARNING(
                    '   Asegúrate de que los archivos CSV estén en la carpeta: ' + csv_dir
                ))
                return

        # Limpieza opcional
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

        self.stdout.write(self.style.SUCCESS('🎉 Carga CSV completada.'))

        with transaction.atomic():
            self.aplicar_correcciones()

        self.stdout.write(self.style.SUCCESS('🎯 Proceso finalizado exitosamente.'))

    # -----------------------------------------------------------------
    # Métodos de parseo robustos
    # -----------------------------------------------------------------
    def _es_nulo(self, valor):
        """Determina si un valor CSV debe considerarse nulo."""
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
            return int(float(value.strip()))
        except ValueError:
            return 0

    def _parse_date(self, value):
        """Convierte string a date (sin hora)."""
        if self._es_nulo(value):
            return None
        # Tomar solo la parte de la fecha
        fecha_str = value.strip().split(' ')[0]
        return parse_date(fecha_str) or datetime.strptime(fecha_str, '%Y-%m-%d').date()

    def _parse_datetime(self, value):
        """Convierte string a datetime aware, asumiendo hora 00:00:00 si no trae hora."""
        if self._es_nulo(value):
            return None
        # Intentar parsear fecha completa con hora
        try:
            dt = datetime.fromisoformat(value.strip().replace(' ', 'T'))
        except (ValueError, TypeError):
            # Si falla, tomar solo la fecha
            dt = datetime.combine(self._parse_date(value), time.min)
        # Hacer aware con la zona horaria por defecto
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

    # -----------------------------------------------------------------
    # Métodos de carga
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
                vehiculo = None
                vid = row['vehiculo_id']
                if not self._es_nulo(vid):
                    vid_int = self._parse_int(vid)
                    if vid_int > 0:
                        try:
                            vehiculo = Vehiculo.objects.get(id=vid_int)
                        except Vehiculo.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f'   ⚠️ Vehículo ID {vid_int} no encontrado para presupuesto ID {row["id"]}. Se asignará null.'
                            ))
                Presupuesto.objects.create(
                    id=self._parse_int(row['id']),
                    anio=self._parse_int(row['anio']),
                    tipo_presupuesto=row['tipo_presupuesto'],
                    cuenta=CuentaPresupuestaria.objects.get(id=self._parse_int(row['cuenta_id'])),
                    monto_asignado=self._parse_int(row['monto_asignado']),
                    monto_ejecutado=self._parse_int(row['monto_ejecutado']),
                    activo=self._parse_bool(row['activo']),
                    vehiculo=vehiculo,
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

    # -----------------------------------------------------------------
    # Correcciones post-carga (sin cambios funcionales)
    # -----------------------------------------------------------------
    def aplicar_correcciones(self):
        self.stdout.write(self.style.WARNING('\n🔧 Aplicando correcciones post-carga...'))

        try:
            cuenta_correctivo_amb = CuentaPresupuestaria.objects.get(codigo='22.06.002.002')
            cuenta_correctivo_cam = CuentaPresupuestaria.objects.get(codigo='22.06.002.004')
        except CuentaPresupuestaria.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ No existen las cuentas 22.06.002.002 / 004. Abortando.'))
            return

        try:
            camioneta = Vehiculo.objects.get(patente='HL.TS-76')
        except Vehiculo.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ No existe el vehículo HL.TS-76.'))
            return

        ocs_camioneta_sin_cuenta = OrdenCompra.objects.filter(
            vehiculo=camioneta,
            cuenta_presupuestaria__isnull=True
        )
        count_ocs = ocs_camioneta_sin_cuenta.update(
            cuenta_presupuestaria=cuenta_correctivo_cam
        )
        self.stdout.write(f'   ✅ {count_ocs} OC de camioneta actualizadas con cuenta 22.06.002.004.')

        mantos_sin_cuenta = Mantenimiento.objects.filter(
            orden_compra__isnull=False,
            cuenta_presupuestaria__isnull=True
        )
        actualizados = 0
        for m in mantos_sin_cuenta:
            if m.orden_compra.cuenta_presupuestaria:
                m.cuenta_presupuestaria = m.orden_compra.cuenta_presupuestaria
                m.save()
                actualizados += 1
        self.stdout.write(f'   ✅ {actualizados} mantenimientos actualizados con cuenta desde su OC.')

        presupuestos_activos = Presupuesto.objects.filter(activo=True)
        for p in presupuestos_activos:
            qs = Mantenimiento.objects.filter(
                estado='Finalizado',
                orden_compra__fecha_emision__year=p.anio
            )
            if p.cuenta:
                qs = qs.filter(cuenta_presupuestaria=p.cuenta)
            if p.vehiculo:
                qs = qs.filter(vehiculo=p.vehiculo)
            total = qs.aggregate(total=Sum('costo_total_real'))['total'] or 0
            p.monto_ejecutado = total
            p.save()
        self.stdout.write(f'   ✅ {presupuestos_activos.count()} presupuestos recalculados.')

        individuales_correctivo = Presupuesto.objects.filter(
            anio=2025,
            tipo_presupuesto='Operativo',
            vehiculo__isnull=False,
            cuenta__in=[cuenta_correctivo_amb, cuenta_correctivo_cam]
        )
        count_ind = individuales_correctivo.count()
        individuales_correctivo.delete()
        self.stdout.write(f'   ✅ {count_ind} presupuestos individuales de correctivo eliminados.')

        total_amb = Mantenimiento.objects.filter(
            cuenta_presupuestaria=cuenta_correctivo_amb,
            fecha_ingreso__year=2025,
            estado='Finalizado'
        ).aggregate(total=Sum('costo_total_real'))['total'] or 0

        presupuesto_global_amb, created = Presupuesto.objects.get_or_create(
            anio=2025,
            tipo_presupuesto='Operativo',
            cuenta=cuenta_correctivo_amb,
            vehiculo=None,
            defaults={
                'monto_asignado': total_amb,
                'monto_ejecutado': total_amb,
                'activo': True
            }
        )
        if not created:
            presupuesto_global_amb.monto_asignado = total_amb
            presupuesto_global_amb.monto_ejecutado = total_amb
            presupuesto_global_amb.save()
        self.stdout.write(f'   ✅ Presupuesto global 22.06.002.002: ${total_amb:,.0f}')

        total_cam = Mantenimiento.objects.filter(
            cuenta_presupuestaria=cuenta_correctivo_cam,
            fecha_ingreso__year=2025,
            estado='Finalizado'
        ).aggregate(total=Sum('costo_total_real'))['total'] or 0

        presupuesto_global_cam, created = Presupuesto.objects.get_or_create(
            anio=2025,
            tipo_presupuesto='Operativo',
            cuenta=cuenta_correctivo_cam,
            vehiculo=None,
            defaults={
                'monto_asignado': total_cam,
                'monto_ejecutado': total_cam,
                'activo': True
            }
        )
        if not created:
            presupuesto_global_cam.monto_asignado = total_cam
            presupuesto_global_cam.monto_ejecutado = total_cam
            presupuesto_global_cam.save()
        self.stdout.write(f'   ✅ Presupuesto global 22.06.002.004: ${total_cam:,.0f}')
        