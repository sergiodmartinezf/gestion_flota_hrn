from django.utils import timezone

from ..models import Alerta, Mantenimiento, Presupuesto

UMBRAL_ALERTA_PRESUPUESTO = 80


def _ids_alertas_pausadas():
    ids_pausadas = set()
    for alerta in Alerta.objects.filter(vigente=True).select_related('vehiculo'):
        if alerta.vehiculo.estado == 'En mantenimiento' and Mantenimiento.objects.filter(
            vehiculo=alerta.vehiculo,
            estado__in=['En taller', 'Esperando repuestos'],
            fecha_salida__isnull=True,
        ).exists():
            ids_pausadas.add(alerta.id)
    return ids_pausadas


def alertas_mantenimiento_vigentes():
    return Alerta.objects.filter(vigente=True).exclude(
        id__in=_ids_alertas_pausadas()
    ).select_related('vehiculo').order_by('-generado_en')


def presupuestos_con_alerta():
    return [
        presupuesto for presupuesto in Presupuesto.objects.filter(
            activo=True,
            alerta_presupuesto_ignorada=False,
        ).exclude(monto_asignado=0).select_related('cuenta')
        if presupuesto.porcentaje_ejecutado >= UMBRAL_ALERTA_PRESUPUESTO
    ]


def contar_alertas_vigentes():
    count_mant = alertas_mantenimiento_vigentes().count()
    count_presupuesto = len(presupuestos_con_alerta())
    return {
        'count': count_mant + count_presupuesto,
        'mantenimiento': count_mant,
        'presupuesto': count_presupuesto,
    }


def resolver_alerta_mantenimiento(alerta):
    alerta.vigente = False
    alerta.resuelta_en = timezone.now()
    alerta.save(update_fields=['vigente', 'resuelta_en'])


def ignorar_alerta_presupuesto(presupuesto):
    presupuesto.alerta_presupuesto_ignorada = True
    presupuesto.save(update_fields=['alerta_presupuesto_ignorada'])
