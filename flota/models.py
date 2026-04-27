from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone


TIPOS_SERVICIO = [
    ('Llamado', 'Llamado'),
    ('Rescate de Paciente', 'Rescate de Paciente'),
    ('A Urgencia HBO', 'A Urgencia HBO'),
    ('Exámenes', 'Exámenes'),
    ('Alta a Domicilio', 'Alta a Domicilio'),
    ('Interconsulta', 'Interconsulta'),
    ('Horas a especialista', 'Horas a especialista'),
    ('Imagen', 'Imagen'),
    ('Administrativo', 'Administrativo'), # Agregado para camionetas
    ('Otro', 'Otro'),
]

TURNOS = [
    ('08-20', 'Turno 08:00 a 20:00'),
    ('20-08', 'Turno 20:00 a 08:00'),
    ('09-20', 'Turno 09:00 a 20:00 (fin de semana/feriado)'),
    ('20-09', 'Turno 20:00 a 09:00 (fin de semana/feriado)'),
    ('08-17', 'Turno 08:00 a 17:00 (Horario Administrativo)'),
]

TIPO_TRASLADO_CATEGORIA = [
    ('PRIMARIO', 'Traslado Primario (Lugar del evento -> Urgencia)'),
    ('SECUNDARIO', 'Traslado Secundario (Urgencia -> Hospital Base/Red)'),
    ('OTROS', 'Otros Traslados (Rescates, Exámenes, Especialista)'),
    ('ALTA', 'Altas'),
    ('Administrativo', 'Administrativo'),
]

# Subcategorías para lógica de negocio
ORIGEN_ALTA = [
    ('URGENCIA', 'Desde Servicio de Urgencia'),
    ('HOSPITALIZADO', 'Desde Hospitalizado'),
    ('HBO', 'Desde Hospital Base Osorno'),
]

DESTINOS_COMUNES = [
    ('HBO', 'Hospital Base Osorno'),
    ('DOMICILIO', 'Domicilio (Ingresar Dirección)'),
    ('CESFAM', 'CESFAM'),
    ('ACHS', 'ACHS/Mutual'),
    ('OTRO', 'Otro (Especificar)'),
]

# Estados de ordenes de compra
def normalizar_estado_oc(estado):
    """
    Normaliza cualquier variante de estado de orden de compra a los estados estándar.
    
    Mapea estados de Mercado Público y variantes a estados internos consistentes.
    """
    if not estado:
        return 'Emitida'
    
    estado = str(estado).strip().upper()
    
    # Mapeo de estados de Mercado Público a estados internos
    mapa_mercadopublico = {
        'RECEPCIÓN CONFORME': 'RECEPCIONADA',
        'RECEPCION CONFORME': 'RECEPCIONADA',
        'RECEPCIONADA PARCIALMENTE': 'RECEPCIONADA',
        'RECEPCION ACEPTADA PARCIALMENTE': 'RECEPCIONADA',
        'RECEPCION CONFORME INCOMPLETA': 'RECEPCIONADA',
        'PENDIENTE DE RECEPCIONAR': 'EMITIDA',
        'ENVIADA A PROVEEDOR': 'EMITIDA',
        'EN PROCESO': 'EMITIDA',
        'CANCELADA': 'ANULADA',
    }
    
    # Mapeo de variantes comunes
    mapa_variantes = {
        'RECEPCIONADA': 'RECEPCIONADA',
        'RECIBIDA': 'RECEPCIONADA',
        'ENTREGADA': 'RECEPCIONADA',
        'FINALIZADA': 'RECEPCIONADA',
        'CONCLUIDA': 'RECEPCIONADA',
        'ACEPTADA': 'ACEPTADA',
        'APROBADA': 'ACEPTADA',
        'VALIDADA': 'ACEPTADA',
        'EMITIDA': 'EMITIDA',
        'CREADA': 'EMITIDA',
        'GENERADA': 'EMITIDA',
        'PAGADA': 'PAGADA',
        'LIQUIDADA': 'PAGADA',
        'FACTURADA': 'PAGADA',
        'ANULADA': 'ANULADA',
        'CANCELADA': 'ANULADA',
        'ELIMINADA': 'ANULADA',
        'RECHAZADA': 'ANULADA',
    }
    
    # Primero buscar en el mapeo de Mercado Público
    if estado in mapa_mercadopublico:
        return mapa_mercadopublico[estado]
    
    # Luego buscar en el mapeo de variantes
    if estado in mapa_variantes:
        return mapa_variantes[estado]
    
    # Si no encuentra coincidencia, intentar coincidencia parcial
    for clave, valor in mapa_mercadopublico.items():
        if clave in estado or estado in clave:
            return valor
    
    for clave, valor in mapa_variantes.items():
        if clave in estado or estado in clave:
            return valor
    
    # Por defecto, devolver Emitida
    return 'EMITIDA'


def normalizar_estado_visual(estado_normalizado):
    """
    Convierte un estado normalizado a su forma legible para mostrar en interfaces.
    """
    estados_visuales = {
        'EMITIDA': 'Emitida',
        'ACEPTADA': 'Aceptada',
        'RECEPCIONADA': 'Recepcionada',
        'PAGADA': 'Pagada',
        'ANULADA': 'Anulada',
    }
    return estados_visuales.get(estado_normalizado, estado_normalizado)


