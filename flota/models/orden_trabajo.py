from django.db import models

from .vehiculo import Vehiculo
from .proveedor import Proveedor

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

