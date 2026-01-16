from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from .models import Mantenimiento, Presupuesto, CargaCombustible, Arriendo

def recalcular_monto_ejecutado(presupuesto):
    """
    Recalcula el total gastado para un presupuesto específico sumando
    Mantenimientos, Combustible y Arriendos asociados.
    """
    anio = presupuesto.anio
    cuenta = presupuesto.cuenta
    vehiculo = presupuesto.vehiculo
    total = Decimal(0)

    # 1. Sumar Mantenimientos (Preventivos y Correctivos asociados a esta cuenta)
    filtros_mant = {
        'cuenta_presupuestaria': cuenta,
        'fecha_ingreso__year': anio,
        'estado__in': ['Finalizado', 'Pagada'] # Solo sumar si ya se gastó
    }
    if vehiculo:
        filtros_mant['vehiculo'] = vehiculo
    
    # Si es presupuesto preventivo, filtrar solo mantenimientos preventivos
    # Si es operativo, incluimos correctivos
    if presupuesto.tipo_presupuesto == 'Preventivo':
        filtros_mant['tipo_mantencion'] = 'Preventivo'
    
    gastos_mant = Mantenimiento.objects.filter(**filtros_mant).aggregate(total=Sum('costo_total_real'))['total'] or 0
    total += gastos_mant

    # 2. Sumar Combustible (Solo si el presupuesto es Operativo/Combustible)
    filtros_comb = {
        'cuenta_presupuestaria': cuenta,
        'fecha__year': anio
    }
    if vehiculo:
        filtros_comb['patente_vehiculo'] = vehiculo
        
    gastos_comb = CargaCombustible.objects.filter(**filtros_comb).aggregate(total=Sum('costo_total'))['total'] or 0
    total += gastos_comb

    # 3. Sumar Arriendos (Solo si el presupuesto es Operativo/Arriendos)
    filtros_arriendo = {
        'cuenta_presupuestaria': cuenta,
        'fecha_inicio__year': anio
    }
    # Nota: Los arriendos suelen ser globales o por vehículo reemplazado, ajustar según lógica
    
    gastos_arriendo = Arriendo.objects.filter(**filtros_arriendo).aggregate(total=Sum('costo_total'))['total'] or 0
    total += gastos_arriendo

    # Actualizar el presupuesto
    presupuesto.monto_ejecutado = total
    presupuesto.save(update_fields=['monto_ejecutado'])

# --- TRIGGERS / SEÑALES ---

@receiver(post_save, sender=Mantenimiento)
@receiver(post_delete, sender=Mantenimiento)
def actualizar_presupuesto_mantenimiento(sender, instance, **kwargs):
    """
    Cuando se guarda/borra un mantenimiento, buscar el presupuesto asociado y recalcular.
    """
    if not instance.cuenta_presupuestaria:
        return

    # Buscar presupuesto compatible (mismo año, misma cuenta, mismo vehículo si aplica)
    anio = instance.fecha_ingreso.year
    
    # Intentar buscar presupuesto específico del vehículo
    presupuestos = Presupuesto.objects.filter(
        cuenta=instance.cuenta_presupuestaria,
        anio=anio,
        vehiculo=instance.vehiculo
    )
    
    # Si no hay específico, buscar general (si aplica lógica de bolsa común)
    if not presupuestos.exists():
        presupuestos = Presupuesto.objects.filter(
            cuenta=instance.cuenta_presupuestaria,
            anio=anio,
            vehiculo__isnull=True
        )

    for p in presupuestos:
        recalcular_monto_ejecutado(p)

@receiver(post_save, sender=CargaCombustible)
@receiver(post_delete, sender=CargaCombustible)
def actualizar_presupuesto_combustible(sender, instance, **kwargs):
    if instance.cuenta_presupuestaria:
        anio = instance.fecha.year
        # Buscar presupuestos que coincidan
        presupuestos = Presupuesto.objects.filter(
            cuenta=instance.cuenta_presupuestaria,
            anio=anio
        )
        for p in presupuestos:
            # Filtrar si el presupuesto es del vehículo o general
            if p.vehiculo == instance.patente_vehiculo or p.vehiculo is None:
                recalcular_monto_ejecutado(p)

@receiver(post_save, sender=Arriendo)
@receiver(post_delete, sender=Arriendo)
def actualizar_presupuesto_arriendo(sender, instance, **kwargs):
    if instance.cuenta_presupuestaria and instance.fecha_inicio:
        anio = instance.fecha_inicio.year
        presupuestos = Presupuesto.objects.filter(
            cuenta=instance.cuenta_presupuestaria,
            anio=anio,
            vehiculo__isnull=True # Arriendos suelen ir a presupuesto general
        )
        for p in presupuestos:
            recalcular_monto_ejecutado(p)

            