# --- GESTIÓN DE USUARIOS ---

class UsuarioManager(BaseUserManager):
    def create_user(self, rut, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un email')
        if not rut:
            raise ValueError('El usuario debe tener un RUT')
        
        email = self.normalize_email(email)
        user = self.model(rut=rut, email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            # Contraseña por defecto: rut
            user.set_password(rut)
        
        user.save(using=self._db)
        return user

    def create_superuser(self, rut, email, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'Administrador')
        extra_fields.setdefault('activo', True)
        
        if password is None:
            password = rut  # Contraseña por defecto para superusuarios
        
        return self.create_user(rut, email, password, **extra_fields)

class Usuario(AbstractBaseUser):
    ROLES = [
        ('Administrador', 'Administrador'),
        ('Conductor', 'Conductor'),
        ('Visualizador', 'Visualizador'),
    ]
    
    id = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='Visualizador')
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'rut'
    REQUIRED_FIELDS = ['email', 'nombre', 'apellido']
    
    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.rut})"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def has_perm(self, perm, obj=None):
        return self.rol == 'Administrador'
    
    def has_module_perms(self, app_label):
        return True
    
    @property
    def is_staff(self):
        return self.rol == 'Administrador'
    
    @property
    def is_active(self):
        return self.activo


# --- GESTIÓN FINANCIERA Y PROVEEDORES ---

class Proveedor(models.Model):
    id = models.AutoField(primary_key=True)
    rut_empresa = models.CharField(max_length=12, unique=True)
    nombre_fantasia = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email_contacto = models.EmailField(blank=True)
    es_taller = models.BooleanField(default=False, verbose_name="Es Taller Mecánico")
    es_arrendador = models.BooleanField(default=False, verbose_name="Es Arrendador de Vehículos")
    es_proveedor_base = models.BooleanField(default=False, verbose_name="Proveedor base (Kaufmann/Arriagada)")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        db_table = 'proveedor'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
    
    def __str__(self):
        return self.nombre_fantasia


