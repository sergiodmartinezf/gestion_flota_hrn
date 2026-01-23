from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

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
    
    rut = models.CharField(max_length=12, unique=True, primary_key=True)
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
    giro = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email_contacto = models.EmailField(blank=True)
    es_taller = models.BooleanField(default=False, verbose_name="Es Taller Mecánico")
    es_arrendador = models.BooleanField(default=False, verbose_name="Es Arrendador de Vehículos")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        db_table = 'proveedor'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
    
    def __str__(self):
        return self.nombre_fantasia


class CuentaPresupuestaria(models.Model):
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
    ESTADOS_OC = [
        ('Emitida', 'Emitida'),
        ('Aceptada', 'Aceptada'),
        ('Recepcionada', 'Recepcionada'),
        ('Pagada', 'Pagada'),
        ('Anulada', 'Anulada'),
    ]

    id = models.AutoField(primary_key=True)
    nro_oc = models.CharField(max_length=50, unique=True, verbose_name="Nro Orden de Compra")
    descripcion = models.TextField(blank=True, verbose_name="Descripción de la OC")
    fecha_emision = models.DateField()
    
    # Montos planificados (según OC física)
    monto_neto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))]) # IVA
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    
    id_licitacion = models.CharField(max_length=50, blank=True, verbose_name="ID MercadoPúblico")
    folio_sigfe = models.CharField(max_length=50, blank=True, verbose_name="Folio SIGFE")
    estado = models.CharField(max_length=20, choices=ESTADOS_OC, default='Emitida')
    
    # Archivo físico digitalizado
    archivo_adjunto = models.FileField(upload_to='ordenes_compra/', null=True, blank=True, verbose_name="PDF Orden de Compra")
    
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes_compra')
    vehiculo = models.ForeignKey('Vehiculo', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vehículo Asociado", help_text="Vehículo identificado en la importación")
    cuenta_presupuestaria = models.ForeignKey(CuentaPresupuestaria, on_delete=models.PROTECT, related_name='ordenes_compra', null=True, blank=True)
    presupuesto = models.ForeignKey('Presupuesto', on_delete=models.PROTECT, related_name='ordenes_compra', null=True, blank=True, verbose_name="Presupuesto asociado")
    
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
    
    patente = models.CharField(max_length=10, primary_key=True)
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
    
    monto_asignado = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    monto_ejecutado = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))])
    
    # Opcional: Presupuesto específico por vehículo, si es null es presupuesto global de la cuenta
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='presupuestos', null=True, blank=True)
    
    # Campo para deshabilitar en vez de eliminar
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        db_table = 'presupuesto'
        verbose_name = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'
        unique_together = ['anio', 'vehiculo', 'cuenta']
    
    def __str__(self):
        destino = self.vehiculo.patente if self.vehiculo else "Flota General"
        return f"{self.anio} - {self.cuenta.codigo} - {destino}"

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
    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_trabajo')
    
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
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, help_text="Costo aproximado inicial")
    
    # Desglose de costos reales
    costo_mano_obra = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Costo Mano de Obra")
    costo_repuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Costo Repuestos")
    costo_total_real = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Costo Final Total")
    
    # Relaciones
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='mantenimientos')
    orden_trabajo = models.ForeignKey(OrdenTrabajo, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='mantenimientos')
    
    cuenta_presupuestaria = models.ForeignKey(CuentaPresupuestaria, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'mantenimiento'
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Auto-calcular total real si no se provee
        if self.costo_mano_obra or self.costo_repuestos:
            self.costo_total_real = self.costo_mano_obra + self.costo_repuestos
        
        # Guardar primero para obtener PK si es nuevo
        super().save(*args, **kwargs)
        
        # Gestionar presupuesto si hay cuenta presupuestaria
        if self.cuenta_presupuestaria and self.vehiculo and self.estado == 'Finalizado':
            try:
                presupuesto = Presupuesto.objects.get(
                    cuenta=self.cuenta_presupuestaria,
                    vehiculo=self.vehiculo,
                    anio=self.fecha_ingreso.year,
                    activo=True
                )
                
                # Solo consumir presupuesto si el mantenimiento está finalizado
                if self.costo_total_real > 0:
                    # El signal se encargará de actualizar el monto ejecutado
                    # Asegurarse de que no se duplique
                    pass
                    
            except Presupuesto.DoesNotExist:
                # Intentar con presupuesto global si no hay específico
                try:
                    presupuesto = Presupuesto.objects.get(
                        cuenta=self.cuenta_presupuestaria,
                        vehiculo__isnull=True,
                        anio=self.fecha_ingreso.year,
                        activo=True
                    )
                except Presupuesto.DoesNotExist:
                    # No hay presupuesto asignado
                    pass

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
    costo_diario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Costo total estimado/real")
    
    # Gestión
    motivo = models.TextField(help_text="Ej: Ambulancia HR-PG-25 en pana de motor")
    nro_orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='arriendos') 
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='arriendos')
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activo')
    dias_arriendo = models.IntegerField(default=0, verbose_name="Días de arriendo")
    
    cuenta_presupuestaria = models.ForeignKey(CuentaPresupuestaria, on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        db_table = 'arriendo'
        verbose_name = 'Contrato de Arriendo'
        verbose_name_plural = 'Contratos de Arriendo'
    
    def clean(self):
        # Validar que no estemos tratando de arrendar un vehículo propio
        if self.vehiculo_arrendado and self.vehiculo_arrendado.tipo_propiedad == 'Propio':
            raise ValidationError("El vehículo seleccionado como 'Arrendado' figura como 'Propio' en el sistema.")
            
        # Validar que no se reemplace un vehículo con sigo mismo
        if self.vehiculo_reemplazado and self.vehiculo_arrendado == self.vehiculo_reemplazado:
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
                 pass

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Arriendo {self.vehiculo_arrendado.patente} ({self.proveedor}) - Reemplaza: {self.vehiculo_reemplazado}"


# --- OPERATIVA DIARIA ---

class HojaRuta(models.Model):
    TURNOS = [
        ('08-20', 'Turno 08:00 a 20:00'),
        ('20-08', 'Turno 20:00 a 08:00'),
        ('09-20', 'Turno 09:00 a 20:00 (fin de semana/feriado)'),
        ('20-09', 'Turno 20:00 a 09:00 (fin de semana/feriado)'),
    ]
    
    id = models.AutoField(primary_key=True)
    fecha = models.DateField()
    turno = models.CharField(max_length=20, choices=TURNOS)

    # REQ: Campos de personal médico (Digitalización)
    medico = models.CharField(max_length=150, blank=True, verbose_name="Médico")
    enfermero = models.CharField(max_length=150, blank=True, verbose_name="Enfermero/a")
    tens = models.CharField(max_length=150, blank=True, verbose_name="TENS")
    camillero = models.CharField(max_length=150, blank=True, verbose_name="Camillero")

    # REQ: Kilometraje obligatorio (se valida en form, aqui min value)
    km_inicio = models.IntegerField(validators=[MinValueValidator(0)])
    km_fin = models.IntegerField(validators=[MinValueValidator(0)])

    # REQ: Eliminar campos de litros de inicio y fin (ELIMINADOS)
    # litros_inicio = ... (ELIMINADO)
    # litros_fin = ... (ELIMINADO)

    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    conductor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='hojas_ruta')
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='hojas_ruta')
    
    class Meta:
        db_table = 'hoja_ruta'
        verbose_name = 'Hoja de Ruta'
        verbose_name_plural = 'Hojas de Ruta'
    
    def __str__(self):
        return f"HR {self.vehiculo.patente} - {self.fecha} - {self.conductor.nombre_completo}"
    
    @property
    def km_recorridos(self):
        return max(0, self.km_fin - self.km_inicio)


