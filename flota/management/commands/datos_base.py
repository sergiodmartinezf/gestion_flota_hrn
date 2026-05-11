import os
import csv
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from django.utils.dateparse import parse_date
from flota.models import (
    Usuario, CuentaPresupuestaria, Proveedor, Vehiculo,
    Presupuesto, OrdenCompra, Mantenimiento, normalizar_estado_oc,
    CargaCombustible, HojaRuta, Viaje, PacienteTraslado, PacienteViaje
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

        # Diccionario con todos los archivos CSV (los nuevos son opcionales)
        csv_files = {
            Usuario: 'usuario.csv',
            CuentaPresupuestaria: 'cuenta_presupuestaria.csv',
            Proveedor: 'proveedor.csv',
            Vehiculo: 'vehiculo.csv',
            Presupuesto: 'presupuesto.csv',
            OrdenCompra: 'orden_compra.csv',
            Mantenimiento: 'mantenimiento.csv',
            # Nuevos modelos (opcionales)
            CargaCombustible: 'carga_combustible.csv',
            HojaRuta: 'hoja_ruta.csv',
            Viaje: 'viaje.csv',
            PacienteTraslado: 'paciente_traslado.csv',
        }

        # Verificar existencia de archivos obligatorios
        modelos_obligatorios = [Usuario, CuentaPresupuestaria, Proveedor, Vehiculo, Presupuesto, OrdenCompra, Mantenimiento]
        for model in modelos_obligatorios:
            filename = csv_files[model]
            path = os.path.join(csv_dir, filename)
            if not os.path.exists(path):
                self.stdout.write(self.style.ERROR(f'❌ No se encuentra: {path}'))
                self.stdout.write(self.style.WARNING(
                    '   Asegúrate de que los archivos CSV obligatorios estén en la carpeta: ' + csv_dir
                ))
                return

        # -----------------------------------------------------------------
        # Desconectar señales
        # -----------------------------------------------------------------
        self.stdout.write(self.style.WARNING('🔌 Desconectando señales...'))
        pre_save.disconnect(validar_cierre_administrativo_mantenimiento, sender=Mantenimiento)
        post_save.disconnect(actualizar_presupuesto_orden_compra, sender=OrdenCompra)
        post_delete.disconnect(actualizar_presupuesto_orden_compra, sender=OrdenCompra)
        post_delete.disconnect(actualizar_presupuesto_al_borrar_mantenimiento, sender=Mantenimiento)

        # Desactivar auto_now_add en campos que lo tengan
        self._patch_auto_now_add(Usuario, 'creado_en')
        self._patch_auto_now_add(Vehiculo, 'creado_en')
        self._patch_auto_now_add(HojaRuta, 'creado_en')
        self._patch_auto_now_add(Viaje, 'creado_en')
        self._patch_auto_now_add(Viaje, 'actualizado_en')

        # Limpieza completa (orden respetando FK)
        self.stdout.write(self.style.WARNING('🧹 Limpiando tablas existentes...'))
        PacienteTraslado.objects.all().delete()
        Viaje.objects.all().delete()
        HojaRuta.objects.all().delete()
        CargaCombustible.objects.all().delete()
        Mantenimiento.objects.all().delete()
        OrdenCompra.objects.all().delete()
        Presupuesto.objects.all().delete()
        Vehiculo.objects.all().delete()
        Proveedor.objects.all().delete()
        CuentaPresupuestaria.objects.all().delete()
        Usuario.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✅ Tablas limpiadas.'))

        with transaction.atomic():
            # ==================== CARGAS OBLIGATORIAS ====================
            self.cargar_usuarios(os.path.join(csv_dir, csv_files[Usuario]))
            self.cargar_cuentas(os.path.join(csv_dir, csv_files[CuentaPresupuestaria]))
            self.cargar_proveedores(os.path.join(csv_dir, csv_files[Proveedor]))
            self.cargar_vehiculos(os.path.join(csv_dir, csv_files[Vehiculo]))
            self.cargar_presupuestos(os.path.join(csv_dir, csv_files[Presupuesto]))
            self.cargar_ordenes_compra(os.path.join(csv_dir, csv_files[OrdenCompra]))
            self.cargar_mantenimientos(os.path.join(csv_dir, csv_files[Mantenimiento]))

            # ==================== NUEVOS CSV (OPCIONALES) ====================
            # ---------- 1. Carga de Combustible ----------
            carga_path = os.path.join(csv_dir, csv_files[CargaCombustible])
            if os.path.exists(carga_path):
                self.cargar_combustible(carga_path)
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ No se encuentra {carga_path}. Se omite carga de combustible.'))

            # ---------- 2. Hojas de Ruta ----------
            hoja_path = os.path.join(csv_dir, csv_files[HojaRuta])
            if os.path.exists(hoja_path):
                self.cargar_hojas_ruta(hoja_path)
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ No se encuentra {hoja_path}. Se omite carga de hojas de ruta.'))

            # ---------- 3. Viajes ----------
            viaje_path = os.path.join(csv_dir, csv_files[Viaje])
            if os.path.exists(viaje_path):
                self.cargar_viajes(viaje_path)
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ No se encuentra {viaje_path}. Se omite carga de viajes.'))

            # ---------- 4. Pacientes Traslado ----------
            paciente_path = os.path.join(csv_dir, csv_files[PacienteTraslado])
            if os.path.exists(paciente_path):
                self.cargar_pacientes_traslado(paciente_path)
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ No se encuentra {paciente_path}. Se omite carga de pacientes traslado.'))

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
        self._restore_auto_now_add(HojaRuta, 'creado_en')
        self._restore_auto_now_add(Viaje, 'creado_en')
        self._restore_auto_now_add(Viaje, 'actualizado_en')

        self.stdout.write(self.style.SUCCESS('🎉 Carga CSV completada.'))
        self.reset_sequences()
        self.stdout.write(self.style.SUCCESS('🎯 Proceso finalizado exitosamente.'))

    # -----------------------------------------------------------------
    # Métodos auxiliares (parseo, parches)
    # -----------------------------------------------------------------
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

    def _parse_float(self, value):
        if self._es_nulo(value):
            return 0.0
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            return 0.0

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

    def _parse_time(self, value):
        if self._es_nulo(value):
            return None
        try:
            return datetime.strptime(value.strip(), '%H:%M:%S').time()
        except ValueError:
            try:
                return datetime.strptime(value.strip(), '%H:%M').time()
            except ValueError:
                return None

    # -----------------------------------------------------------------
    # Métodos de carga originales (sin cambios)
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

    # ==================== NUEVOS MÉTODOS DE CARGA ====================
    def cargar_combustible(self, filepath):
        self.stdout.write('📁 Cargando Cargas de Combustible...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                CargaCombustible.objects.create(
                    id=self._parse_int(row['id']),
                    fecha=self._parse_date(row['fecha']),
                    litros=self._parse_float(row['litros']),
                    costo_total=self._parse_int(row['costo_total']),
                    kilometraje_al_cargar=self._parse_int(row['kilometraje_al_cargar']),
                    nro_boleta=row.get('nro_boleta', ''),
                    patente_vehiculo=Vehiculo.objects.get(id=self._parse_int(row['patente_vehiculo_id'])),
                    conductor_id=self._parse_int(row['conductor_id']) if row.get('conductor_id') else None,
                    cuenta_presupuestaria_id=self._parse_int(row['cuenta_presupuestaria_id']) if row.get('cuenta_presupuestaria_id') else None,
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {CargaCombustible.objects.count()} cargas de combustible.'))

    def cargar_hojas_ruta(self, filepath):
        self.stdout.write('📁 Cargando Hojas de Ruta...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                HojaRuta.objects.create(
                    id=self._parse_int(row['id']),
                    vehiculo=Vehiculo.objects.get(id=self._parse_int(row['vehiculo_id'])),
                    conductor=Usuario.objects.get(id=self._parse_int(row['conductor_id'])),
                    fecha=self._parse_date(row['fecha']),
                    turno=row['turno'],
                    km_inicio=self._parse_int(row['km_inicio']),
                    km_fin=self._parse_int(row['km_fin']) if row.get('km_fin') else None,
                    medico_derivador=row.get('medico_derivador', ''),
                    tens=row.get('tens', ''),
                    enfermero=row.get('enfermero', '') or None,
                    no_aplica_enfermero=self._parse_bool(row.get('no_aplica_enfermero', 'False')),
                    camillero=row.get('camillero', '') or None,
                    no_aplica_camillero=self._parse_bool(row.get('no_aplica_camillero', 'False')),
                    abierta=self._parse_bool(row.get('abierta', 'True')),
                    creado_en=self._parse_datetime(row.get('creado_en', datetime.now().isoformat())),
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {HojaRuta.objects.count()} hojas de ruta.'))

    def cargar_viajes(self, filepath):
        self.stdout.write('📁 Cargando Viajes...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Viaje.objects.create(
                    id=self._parse_int(row['id']),
                    hoja_ruta=HojaRuta.objects.get(id=self._parse_int(row['hoja_ruta_id'])),
                    hora_salida=self._parse_time(row['hora_salida']),
                    hora_llegada=self._parse_time(row['hora_llegada']) if row.get('hora_llegada') else None,
                    km_salida=self._parse_int(row['km_salida']),
                    km_llegada=self._parse_int(row['km_llegada']) if row.get('km_llegada') else None,
                    hora_salida_hbo=self._parse_time(row['hora_salida_hbo']) if row.get('hora_salida_hbo') else None,
                    hora_llegada_hbo=self._parse_time(row['hora_llegada_hbo']) if row.get('hora_llegada_hbo') else None,
                    observaciones=row.get('observaciones', ''),
                    creado_en=self._parse_datetime(row.get('creado_en', datetime.now().isoformat())),
                    actualizado_en=self._parse_datetime(row.get('actualizado_en', datetime.now().isoformat())),
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {Viaje.objects.count()} viajes.'))

    def cargar_pacientes_traslado(self, filepath):
        self.stdout.write('📁 Cargando Pacientes Traslado...')
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Buscar o crear paciente_viaje (maestro)
                paciente_viaje = None
                if row.get('rut') and row.get('nombre'):
                    pv, _ = PacienteViaje.objects.get_or_create(
                        rut=row['rut'].strip(),
                        defaults={'nombre': row['nombre'], 'prevision': row.get('prevision', '')}
                    )
                    paciente_viaje = pv

                PacienteTraslado.objects.create(
                    id=self._parse_int(row['id']),
                    viaje_id=self._parse_int(row['viaje_id']),
                    paciente_viaje=paciente_viaje,
                    nombre=row['nombre'],
                    rut=row.get('rut', ''),
                    categoria_traslado=row.get('categoria_traslado', 'Administrativo'),
                    detalle_origen_alta=row.get('detalle_origen_alta') or None,
                    sentido=row.get('sentido', 'IDA'),
                    destino_tipo=row.get('destino_tipo', 'HBO'),
                    direccion_especifica=row.get('direccion_especifica', ''),
                    prevision=row.get('prevision', ''),
                )
        self.stdout.write(self.style.SUCCESS(f'   ✅ {PacienteTraslado.objects.count()} pacientes traslado.'))

    # -----------------------------------------------------------------
    # Reseteo de secuencias (PostgreSQL)
    # -----------------------------------------------------------------
    def reset_sequences(self):
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
                'carga_combustible',
                'hoja_ruta',
                'viaje',
                'paciente_traslado',
            ]
            for tabla in tablas:
                cursor.execute(
                    f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                    f"(SELECT COALESCE(MAX(id), 1) FROM {tabla}));"
                )
        self.stdout.write(self.style.SUCCESS('   ✅ Secuencias actualizadas.'))
        