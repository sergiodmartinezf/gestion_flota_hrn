from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator
from decimal import Decimal


class UsuarioManager(BaseUserManager):
    def create_user(self, rut, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un email')
        email = self.normalize_email(email)
        user = self.model(rut=rut, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, rut, email, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'Administrador')
        extra_fields.setdefault('activo', True)
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


class Proveedor(models.Model):
    id = models.AutoField(primary_key=True)
    rut_empresa = models.CharField(max_length=12, unique=True)
    nombre_fantasia = models.CharField(max_length=200)
    giro = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email_contacto = models.EmailField(blank=True)
    
    class Meta:
        db_table = 'proveedor'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
    
    def __str__(self):
        return self.nombre_fantasia


class OrdenCompra(models.Model):
    id = models.AutoField(primary_key=True)
    nro_oc = models.CharField(max_length=50, unique=True)
    fecha_emision = models.DateField()
    monto_neto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    id_licitacion = models.CharField(max_length=50, blank=True)
    folio_sigfe = models.CharField(max_length=50, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes_compra')
    
    class Meta:
        db_table = 'orden_compra'
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Ordenes de Compra'
    
    def __str__(self):
        return f"OC {self.nro_oc} - {self.proveedor.nombre_fantasia}"


class Vehiculo(models.Model):
    ESTADOS = [
        ('Disponible', 'Disponible'),
        ('En uso', 'En uso'),
        ('En mantenimiento', 'En mantenimiento'),
        ('Fuera de servicio', 'Fuera de servicio'),
        ('Arrendado', 'Arrendado'),
    ]
    
    TIPOS_PROPIEDAD = [
        ('Propio', 'Propio'),
        ('Arrendado', 'Arrendado'),
    ]
    
    TIPOS_CARROCERIA = [
        ('Ambulancia', 'Ambulancia'),
        ('Camioneta', 'Camioneta'),
        ('Otro', 'Otro'),
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
    vida_util = models.IntegerField(default=10)  # años
    vida_util_residual = models.IntegerField(default=0)
    kilometraje_actual = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    umbral_mantencion = models.IntegerField(default=10000, validators=[MinValueValidator(0)])
    tipo_carroceria = models.CharField(max_length=20, choices=TIPOS_CARROCERIA)
    clase_ambulancia = models.CharField(max_length=50, blank=True)
    es_samu = models.BooleanField(default=False)
    establecimiento = models.CharField(max_length=200, default='Hospital Río Negro')
    criticidad = models.CharField(max_length=20, choices=CRITICIDAD, default='No crítico')
    es_backup = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Disponible')
    tipo_propiedad = models.CharField(max_length=20, choices=TIPOS_PROPIEDAD, default='Propio')
    dias_fuera_servicio = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    creado_en = models.DateTimeField(auto_now_add=True)
    
    # Relaciones opcionales
    orden_trabajo = models.ForeignKey('OrdenTrabajo', on_delete=models.SET_NULL, null=True, blank=True, related_name='vehiculos_ot')
    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehiculos_oc')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehiculos')
    
    class Meta:
        db_table = 'vehiculo'
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
    
    def __str__(self):
        return f"{self.patente} - {self.marca} {self.modelo}"
    
    @property
    def kilometraje_para_mantencion(self):
        """Calcula cuántos kilómetros faltan para el próximo mantenimiento"""
        return max(0, self.umbral_mantencion - (self.kilometraje_actual % self.umbral_mantencion))


class OrdenTrabajo(models.Model):
    id = models.AutoField(primary_key=True)
    nro_ot = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField()
    fecha_solicitud = models.DateField()
    fecha_programada = models.DateField()
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='ordenes_trabajo')
    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_trabajo')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes_trabajo')
    
    class Meta:
        db_table = 'orden_trabajo'
        verbose_name = 'Orden de Trabajo'
        verbose_name_plural = 'Ordenes de Trabajo'
    
    def __str__(self):
        return f"OT {self.nro_ot} - {self.vehiculo.patente}"


class Presupuesto(models.Model):
    id = models.AutoField(primary_key=True)
    anio = models.IntegerField()
    categoria = models.CharField(max_length=100)
    subasignacion_sigfe = models.CharField(max_length=50)
    monto_asignado = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    monto_ejecutado = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))])
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='presupuestos')
    
    class Meta:
        db_table = 'presupuesto'
        verbose_name = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'
        unique_together = ['anio', 'vehiculo', 'categoria']
    
    def __str__(self):
        return f"Presupuesto {self.anio} - {self.vehiculo.patente} - {self.categoria}"
    
    @property
    def porcentaje_ejecutado(self):
        if self.monto_asignado > 0:
            return (self.monto_ejecutado / self.monto_asignado) * 100
        return 0


