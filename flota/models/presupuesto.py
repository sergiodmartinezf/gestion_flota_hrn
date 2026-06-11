from django.db import models
from django.core.validators import MinValueValidator

from .proveedor import CuentaPresupuestaria

class Presupuesto(models.Model):
    """
    Presupuesto anual asignado a un vehículo o a la flota general.
    """
    id = models.AutoField(primary_key=True)
    anio = models.IntegerField(verbose_name="Año Presupuestario")

    TIPO_PRESUPUESTO = [
        ('Preventivo', 'Preventivo (Por Vehículo)'),
        ('Operativo', 'Correctivo (Bolsa General)'),
    ]
    tipo_presupuesto = models.CharField(max_length=20, choices=TIPO_PRESUPUESTO, default='Preventivo')
    
    cuenta = models.ForeignKey(CuentaPresupuestaria, on_delete=models.PROTECT, related_name='presupuestos', verbose_name="Cuenta SIGFE")
    
    monto_asignado = models.IntegerField(validators=[MinValueValidator(0)])
    monto_ejecutado = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Campo para deshabilitar en vez de eliminar
    activo = models.BooleanField(default=True, verbose_name="Activo")
    alerta_presupuesto_ignorada = models.BooleanField(
        default=False,
        verbose_name="Alerta de ejecución descartada",
    )
    
    class Meta:
        db_table = 'presupuesto'
        verbose_name = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'
        unique_together = ['anio', 'cuenta']
    
    def __str__(self):
        return f"{self.anio} - {self.cuenta.codigo} - {self.cuenta.nombre}"

    @property
    def disponible(self):
        """
        Monto disponible del presupuesto
        """
        return self.monto_asignado - self.monto_ejecutado
    
    @property
    def porcentaje_ejecutado(self):
        if self.monto_asignado > 0:
            return (self.monto_ejecutado / self.monto_asignado) * 100
        return 0
    
    def tiene_saldo_suficiente(self, monto_requerido):
        """
        Verifica si el presupuesto tiene saldo suficiente para un monto
        """
        return self.disponible >= monto_requerido
    
    def consumir_presupuesto(self, monto):
        """
        Consume un monto del presupuesto (incrementa monto_ejecutado)
        """
        if self.disponible >= monto:
            self.monto_ejecutado += monto
            self.save(update_fields=['monto_ejecutado'])
            return True
        return False
    
    def liberar_presupuesto(self, monto):
        """
        Libera un monto del presupuesto (disminuye monto_ejecutado)
        """
        if self.monto_ejecutado >= monto:
            self.monto_ejecutado -= monto
            self.save(update_fields=['monto_ejecutado'])
            return True
        return False

    def save(self, *args, **kwargs):
        # Si se supera el presupuesto asignado, se deshabilita automáticamente.
        if self.monto_asignado > 0 and self.monto_ejecutado >= self.monto_asignado:
            self.activo = False
        if self.monto_asignado > 0 and self.porcentaje_ejecutado < 80:
            self.alerta_presupuesto_ignorada = False
        super().save(*args, **kwargs)