class CuentaPresupuestaria(models.Model):
    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=50, unique=True, help_text="Ej: 22.06.002.001")
    nombre = models.CharField(max_length=200, help_text="Ej: Mantenimiento y Reparación de Vehículos")
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'cuenta_presupuestaria'
        verbose_name = 'Cuenta Presupuestaria (SIGFE)'
        verbose_name_plural = 'Cuentas Presupuestarias'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class OrdenCompra(models.Model):
    id = models.AutoField(primary_key=True)
    nro_oc = models.CharField(max_length=50, unique=True, verbose_name="Nro Orden de Compra")
    descripcion = models.TextField(blank=True, verbose_name="Descripción de la OC")
    fecha_emision = models.DateField()
    
    # Montos planificados (según OC física)
    monto_neto = models.IntegerField(validators=[MinValueValidator(0)])
    impuesto = models.IntegerField(default=0, validators=[MinValueValidator(0)]) # IVA
    monto_total = models.IntegerField(validators=[MinValueValidator(0)])
    
    id_licitacion = models.CharField(max_length=50, blank=True, verbose_name="ID MercadoPúblico")
    folio_sigfe = models.CharField(max_length=50, blank=True, verbose_name="Folio SIGFE")
    estado = models.CharField(max_length=20, default='N/A')
    
    # Archivo físico digitalizado
    archivo_adjunto = models.FileField(upload_to='ordenes_compra/', null=True, blank=True, verbose_name="PDF Orden de Compra")
    
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes_compra')
    vehiculo = models.ForeignKey('Vehiculo', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vehículo Asociado", help_text="Vehículo identificado en la importación")
    cuenta_presupuestaria = models.ForeignKey(CuentaPresupuestaria, on_delete=models.PROTECT, related_name='ordenes_compra', null=True, blank=True)
    presupuesto = models.ForeignKey('Presupuesto', on_delete=models.PROTECT, related_name='ordenes_compra', null=True, blank=True, verbose_name="Presupuesto asociado")
    orden_trabajo = models.ForeignKey('OrdenTrabajo', on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_compra', verbose_name="Orden de Trabajo asociada", help_text="Orden de trabajo que originó esta orden de compra")
    
    TIPO_ADQUISICION = [
        ('Convenio Marco', 'Convenio Marco'),
        ('Licitación Pública', 'Licitación Pública'),
        ('Trato Directo', 'Trato Directo'),
        ('Compra Ágil', 'Compra Ágil'),
    ]
    tipo_adquisicion = models.CharField(max_length=30, choices=TIPO_ADQUISICION, default='Convenio Marco')

    class Meta:
        db_table = 'orden_compra'
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Ordenes de Compra'
        indexes = [
            models.Index(fields=['folio_sigfe']),
            models.Index(fields=['estado', 'fecha_emision']),
            models.Index(fields=['proveedor', 'fecha_emision']),
        ]
    
    def save(self, *args, **kwargs):
        """
        Al guardar una OC, validar y gestionar presupuesto si corresponde.
        NOTA: El consumo real del presupuesto se hace a través de signals
        que recalculan basándose en las OCs activas (no anuladas).
        """
        is_new = self.pk is None

        # Si es nueva OC o se cambió el monto/estado, validar presupuesto
        if self.cuenta_presupuestaria and self.monto_total > 0 and self.estado != 'Anulada':
            anio = self.fecha_emision.year

            # Buscar presupuesto por cuenta y año (ya no por vehículo)
            presupuesto = Presupuesto.objects.filter(
                cuenta=self.cuenta_presupuestaria,
                anio=anio,
                activo=True
            ).first()

            # Si es nueva OC, validar presupuesto disponible
            if is_new and presupuesto:
                if not presupuesto.tiene_saldo_suficiente(self.monto_total):
                    raise ValueError(
                        f"Presupuesto insuficiente para generar OC. "
                        f"Disponible: ${presupuesto.disponible:.0f}, "
                        f"Requerido: ${self.monto_total:.0f}"
                    )
            # Si se está modificando y cambió el monto, validar disponibilidad
            elif not is_new and presupuesto:
                try:
                    oc_anterior = OrdenCompra.objects.get(pk=self.pk)
                    monto_anterior = oc_anterior.monto_total if oc_anterior.estado != 'Anulada' else 0
                    diferencia = self.monto_total - monto_anterior

                    if diferencia > 0 and self.estado != 'Anulada':
                        if not presupuesto.tiene_saldo_suficiente(diferencia):
                            raise ValueError(
                                f"Presupuesto insuficiente para aumentar OC. "
                                f"Disponible: ${presupuesto.disponible:.0f}, "
                                f"Incremento requerido: ${diferencia:.0f}"
                            )
                except OrdenCompra.DoesNotExist:
                    pass

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"OC {self.nro_oc} - {self.proveedor.nombre_fantasia}"

    def clean(self):
        if self.cuenta_presupuestaria and self.presupuesto:
            if self.presupuesto.cuenta != self.cuenta_presupuestaria:
                raise ValidationError('La cuenta presupuestaria de la OC debe coincidir con la cuenta del presupuesto')


# --- GESTIÓN DE FLOTA ---

class Vehiculo(models.Model):
    ESTADOS = [
        ('Disponible', 'Disponible'),
        ('En uso', 'En uso'),
        ('En mantenimiento', 'En mantenimiento'),
        ('Fuera de servicio', 'Fuera de servicio'),
        ('Baja', 'Dado de Baja'),
    ]
    
    TIPOS_PROPIEDAD = [
        ('Propio', 'Propio'),
        ('Arrendado', 'Arrendado (Reemplazo)'),
    ]
    
    TIPOS_CARROCERIA = [
        ('Ambulancia', 'Ambulancia'),
        ('Sedán', 'Sedán'),
        ('Station Vagon', 'Station Vagon'),
        ('Camioneta', 'Camioneta'),
        ('Minibús', 'Minibús'),
        ('Furgón', 'Furgón'),
        ('Camión', 'Camión'),
        ('Carro de Arrastre', 'Carro de Arrastre'),
    ]
    
    CRITICIDAD = [
        ('Crítico', 'Crítico'),
        ('No crítico', 'No crítico'),
    ]
    
    id = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    vin = models.CharField(max_length=17, blank=True)
    nro_motor = models.CharField(max_length=50, blank=True)
    anio_adquisicion = models.IntegerField()
    
    vida_util = models.IntegerField(default=10, help_text="Años de vida útil estimada")
    kilometraje_actual = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Mantenimiento
    umbral_mantencion = models.IntegerField(default=10000, help_text="Kms entre mantenciones preventivas")
    
    # Clasificación
    tipo_carroceria = models.CharField(max_length=20, choices=TIPOS_CARROCERIA)
    CLASES_AMBULANCIA = [
        ('URBANA (4X2)', 'URBANA (4X2)'),
        ('TODO TERRENO (4X4)', 'TODO TERRENO (4X4)'),
        ('MARÍTIMO (LANCHA)', 'MARÍTIMO (LANCHA)'),
    ]
    
    clase_ambulancia = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        choices=CLASES_AMBULANCIA,
        verbose_name="Clase Ambulancia"
    )
    es_samu = models.BooleanField(default=False, verbose_name="Pertenece a SAMU")
    establecimiento = models.CharField(max_length=200, default='Hospital Río Negro')
    criticidad = models.CharField(max_length=20, choices=CRITICIDAD, default='No crítico')
    es_backup = models.BooleanField(
        default=False, 
        verbose_name="¿Es vehículo de backup?"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Disponible')
    tipo_propiedad = models.CharField(max_length=30, choices=TIPOS_PROPIEDAD, default='Propio')
    
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vehiculo'
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
    
    def __str__(self):
        return f"{self.patente} - {self.marca} {self.modelo}"

    @property
    def kilometraje_para_mantencion(self):
        """Calcula cuántos kilómetros faltan para el próximo mantenimiento"""
        if self.umbral_mantencion > 0:
            resto = self.kilometraje_actual % self.umbral_mantencion
            return max(0, self.umbral_mantencion - resto)
        return 0

    @classmethod
    def objetos_operativos(cls):
        from django.db.models import OuterRef, Subquery, F, Value, IntegerField, Case, When

        last_maint = Mantenimiento.objects.filter(
            vehiculo=OuterRef('pk'),
            tipo_mantencion='Preventivo',
            estado='Finalizado'
        ).order_by('-fecha_salida').values('km_al_ingreso')[:1]

        qs = cls.objects.filter(estado__in=['Disponible', 'En uso']).annotate(
            ultimo_km=Subquery(last_maint, output_field=IntegerField())
        ).annotate(
            recorrido=Case(
                When(ultimo_km__isnull=True, then=F('kilometraje_actual')),  # ← corregido
                default=F('kilometraje_actual') - F('ultimo_km'),            # ← corregido
                output_field=IntegerField()
            )
        ).filter(recorrido__lt=12000)
        return qs

    def save(self, *args, **kwargs):
        # Guardar primero para tener el ID
        super().save(*args, **kwargs)

        # Obtener el último mantenimiento preventivo finalizado
        ultimo_mant = self.mantenimientos.filter(
            tipo_mantencion='Preventivo',
            estado='Finalizado'
        ).order_by('-fecha_salida').first()

        # Si no hay mantenimiento preventivo, no se generan alertas de kilometraje
        if not ultimo_mant:
            # Eliminar posibles alertas previas de kilometraje (por si acaso)
            AlertaMantencion.objects.filter(
                vehiculo=self,
                vigente=True,
                valor_umbral__in=[8000, 12000]
            ).update(vigente=False, resuelta_en=timezone.now())
            return

        km_base = ultimo_mant.km_al_ingreso
        recorrido = self.kilometraje_actual - km_base

        UMBRAL_PREVENTIVO = 8000
        UMBRAL_CRITICO = 12000

        if recorrido >= UMBRAL_CRITICO:
            nuevo_umbral = UMBRAL_CRITICO
            descripcion = (
                f'ALERTA CRÍTICA: {recorrido} km desde última mantención '
                f'(supera los {UMBRAL_CRITICO} km). Vehículo bloqueado para operación.'
            )
            if self.estado not in ['Fuera de servicio', 'Baja']:
                self.estado = 'Fuera de servicio'
                # Guardamos el cambio de estado (evitamos recursión usando update_fields)
                Vehiculo.objects.filter(pk=self.pk).update(estado=self.estado)

        elif recorrido >= UMBRAL_PREVENTIVO:
            nuevo_umbral = UMBRAL_PREVENTIVO
            descripcion = (
                f'Alerta por kilometraje: {recorrido} km desde última mantención '
                f'(umbral {UMBRAL_PREVENTIVO} km). Programar mantenimiento.'
            )
        else:
            # Si el recorrido es menor a 8000, no debe haber alerta de kilometraje vigente.
            AlertaMantencion.objects.filter(
                vehiculo=self,
                vigente=True,
                valor_umbral__in=[UMBRAL_PREVENTIVO, UMBRAL_CRITICO]
            ).update(vigente=False, resuelta_en=timezone.now())
            return

        # Manejo de alertas existentes
        alerta_existente = AlertaMantencion.objects.filter(
            vehiculo=self,
            vigente=True,
            valor_umbral=nuevo_umbral
        ).first()

        if alerta_existente:
            alerta_existente.descripcion = descripcion
            alerta_existente.save()
        else:
            # Desactivar la otra alerta si existe
            AlertaMantencion.objects.filter(
                vehiculo=self,
                vigente=True,
                valor_umbral__in=[UMBRAL_PREVENTIVO, UMBRAL_CRITICO]
            ).exclude(valor_umbral=nuevo_umbral).update(vigente=False, resuelta_en=timezone.now())

            AlertaMantencion.objects.create(
                vehiculo=self,
                descripcion=descripcion,
                valor_umbral=nuevo_umbral
            )

class Presupuesto(models.Model):
    """
    Presupuesto anual asignado a un vehículo o a la flota general.
    """
    id = models.AutoField(primary_key=True)
    anio = models.IntegerField(verbose_name="Año Presupuestario")

    TIPO_PRESUPUESTO = [
        ('Preventivo', 'Preventivo (Por Vehículo)'),
        ('Operativo', 'Operativo/Correctivo (Bolsa General)'),
    ]
    tipo_presupuesto = models.CharField(max_length=20, choices=TIPO_PRESUPUESTO, default='Preventivo')
    
    cuenta = models.ForeignKey(CuentaPresupuestaria, on_delete=models.PROTECT, related_name='presupuestos', verbose_name="Cuenta SIGFE")
    
    monto_asignado = models.IntegerField(validators=[MinValueValidator(0)])
    monto_ejecutado = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Campo para deshabilitar en vez de eliminar
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        db_table = 'presupuesto'
        verbose_name = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'
        unique_together = ['anio', 'cuenta']
    
    def __str__(self):
        return f"{self.anio} - {self.cuenta.codigo} - {self.cuenta.nombre}"

    @property
    def disponible(self):
        """Monto disponible del presupuesto"""
        return self.monto_asignado - self.monto_ejecutado
    
    @property
    def porcentaje_ejecutado(self):
        if self.monto_asignado > 0:
            return (self.monto_ejecutado / self.monto_asignado) * 100
        return 0
    
    def tiene_saldo_suficiente(self, monto_requerido):
        """Verifica si el presupuesto tiene saldo suficiente para un monto"""
        return self.disponible >= monto_requerido
    
    def consumir_presupuesto(self, monto):
        """Consume un monto del presupuesto (incrementa monto_ejecutado)"""
        if self.disponible >= monto:
            self.monto_ejecutado += monto
            self.save(update_fields=['monto_ejecutado'])
            return True
        return False
    
    def liberar_presupuesto(self, monto):
        """Libera un monto del presupuesto (disminuye monto_ejecutado)"""
        if self.monto_ejecutado >= monto:
            self.monto_ejecutado -= monto
            self.save(update_fields=['monto_ejecutado'])
            return True
        return False

    def save(self, *args, **kwargs):
        # Si se supera el presupuesto asignado, se deshabilita automáticamente.
        if self.monto_asignado > 0 and self.monto_ejecutado >= self.monto_asignado:
            self.activo = False
        super().save(*args, **kwargs)


# --- OPERACIONES Y MANTENIMIENTO ---

class OrdenTrabajo(models.Model):
    """
    Solicitud formal de trabajo al taller.
    """
    id = models.AutoField(primary_key=True)
    nro_ot = models.CharField(max_length=50, unique=True, verbose_name="Nro Orden de Trabajo")
    descripcion = models.TextField(verbose_name="Descripción del trabajo solicitado")
    fecha_solicitud = models.DateField()
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='ordenes_trabajo')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes_trabajo')
    # NOTA: La orden de compra se genera DESPUÉS de la orden de trabajo.
    # La relación está en OrdenCompra.orden_trabajo, no aquí.
    
    class Meta:
        db_table = 'orden_trabajo'
        verbose_name = 'Orden de Trabajo'
        verbose_name_plural = 'Ordenes de Trabajo'
    
    def __str__(self):
        return f"OT {self.nro_ot} - {self.vehiculo.patente}"


class Mantenimiento(models.Model):
    TIPOS_MANTENCION = [
        ('Preventivo', 'Preventivo'),
        ('Correctivo', 'Correctivo'),
    ]
    
    ESTADOS = [
        ('Programado', 'Programado'),
        ('En taller', 'En taller'),
        ('Esperando repuestos', 'Esperando repuestos'),
        ('Finalizado', 'Finalizado / Cerrado'),
        ('Cancelado', 'Cancelado'),
    ]
    
    id = models.AutoField(primary_key=True)
    tipo_mantencion = models.CharField(max_length=20, choices=TIPOS_MANTENCION)
    fecha_ingreso = models.DateField()
    fecha_salida = models.DateField(null=True, blank=True)
    fecha_programada = models.DateField(null=True, blank=True, verbose_name="Fecha Programada", 
                                         help_text="Fecha en que se programó realizar el mantenimiento (para alertas por tiempo)")
    km_al_ingreso = models.IntegerField(validators=[MinValueValidator(0)])
    
    descripcion_trabajo = models.TextField()
    estado = models.CharField(max_length=30, choices=ESTADOS, default='Programado')

    nro_factura = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número de Factura")
    archivo_adjunto = models.FileField(upload_to='mantenimientos/', null=True, blank=True, verbose_name="Documento Adjunto")
    
    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos_directos')
    
    # --- GESTIÓN DE COSTOS (PLANIFICADO vs REAL) ---
    costo_estimado = models.IntegerField(default=0, blank=True, help_text="Costo aproximado inicial")
    
    # Desglose de costos reales
    costo_mano_obra = models.IntegerField(default=0, verbose_name="Costo Mano de Obra")
    costo_repuestos = models.IntegerField(default=0, verbose_name="Costo Repuestos")
    costo_total_real = models.IntegerField(default=0, verbose_name="Costo Final Total")
    
    # Relaciones
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='mantenimientos')
    orden_trabajo = models.ForeignKey(OrdenTrabajo, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='mantenimientos')
    
    cuenta_presupuestaria = models.ForeignKey(CuentaPresupuestaria, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'mantenimiento'
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'

    def puede_cerrar_administrativamente(self):
        """
        Verifica si el mantenimiento cumple las condiciones para cierre administrativo
        (normativa hospitalaria: estado Finalizado requiere OC y costos reales).
        """
        if self.estado != 'Finalizado':
            return False
        if not self.orden_compra_id:
            return False
        if (self.costo_total_real or 0) <= 0:
            return False
        return True

    def _obtener_presupuesto_para_cierre(self):
        """Obtiene el presupuesto aplicable por cuenta y año. No modifica nada."""
        if not self.cuenta_presupuestaria or not self.vehiculo:
            return None
        anio = self.fecha_ingreso.year
        return Presupuesto.objects.filter(
            cuenta=self.cuenta_presupuestaria,
            anio=anio,
            activo=True
        ).first()

    def ejecutar_cierre_presupuestario(self):
        """
        Único punto de ejecución presupuestaria por mantenimiento.
        Valida: OC asociada, estado Finalizado, costos reales > 0, cuenta presupuestaria,
        presupuesto existe y con saldo.
        """
        if self.estado != 'Finalizado':
            return
        if not self.orden_compra_id:
            raise ValueError(
                "No se puede ejecutar presupuesto: el mantenimiento debe tener Orden de Compra asociada."
            )
        if (self.costo_total_real or 0) <= 0:
            return
        # Validar que tenga cuenta presupuestaria
        if not self.cuenta_presupuestaria:
            raise ValueError(
                "El mantenimiento no tiene una cuenta presupuestaria asignada. "
                "No se puede ejecutar el cierre presupuestario."
            )
        presupuesto = self._obtener_presupuesto_para_cierre()
        if not presupuesto:
            raise ValueError(
                f"No hay presupuesto asignado para la cuenta {self.cuenta_presupuestaria.codigo} "
                f"en el año {self.fecha_ingreso.year}."
            )
        if not presupuesto.tiene_saldo_suficiente(self.costo_total_real):
            raise ValueError(
                f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                f"Requerido: ${self.costo_total_real:.0f}"
            )
        from .signals import recalcular_monto_ejecutado
        recalcular_monto_ejecutado(presupuesto)

    def save(self, *args, **kwargs):
        # Auto-calcular total real si no se provee
        if self.costo_mano_obra or self.costo_repuestos:
            self.costo_total_real = self.costo_mano_obra + self.costo_repuestos
        # Bloqueos de cierre administrativo (sin atajos desde otras vistas/formularios)
        if self.estado == 'Finalizado':
            if not self.orden_compra_id:
                raise ValidationError(
                    "No se puede cerrar administrativamente un mantenimiento sin Orden de Compra asociada."
                )
            if (self.costo_total_real or 0) <= 0:
                raise ValidationError(
                    "No se puede cerrar administrativamente un mantenimiento sin costos reales."
                )
        if self.estado == 'Finalizado':
        # Al finalizar, resolver las alertas de kilometraje de este vehículo
            from django.utils import timezone
            AlertaMantencion.objects.filter(
                vehiculo=self.vehiculo,
                vigente=True,
                descripcion__icontains='kilometraje'
            ).update(vigente=False, resuelta_en=timezone.now())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_mantencion} {self.vehiculo.patente} - {self.fecha_ingreso}"

    @property
    def trazabilidad_presupuesto(self):
        if self.orden_trabajo and self.orden_trabajo.orden_compra:
            oc = self.orden_trabajo.orden_compra
            return {
                'presupuesto': oc.presupuesto,
                'cuenta_sigfe': oc.cuenta_presupuestaria,
                'folio_sigfe': oc.folio_sigfe,
                'nro_oc': oc.nro_oc,
                'nro_ot': self.orden_trabajo.nro_ot
            }
        return None


