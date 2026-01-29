from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from .models import Mantenimiento, Presupuesto, CargaCombustible, Arriendo, OrdenCompra

@receiver(pre_save, sender=Mantenimiento)
def validar_presupuesto_antes_de_guardar(sender, instance, **kwargs):
    """
    Valida que haya presupuesto suficiente antes de guardar un mantenimiento.
    Solo aplica para mantenimientos finalizados o que están siendo finalizados.
    """
    if instance.estado == 'Finalizado' and instance.costo_total_real > 0:
        if instance.cuenta_presupuestaria and instance.vehiculo:
            # Buscar presupuesto específico del vehículo
            presupuesto = Presupuesto.objects.filter(
                cuenta=instance.cuenta_presupuestaria,
                vehiculo=instance.vehiculo,
                anio=instance.fecha_ingreso.year,
                activo=True
            ).first()
            
            # Si no hay específico, buscar global
            if not presupuesto:
                presupuesto = Presupuesto.objects.filter(
                    cuenta=instance.cuenta_presupuestaria,
                    vehiculo__isnull=True,
                    anio=instance.fecha_ingreso.year,
                    activo=True
                ).first()
            
            if presupuesto:
                if not presupuesto.tiene_saldo_suficiente(instance.costo_total_real):
                    raise ValueError(
                        f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                        f"Requerido: ${instance.costo_total_real:.0f}"
                    )
            else:
                raise ValueError(
                    f"No hay presupuesto asignado para la cuenta {instance.cuenta_presupuestaria.codigo} "
                    f"en el año {instance.fecha_ingreso.year}"
                )

@receiver(post_save, sender=Mantenimiento)
@receiver(post_delete, sender=Mantenimiento)
def actualizar_presupuesto_mantenimiento(sender, instance, **kwargs):
    """
    Cuando se guarda/borra un mantenimiento, buscar el presupuesto asociado y recalcular.
    Solo para mantenimientos finalizados.
    """
    if instance.estado != 'Finalizado' or not instance.cuenta_presupuestaria:
        return

    # Buscar presupuesto compatible (mismo año, misma cuenta, mismo vehículo si aplica)
    anio = instance.fecha_ingreso.year
    
    # Intentar buscar presupuesto específico del vehículo
    presupuestos = Presupuesto.objects.filter(
        cuenta=instance.cuenta_presupuestaria,
        anio=anio,
        vehiculo=instance.vehiculo,
        activo=True
    )
    
    # Si no hay específico, buscar general (si aplica lógica de bolsa común)
    if not presupuestos.exists():
        presupuestos = Presupuesto.objects.filter(
            cuenta=instance.cuenta_presupuestaria,
            anio=anio,
            vehiculo__isnull=True,
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
    vehiculo = presupuesto.vehiculo
    total = Decimal(0)

    # 1. Sumar Mantenimientos FINALIZADOS
    filtros_mant = {
        'cuenta_presupuestaria': cuenta,
        'fecha_ingreso__year': anio,
        'estado': 'Finalizado'
    }
    
    if vehiculo:
        filtros_mant['vehiculo'] = vehiculo
    else:
        # Para presupuesto global, sumar mantenimientos de todos los vehículos
        pass
    
    gastos_mant = Mantenimiento.objects.filter(**filtros_mant).aggregate(
        total=Sum('costo_total_real')
    )['total'] or Decimal('0')
    total += gastos_mant

    # 2. Sumar Combustible
    filtros_comb = {
        'cuenta_presupuestaria': cuenta,
        'fecha__year': anio
    }
    if vehiculo:
        filtros_comb['patente_vehiculo'] = vehiculo
        
    gastos_comb = CargaCombustible.objects.filter(**filtros_comb).aggregate(
        total=Sum('costo_total')
    )['total'] or Decimal('0')
    total += gastos_comb

    # 3. Sumar Arriendos
    filtros_arriendo = {
        'cuenta_presupuestaria': cuenta,
        'fecha_inicio__year': anio,
        'estado': 'Activo'
    }
    if vehiculo:
        # Para presupuesto específico de vehículo, buscar arriendos donde este vehículo sea reemplazado
        filtros_arriendo['vehiculo_reemplazado'] = vehiculo
    
    gastos_arriendo = Arriendo.objects.filter(**filtros_arriendo).aggregate(
        total=Sum('costo_total')
    )['total'] or Decimal('0')
    total += gastos_arriendo

    # 4. Sumar Órdenes de Compra activas (no anuladas)
    # Las OCs representan compromisos presupuestarios
    from django.db.models import Q
    
    # Determinar vehículo para filtrar OCs
    if vehiculo:
        # Buscar OCs del vehículo específico (directamente o a través de OT)
        ocs = OrdenCompra.objects.filter(
            cuenta_presupuestaria=cuenta,
            fecha_emision__year=anio
        ).exclude(estado='Anulada').filter(
            Q(vehiculo=vehiculo) | Q(orden_trabajo__vehiculo=vehiculo)
        )
    else:
        # Para presupuesto global, sumar todas las OCs
        ocs = OrdenCompra.objects.filter(
            cuenta_presupuestaria=cuenta,
            fecha_emision__year=anio
        ).exclude(estado='Anulada')
    
    gastos_oc = ocs.aggregate(
        total=Sum('monto_total')
    )['total'] or Decimal('0')
    total += gastos_oc

    # Actualizar el presupuesto
    presupuesto.monto_ejecutado = total
    presupuesto.save(update_fields=['monto_ejecutado'])


@receiver(post_save, sender=OrdenCompra)
@receiver(post_delete, sender=OrdenCompra)
def actualizar_presupuesto_orden_compra(sender, instance, **kwargs):
    """
    Cuando se guarda/borra una OC, recalcular el presupuesto asociado.
    Las OCs representan compromisos presupuestarios.
    """
    if not instance.cuenta_presupuestaria:
        return
    
    # Determinar vehículo: desde orden_trabajo o directamente
    vehiculo_oc = instance.vehiculo
    if not vehiculo_oc and instance.orden_trabajo:
        vehiculo_oc = instance.orden_trabajo.vehiculo
    
    anio = instance.fecha_emision.year
    
    # Buscar presupuestos afectados
    presupuestos = Presupuesto.objects.filter(
        cuenta=instance.cuenta_presupuestaria,
        anio=anio,
        activo=True
    )
    
    if vehiculo_oc:
        # Buscar presupuesto específico del vehículo
        presupuestos = presupuestos.filter(vehiculo=vehiculo_oc)
        if not presupuestos.exists():
            # Si no hay específico, buscar global
            presupuestos = Presupuesto.objects.filter(
                cuenta=instance.cuenta_presupuestaria,
                anio=anio,
                vehiculo__isnull=True,
                activo=True
            )
    else:
        # Si no hay vehículo específico, afecta a presupuestos globales
        presupuestos = presupuestos.filter(vehiculo__isnull=True)
    
    for p in presupuestos:
        recalcular_monto_ejecutado(p)

    