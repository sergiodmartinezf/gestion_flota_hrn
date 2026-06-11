from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from .vehiculo import Vehiculo
from .proveedor import Proveedor, CuentaPresupuestaria
from .orden_compra import OrdenCompra

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
            self.costo_total = self.costo_diario * self.dias_arriendo
        
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