class Arriendo(models.Model):
    ESTADOS = [
        ('Activo', 'Activo'),
        ('Finalizado', 'Finalizado'),
    ]
    
    id = models.AutoField(primary_key=True)
    
    # Vinculación de vehículo arrendado con tabla de vehículos
    vehiculo_arrendado = models.ForeignKey(
        Vehiculo, 
        on_delete=models.PROTECT, 
        related_name='contratos_arriendo',
        limit_choices_to={'tipo_propiedad': 'Arrendado'},
        verbose_name="Vehículo Arrendado (Activo)"
    )
    
    # Vinculación con vehículo que reemplaza
    vehiculo_reemplazado = models.ForeignKey(
        Vehiculo, 
        on_delete=models.PROTECT, # Si se borra el vehículo, no se borra el historial del arriendo
        null=True, 
        blank=True, 
        related_name='arriendos_sustitutos', 
        limit_choices_to={'tipo_propiedad': 'Propio'},
        verbose_name="Vehículo Propio Reemplazado"
    )
    
    # Fechas y costos
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio Contrato")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha Fin Contrato")
    
    # Costos
    costo_diario = models.IntegerField(validators=[MinValueValidator(0)])
    costo_total = models.IntegerField(null=True, blank=True, verbose_name="Costo total estimado/real")
    
    # Gestión
    motivo = models.TextField(help_text="Ej: Ambulancia HR-PG-25 en pana de motor")
    nro_orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='arriendos') 
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='arriendos')
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activo')
    dias_arriendo = models.IntegerField(default=0, verbose_name="Días de arriendo")
    
    cuenta_presupuestaria = models.ForeignKey(CuentaPresupuestaria, on_delete=models.PROTECT, null=True, blank=True)
    
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        db_table = 'arriendo'
        verbose_name = 'Contrato de Arriendo'
        verbose_name_plural = 'Contratos de Arriendo'
    
    def clean(self):
        # Validar que no estemos tratando de arrendar un vehículo propio
        if self.vehiculo_arrendado_id and self.vehiculo_arrendado.tipo_propiedad == 'Propio':
            raise ValidationError("El vehículo seleccionado como 'Arrendado' figura como 'Propio' en el sistema.")
            
        # Validar que no se reemplace un vehículo con sigo mismo
        if self.vehiculo_reemplazado and self.vehiculo_arrendado_id and self.vehiculo_arrendado == self.vehiculo_reemplazado:
            raise ValidationError("El vehículo arrendado no puede ser el mismo que el reemplazado.")

    def save(self, *args, **kwargs):
        # Calcular días de arriendo
        if self.fecha_inicio and self.fecha_fin:
            self.dias_arriendo = (self.fecha_fin - self.fecha_inicio).days
            if self.dias_arriendo < 0:
                self.dias_arriendo = 0
        
        # Calcular costo total estimado
        if self.costo_diario and self.dias_arriendo > 0:
            self.costo_total = self.costo_diario * Decimal(self.dias_arriendo)
        
        # Al activar el arriendo, cambiamos el estado del vehículo arrendado a 'Disponible'
        if self.estado == 'Activo' and self.vehiculo_arrendado:
            self.vehiculo_arrendado.estado = 'Disponible'
            self.vehiculo_arrendado.save()
                
            # Marcar el vehículo propio como 'Fuera de servicio' si no lo está
            if self.vehiculo_reemplazado and self.vehiculo_reemplazado.estado != 'Baja':
                self.vehiculo_reemplazado.estado = 'Fuera de servicio'
                self.vehiculo_reemplazado.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Arriendo {self.vehiculo_arrendado.patente} ({self.proveedor}) - Reemplaza: {self.vehiculo_reemplazado}"