class Viaje(models.Model):
    TIPOS_SERVICIO = [
        ('Traslado Paciente', 'Traslado Paciente'),
        ('Administrativo', 'Administrativo'),
        ('Urgencia SAMU', 'Urgencia SAMU'),
        ('Ronda Médica', 'Ronda Médica'),
        ('Otro', 'Otro'),
    ]
    
    id = models.AutoField(primary_key=True)
    hora_salida = models.TimeField()
    hora_llegada = models.TimeField(null=True, blank=True)
    destino = models.CharField(max_length=200)
    rut_paciente = models.CharField(max_length=12, blank=True)
    nombre_paciente = models.CharField(max_length=150, blank=True)
    tipo_servicio = models.CharField(max_length=30, choices=TIPOS_SERVICIO, default='Traslado Paciente')
    #km_recorridos_viaje = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    km_inicio_viaje = models.IntegerField(
        validators=[MinValueValidator(0)], 
        verbose_name="KM al inicio del viaje"
    )
    km_fin_viaje = models.IntegerField(
        validators=[MinValueValidator(0)], 
        verbose_name="KM al final del viaje"
    )
    
    hoja_ruta = models.ForeignKey(HojaRuta, on_delete=models.CASCADE, related_name='viajes')
    
    class Meta:
        db_table = 'viaje'
        verbose_name = 'Viaje'
        verbose_name_plural = 'Viajes'
    
    def __str__(self):
        return f"Viaje {self.hoja_ruta.vehiculo.patente} - {self.destino}"

    @property
    def km_recorridos_calculados(self):
        """Calcula automáticamente los KM recorridos en este viaje"""
        return max(0, self.km_fin_viaje - self.km_inicio_viaje)


class CargaCombustible(models.Model):
    id = models.AutoField(primary_key=True)
    fecha = models.DateField()
    litros = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Control para rendimiento
    kilometraje_al_cargar = models.IntegerField(validators=[MinValueValidator(0)])
    
    costo_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
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
    nivel_urgencia = models.CharField(max_length=20, choices=[('Alta', 'Alta'), ('Media', 'Media'), ('Baja', 'Baja')], null=True, blank=True,default='Media')
    
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
