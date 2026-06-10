from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from .vehiculo import Vehiculo
from .proveedor import Proveedor, CuentaPresupuestaria
from .orden_compra import OrdenCompra
from .orden_trabajo import OrdenTrabajo
from .presupuesto import Presupuesto

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
        Verifica si el mantenimiento cumple las condiciones para cierre administrativo (normativa hospitalaria: estado Finalizado requiere OC y costos reales).
        """
        if self.estado != 'Finalizado':
            return False
        if not self.orden_compra_id:
            return False
        if (self.costo_total_real or 0) <= 0:
            return False
        return True

    def _obtener_presupuesto_para_cierre(self):
        """
        Obtiene el presupuesto aplicable por cuenta y año. No modifica nada.
        """
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
        Único punto de ejecución presupuestaria por mantenimiento. Valida: OC asociada, estado Finalizado, costos reales > 0, cuenta presupuestaria, presupuesto existe y con saldo.
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
        from flota.signals import recalcular_monto_ejecutado
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
            from .operativa import Alerta

            Alerta.objects.filter(
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