# --- OPERATIVA DIARIA ---

class HojaRuta(models.Model):
    id = models.AutoField(primary_key=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT)
    conductor = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    fecha = models.DateField(default=timezone.now)
    turno = models.CharField(max_length=50, choices=TURNOS)
    km_inicio = models.IntegerField(validators=[MinValueValidator(0)])
    km_fin = models.PositiveIntegerField(null=True, blank=True)
    
    # Tripulación (Reglas: Medico/Tens obligatorios, otros opcionales)
    medico_derivador = models.CharField(max_length=100, verbose_name="Médico del Turno")
    tens = models.CharField(max_length=100, verbose_name="TENS")
    
    # Opcionales
    enfermero = models.CharField(max_length=100, blank=True, null=True, verbose_name="Enfermero/Matrón")
    no_aplica_enfermero = models.BooleanField(default=False, verbose_name="No aplica Enfermero")
    
    camillero = models.CharField(max_length=100, blank=True, null=True)
    no_aplica_camillero = models.BooleanField(default=False, verbose_name="No aplica Camillero")
    
    abierta = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'hoja_ruta'
        verbose_name = 'Hoja de Ruta'
        verbose_name_plural = 'Hojas de Ruta'
        ordering = ['-fecha', '-creado_en']
    
    def __str__(self):
        return f"HR {self.vehiculo.patente} - {self.fecha} - {self.conductor.nombre_completo}"
    
    def clean(self):
        # Si no hay vehículo, no podemos continuar; el formulario ya mostrará error
        if not self.vehiculo_id:
            return

        if self.vehiculo.tipo_carroceria == 'Camioneta':
            if self.turno != '08-17':
                raise ValidationError({
                    'turno': 'Las camionetas solo pueden operar en turno administrativo (08:00 a 17:00).'
                })
            # Para camionetas, el resto de la validación no aplica
            return

        # Validaciones para ambulancias (no camionetas)
        if not self.medico_derivador:
            raise ValidationError({'medico_derivador': 'El médico derivador es obligatorio para ambulancias.'})
        if not self.tens:
            raise ValidationError({'tens': 'El TENS es obligatorio para ambulancias.'})
        if not self.no_aplica_enfermero and not self.enfermero:
            raise ValidationError({'enfermero': 'Debe indicar un Enfermero o marcar "No aplica".'})
        if not self.no_aplica_camillero and not self.camillero:
            raise ValidationError({'camillero': 'Debe indicar un Camillero o marcar "No aplica".'})

    @property
    def km_recorridos(self):
        if self.km_fin is not None and self.km_inicio is not None:
            return max(0, self.km_fin - self.km_inicio)
        return 0
    
    @property
    def tripulacion_str(self):
        """Devuelve string con la tripulación"""
        trip = f"Médico: {self.medico_derivador} | TENS: {self.tens}"
        if self.enfermero:
            trip += f" | Enfermero: {self.enfermero}"
        elif self.no_aplica_enfermero:
            trip += " | Sin enfermero"
        if self.camillero:
            trip += f" | Camillero: {self.camillero}"
        elif self.no_aplica_camillero:
            trip += " | Sin camillero"
        return trip


