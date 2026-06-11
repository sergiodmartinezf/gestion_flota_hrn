from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

from .choices import (
    TIPOS_SERVICIO, TURNOS, TIPO_TRASLADO_CATEGORIA, ORIGEN_ALTA,
    DESTINOS_COMUNES, CODIGOS_DESTINOS_RED, ROL_TRIPULACION,
)
from .usuario import Usuario
from .vehiculo import Vehiculo
from .proveedor import CuentaPresupuestaria
from .mantenimiento import Mantenimiento

class HojaRuta(models.Model):
    id = models.AutoField(primary_key=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT)
    conductor = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    fecha = models.DateField(default=timezone.now)
    turno = models.CharField(max_length=50, choices=TURNOS)
    km_inicio = models.IntegerField(validators=[MinValueValidator(0)])
    km_fin = models.PositiveIntegerField(null=True, blank=True)
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

    @property
    def km_recorridos(self):
        if self.km_fin is not None and self.km_inicio is not None:
            return max(0, self.km_fin - self.km_inicio)
        return 0


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

    no_aplica_enfermero = models.BooleanField(default=True, verbose_name="No aplica Enfermero")
    no_aplica_camillero = models.BooleanField(default=True, verbose_name="No aplica Camillero")

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
        ruts = [p.rut for p in pkts if p.rut]
        return ", ".join(ruts) if ruts else "Sin pacientes"

    @property
    def km_recorridos_calculados(self):
        """Calcula automáticamente los KM recorridos en este viaje"""
        if self.km_llegada and self.km_salida:
            return max(0, self.km_llegada - self.km_salida)
        return 0

    def tiene_destino_hbo(self):
        """Verifica si algún paciente tiene destino HBO"""
        return self.pacientes.filter(destino_tipo='HBO').exists()

    def tiene_destino_red_hospital(self):
        """Verifica si algún paciente tiene destino en la red hospitalaria"""
        return self.pacientes.filter(destino_tipo__in=CODIGOS_DESTINOS_RED).exists()

    def tripulacion_por_rol(self, rol):
        return self.tripulacion.filter(rol=rol).order_by('id')

    @property
    def tripulacion_str(self):
        partes = []
        for rol, etiqueta in ROL_TRIPULACION:
            nombres = list(self.tripulacion.filter(rol=rol).values_list('nombre', flat=True))
            if nombres:
                partes.append(f"{etiqueta}: {', '.join(nombres)}")
            elif rol == 'ENFERMERO' and self.no_aplica_enfermero:
                partes.append('Sin enfermero')
            elif rol == 'CAMILLERO' and self.no_aplica_camillero:
                partes.append('Sin camillero')
        return ' | '.join(partes) if partes else 'Sin tripulación registrada'


class PersonaTripulacion(models.Model):
    """Catálogo de personal de tripulación ingresado en viajes anteriores."""
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    rol = models.CharField(max_length=20, choices=ROL_TRIPULACION)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'persona_tripulacion'
        verbose_name = 'Persona de tripulación'
        verbose_name_plural = 'Personas de tripulación'
        ordering = ['rol', 'nombre']
        constraints = [
            models.UniqueConstraint(fields=['nombre', 'rol'], name='uniq_persona_tripulacion_nombre_rol'),
        ]

    def __str__(self):
        return f"{self.get_rol_display()}: {self.nombre}"


class TripulacionViaje(models.Model):
    """Miembros de tripulación asociados a un viaje (0 a N por rol)."""
    id = models.AutoField(primary_key=True)
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='tripulacion')
    persona_tripulacion = models.ForeignKey(
        PersonaTripulacion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='asignaciones', verbose_name="Persona (de listado anterior)",
    )
    nombre = models.CharField(max_length=100)
    rol = models.CharField(max_length=20, choices=ROL_TRIPULACION)

    class Meta:
        db_table = 'tripulacion_viaje'
        verbose_name = 'Tripulación de viaje'
        verbose_name_plural = 'Tripulación de viajes'
        ordering = ['rol', 'id']

    def __str__(self):
        return f"{self.get_rol_display()}: {self.nombre}"


class PacienteViaje(models.Model):
    """
    Tabla maestra de RUT de pacientes/pasajeros trasladados en viajes anteriores.
    Permite listado desplegable para reutilizar el RUT en nuevos traslados.
    """
    id = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paciente_viaje'
        verbose_name = 'Paciente (traslados anteriores)'
        verbose_name_plural = 'Pacientes (traslados anteriores)'
        ordering = ['rut']

    def __str__(self):
        return self.rut


class PacienteTraslado(models.Model):
    """Modelo para soportar 0 a N pacientes por viaje"""
    id = models.AutoField(primary_key=True)
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='pacientes')
    # Opcional: vincular con paciente de la tabla maestra (traslados anteriores)
    paciente_viaje = models.ForeignKey(
        PacienteViaje, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='traslados', verbose_name="Paciente (de listado anterior)"
    )
    rut = models.CharField(max_length=12, blank=True, default='')

    categoria_traslado = models.CharField(
        max_length=20, choices=TIPO_TRASLADO_CATEGORIA, default='Administrativo'
    )
    detalle_origen_alta = models.CharField(
        max_length=20, choices=ORIGEN_ALTA, blank=True, null=True, verbose_name="Origen del Alta"
    )
    sentido = models.CharField(
        max_length=10,
        choices=[('IDA', 'Ida'), ('REGRESO', 'Regreso')],
        default='IDA',
    )
    
    destino_tipo = models.CharField(max_length=20, choices=DESTINOS_COMUNES)
    direccion_especifica = models.CharField(max_length=200, blank=True, help_text="Dirección si es domicilio u otro")

    class Meta:
        db_table = 'paciente_traslado'

    def __str__(self):
        return self.rut or f"Paciente #{self.pk}"


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

class Alerta(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.TextField()
    valor_umbral = models.IntegerField()
    generado_en = models.DateTimeField(auto_now_add=True)
    vigente = models.BooleanField(default=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='alertas')
    
    class Meta:
        db_table = 'alerta'
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
