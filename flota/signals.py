from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum, Q
from decimal import Decimal
from .models import Mantenimiento, Presupuesto, CargaCombustible, Arriendo, OrdenCompra
from .services.presupuesto import validar_presupuesto_disponible

@receiver(pre_save, sender=Mantenimiento)
def validar_cierre_administrativo_mantenimiento(sender, instance, **kwargs):
    """
    Valida condiciones de cierre administrativo: Finalizado requiere OC y presupuesto suficiente.
    La ejecución presupuestaria se hace solo vía Mantenimiento.ejecutar_cierre_presupuestario().
    """
    if instance.estado != 'Finalizado':
        return
    # Obligatorio: Orden de Compra asociada
    if not instance.orden_compra_id:
        raise ValueError(
            "No se puede cerrar un mantenimiento sin Orden de Compra asociada."
        )
    if (instance.costo_total_real or 0) <= 0:
        raise ValueError(
            "No se puede cerrar un mantenimiento sin costos reales."
        )
    if not instance.cuenta_presupuestaria or not instance.vehiculo:
        return
    ok, mensaje, presupuesto = validar_presupuesto_disponible(
        instance.cuenta_presupuestaria,
        instance.fecha_ingreso.year,
        instance.costo_total_real,
    )
    if not ok:
        raise ValueError(mensaje)

@receiver(post_delete, sender=Mantenimiento)
def actualizar_presupuesto_al_borrar_mantenimiento(sender, instance, **kwargs):
    """
    Al borrar un mantenimiento finalizado, recalcular presupuesto afectado.
    La ejecución en guardado se hace solo vía Mantenimiento.ejecutar_cierre_presupuestario().
    """
    if instance.estado != 'Finalizado' or not instance.cuenta_presupuestaria:
        return
    anio = instance.fecha_ingreso.year
    presupuestos = Presupuesto.objects.filter(
        cuenta=instance.cuenta_presupuestaria,
        anio=anio,
        activo=True
    )
    for p in presupuestos:
        recalcular_monto_ejecutado(p)

def recalcular_monto_ejecutado(presupuesto):
    """
    Recalcula el total gastado para un presupuesto específico sumando
    Mantenimientos, Combustible y Arriendos asociados.
    """
    anio = presupuesto.anio
    cuenta = presupuesto.cuenta
    total = Decimal(0)

    # 1. Mantenimientos finalizados
    total += Mantenimiento.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha_ingreso__year=anio,
        estado='Finalizado'
    ).aggregate(total=Sum('costo_total_real'))['total'] or Decimal(0)
    
    # 2. Combustible
    total += CargaCombustible.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha__year=anio
    ).aggregate(total=Sum('costo_total'))['total'] or Decimal(0)
    
    # 3. Arriendos
    total += Arriendo.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha_inicio__year=anio,
        estado='Activo'
    ).aggregate(total=Sum('costo_total'))['total'] or Decimal(0)
    
    # 4. Órdenes de compra no anuladas (que no estén ya en mantenimientos)
    ids_oc_contabilizadas = set(
        Mantenimiento.objects.filter(
            estado='Finalizado',
            cuenta_presupuestaria=cuenta,
            fecha_ingreso__year=anio,
            orden_compra_id__isnull=False
        ).values_list('orden_compra_id', flat=True)
    )
    
    ocs = OrdenCompra.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha_emision__year=anio
    ).exclude(estado='Anulada')
    
    if ids_oc_contabilizadas:
        ocs = ocs.exclude(id__in=ids_oc_contabilizadas)
    
    total += ocs.aggregate(total=Sum('monto_total'))['total'] or Decimal(0)
    
    presupuesto.monto_ejecutado = total
    presupuesto.save(update_fields=['monto_ejecutado', 'activo'])


@receiver(post_save, sender=OrdenCompra)
@receiver(post_delete, sender=OrdenCompra)
def actualizar_presupuesto_orden_compra(sender, instance, **kwargs):
    """
    Cuando se guarda/borra una OC, recalcular el presupuesto asociado.
    Las OCs representan compromisos presupuestarios.
    """
    if not instance.cuenta_presupuestaria:
        return
    
    anio = instance.fecha_emision.year
    
    # Buscar presupuestos afectados
    presupuestos = Presupuesto.objects.filter(
        cuenta=instance.cuenta_presupuestaria,
        anio=anio,
        activo=True
    )
    
    for p in presupuestos:
        recalcular_monto_ejecutado(p)

    