class Viaje(models.Model):
    id = models.AutoField(primary_key=True)
    hoja_ruta = models.ForeignKey(HojaRuta, on_delete=models.CASCADE, related_name='viajes')
    
    hora_salida = models.TimeField()
    hora_llegada = models.TimeField(null=True, blank=True)
    km_salida = models.PositiveIntegerField()
    km_llegada = models.PositiveIntegerField(null=True, blank=True)

    # Horas específicas para Hospital Base Osorno
    hora_salida_hbo = models.TimeField(null=True, blank=True, verbose_name="Hora Salida HBO")
    hora_llegada_hbo = models.TimeField(null=True, blank=True, verbose_name="Hora Llegada HBO")
    
    # Categorización del Viaje
    categoria_traslado = models.CharField(max_length=20, choices=TIPO_TRASLADO_CATEGORIA)
    detalle_origen_alta = models.CharField(max_length=20, choices=ORIGEN_ALTA, blank=True, null=True, verbose_name="Origen del Alta")
    
    observaciones = models.TextField(blank=True, null=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'viaje'
        verbose_name = 'Viaje'
        verbose_name_plural = 'Viajes'
        ordering = ['-hora_salida']
    
    def __str__(self):
        return f"Viaje {self.id} - {self.hoja_ruta.vehiculo.patente} - {self.hora_salida}"

    @property
    def get_pacientes_str(self):
        pkts = self.pacientes.all()
        if not pkts:
            return "Sin pacientes"
        return ", ".join([p.nombre for p in pkts])

    @property
    def km_recorridos_calculados(self):
        """Calcula automáticamente los KM recorridos en este viaje"""
        if self.km_llegada and self.km_salida:
            return max(0, self.km_llegada - self.km_salida)
        return 0

    def tiene_destino_hbo(self):
        """Verifica si algún paciente tiene destino HBO"""
        return self.pacientes.filter(destino_tipo='HBO').exists()


class PacienteViaje(models.Model):
    """
    Tabla maestra de pacientes que han sido trasladados en algún viaje.
    Permite listado desplegable para reutilizar datos en nuevos traslados.
    """
    id = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True, db_index=True)
    nombre = models.CharField(max_length=150)
    prevision = models.CharField(max_length=50, blank=True, verbose_name="Previsión/Tipo Servicio por defecto")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paciente_viaje'
        verbose_name = 'Paciente (traslados anteriores)'
        verbose_name_plural = 'Pacientes (traslados anteriores)'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.rut})"


