from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from .proveedor import Proveedor, CuentaPresupuestaria
from .presupuesto import Presupuesto
from .orden_trabajo import OrdenTrabajo

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
        NOTA: El consumo real del presupuesto se hace a través de signals que recalculan basándose en las OCs activas (no anuladas).
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