class Arriendo(models.Model):
    ESTADOS = [
        ('Activo', 'Activo'),
        ('Finalizado', 'Finalizado'),
        ('Cancelado', 'Cancelado'),
    ]
    
    id = models.AutoField(primary_key=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    costo_diario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    nro_orden_compra = models.CharField(max_length=50, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activo')
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='arriendos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='arriendos')
    
    class Meta:
        db_table = 'arriendo'
        verbose_name = 'Arriendo'
        verbose_name_plural = 'Arriendos'
    
    def __str__(self):
        return f"Arriendo {self.vehiculo.patente} - {self.proveedor.nombre_fantasia}"


class DisponibilidadVehiculo(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    motivo = models.TextField()
    dias_no_operativo = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='disponibilidades')
    
    class Meta:
        db_table = 'disponibilidad_vehiculo'
        verbose_name = 'Disponibilidad de Vehículo'
        verbose_name_plural = 'Disponibilidades de Vehículos'
    
    def __str__(self):
        return f"{self.vehiculo.patente} - {self.fecha_inicio}"


class HojaRuta(models.Model):
    TURNOS = [
        ('Mañana', 'Mañana'),
        ('Tarde', 'Tarde'),
        ('Noche', 'Noche'),
    ]
    
    id = models.AutoField(primary_key=True)
    fecha = models.DateField()
    turno = models.CharField(max_length=20, choices=TURNOS)
    km_inicio = models.IntegerField(validators=[MinValueValidator(0)])
    km_fin = models.IntegerField(validators=[MinValueValidator(0)])
    litros_inicio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    litros_fin = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
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
        ('Traslado', 'Traslado'),
        ('Emergencia', 'Emergencia'),
        ('Otro', 'Otro'),
    ]
    
    id = models.AutoField(primary_key=True)
    hora_salida = models.TimeField()
    hora_llegada = models.TimeField(null=True, blank=True)
    destino = models.CharField(max_length=200)
    rut_paciente = models.CharField(max_length=12, blank=True)
    tipo_servicio = models.CharField(max_length=20, choices=TIPOS_SERVICIO, default='Traslado')
    km_recorridos = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    hoja_ruta = models.ForeignKey(HojaRuta, on_delete=models.CASCADE, related_name='viajes')
    
    class Meta:
        db_table = 'viaje'
        verbose_name = 'Viaje'
        verbose_name_plural = 'Viajes'
    
    def __str__(self):
        return f"Viaje {self.hoja_ruta.vehiculo.patente} - {self.destino}"


class CargaCombustible(models.Model):
    id = models.AutoField(primary_key=True)
    fecha = models.DateField()
    litros = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    kilometraje_al_cargar = models.IntegerField(validators=[MinValueValidator(0)])
    costo_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    nro_boleta = models.CharField(max_length=50, blank=True)
    patente_vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='cargas_combustible')
    conductor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='cargas_combustible', null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='cargas_combustible')
    hoja_ruta = models.ForeignKey(HojaRuta, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargas_combustible')
    
    class Meta:
        db_table = 'carga_combustible'
        verbose_name = 'Carga de Combustible'
        verbose_name_plural = 'Cargas de Combustible'
    
    def __str__(self):
        return f"Combustible {self.patente_vehiculo.patente} - {self.fecha}"


class Mantenimiento(models.Model):
    TIPOS_MANTENCION = [
        ('Preventivo', 'Preventivo'),
        ('Correctivo', 'Correctivo'),
    ]
    
    ESTADOS = [
        ('Programado', 'Programado'),
        ('En taller', 'En taller'),
        ('Completado', 'Completado'),
        ('Cancelado', 'Cancelado'),
    ]
    
    id = models.AutoField(primary_key=True)
    tipo_mantencion = models.CharField(max_length=20, choices=TIPOS_MANTENCION)
    fecha_ingreso = models.DateField()
    fecha_salida = models.DateField(null=True, blank=True)
    km_al_ingreso = models.IntegerField(validators=[MinValueValidator(0)])
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))])
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Programado')
    dias_fuera_servicio = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='mantenimientos')
    orden_trabajo = models.ForeignKey(OrdenTrabajo, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos')
    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='mantenimientos')
    
    class Meta:
        db_table = 'mantenimiento'
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
    
    def __str__(self):
        return f"{self.tipo_mantencion} {self.vehiculo.patente} - {self.fecha_ingreso}"


class AlertaMantencion(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.TextField()
    valor_umbral = models.IntegerField()
    generado_en = models.DateTimeField(auto_now_add=True)
    vigente = models.BooleanField(default=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='alertas_mantencion')
    mantenimiento = models.ForeignKey(Mantenimiento, on_delete=models.SET_NULL, null=True, blank=True, related_name='alertas')
    
    class Meta:
        db_table = 'alerta_mantencion'
        verbose_name = 'Alerta de Mantenimiento'
        verbose_name_plural = 'Alertas de Mantenimiento'
    
    def __str__(self):
        return f"Alerta {self.vehiculo.patente} - {self.generado_en.date()}"


class FallaReportada(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_reporte = models.DateField()
    descripcion = models.TextField()
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='fallas_reportadas')
    conductor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='fallas_reportadas')
    mantenimiento = models.ForeignKey(Mantenimiento, on_delete=models.SET_NULL, null=True, blank=True, related_name='fallas')
    
    class Meta:
        db_table = 'falla_reportada'
        verbose_name = 'Falla Reportada'
        verbose_name_plural = 'Fallas Reportadas'
    
    def __str__(self):
        return f"Falla {self.vehiculo.patente} - {self.fecha_reporte}"