class PacienteTraslado(models.Model):
    """Modelo para soportar 0 a N pacientes por viaje"""
    id = models.AutoField(primary_key=True)
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='pacientes')
    # Opcional: vincular con paciente de la tabla maestra (traslados anteriores)
    paciente_viaje = models.ForeignKey(
        PacienteViaje, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='traslados', verbose_name="Paciente (de listado anterior)"
    )
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, blank=True, null=True)
    
    # Requerimiento: Cada paciente tiene su destino y tipo de servicio
    destino_tipo = models.CharField(max_length=20, choices=DESTINOS_COMUNES)
    direccion_especifica = models.CharField(max_length=200, blank=True, help_text="Dirección si es domicilio u otro")
    prevision = models.CharField(max_length=50, blank=True, verbose_name="Previsión/Tipo Servicio")

    def __str__(self):
        return self.nombre


class CargaCombustible(models.Model):
    id = models.AutoField(primary_key=True)
    fecha = models.DateField()
    litros = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    
    precio_unitario = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    costo_total = models.IntegerField(validators=[MinValueValidator(0)])

    # Control para rendimiento
    kilometraje_al_cargar = models.IntegerField(validators=[MinValueValidator(0)])
    
    nro_boleta = models.CharField(max_length=50, blank=True)
    
    patente_vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='cargas_combustible')
    conductor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='cargas_combustible', null=True, blank=True)
    
    cuenta_presupuestaria = models.ForeignKey(CuentaPresupuestaria, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'carga_combustible'
        verbose_name = 'Carga de Combustible'
        verbose_name_plural = 'Cargas de Combustible'
    
    def __str__(self):
        return f"Combustible {self.patente_vehiculo.patente} - {self.fecha} - ${self.costo_total}"


class FallaReportada(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_reporte = models.DateField()
    descripcion = models.TextField()
    nivel_urgencia = models.CharField(max_length=20, choices=[('Alta', 'Alta'), ('Media', 'Media'), ('Baja', 'Baja')], null=True, blank=True, default='Media')
    
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='fallas_reportadas')
    conductor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='fallas_reportadas')
    
    mantenimiento = models.ForeignKey(Mantenimiento, on_delete=models.SET_NULL, null=True, blank=True, related_name='fallas_origen')
    
    class Meta:
        db_table = 'falla_reportada'
        verbose_name = 'Falla Reportada'
        verbose_name_plural = 'Fallas Reportadas'
    
    def __str__(self):
        return f"Falla {self.vehiculo.patente} - {self.fecha_reporte}"

class AlertaMantencion(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.TextField()
    valor_umbral = models.IntegerField()
    generado_en = models.DateTimeField(auto_now_add=True)
    vigente = models.BooleanField(default=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='alertas_mantencion')
    
    class Meta:
        db_table = 'alerta_mantencion'
        verbose_name = 'Alerta de Mantenimiento'
        verbose_name_plural = 'Alertas de Mantenimiento'
