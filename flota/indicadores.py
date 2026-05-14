"""
Indicadores del Plan Trienal (combustible, disponibilidad).
Consultas agrupadas por vehículo para evitar N+1 en reportes.
"""
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import (
    Count,
    ExpressionWrapper,
    F,
    IntegerField,
    Max,
    Min,
    Sum,
)

from .models import HojaRuta


def rango_fechas_reporte(anio, mes=None):
    """Período inclusivo [fecha_desde, fecha_hasta] según año y opcionalmente mes."""
    if mes and 1 <= int(mes) <= 12:
        mes = int(mes)
        ultimo = monthrange(anio, mes)[1]
        return date(anio, mes, 1), date(anio, mes, ultimo)
    return date(anio, 1, 1), date(anio, 12, 31)


def km_recorridos_desde_hojas(vehiculo_ids, fecha_desde, fecha_hasta):
    """Suma (km_fin - km_inicio) por vehículo en el período."""
    if not vehiculo_ids:
        return {}
    qs = HojaRuta.objects.filter(
        vehiculo_id__in=vehiculo_ids,
        fecha__gte=fecha_desde,
        fecha__lte=fecha_hasta,
        km_fin__isnull=False,
    ).values('vehiculo_id').annotate(
        km_sum=Sum(
            ExpressionWrapper(
                F('km_fin') - F('km_inicio'),
                output_field=IntegerField(),
            )
        )
    )
    return {row['vehiculo_id']: max(0, row['km_sum'] or 0) for row in qs}


def km_recorridos_fallback_cargas(vehiculo_ids, fecha_desde, fecha_hasta):
    """max(km carga) - min(km carga) por vehículo si hay cargas en el período."""
    if not vehiculo_ids:
        return {}
    from .models import CargaCombustible

    qs = (
        CargaCombustible.objects.filter(
            patente_vehiculo_id__in=vehiculo_ids,
            fecha__gte=fecha_desde,
            fecha__lte=fecha_hasta,
        )
        .values('patente_vehiculo_id')
        .annotate(mx=Max('kilometraje_al_cargar'), mn=Min('kilometraje_al_cargar'))
    )
    out = {}
    for row in qs:
        mx, mn = row['mx'], row['mn']
        if mx is not None and mn is not None:
            out[row['patente_vehiculo_id']] = max(0, mx - mn)
        else:
            out[row['patente_vehiculo_id']] = 0
    return out


def km_totales_por_vehiculo(vehiculo_ids, fecha_desde, fecha_hasta):
    """
    Km recorridos en el período: preferir suma de hojas de ruta;
    si es 0, usar diferencia de odómetro entre cargas de combustible.
    """
    desde_hojas = km_recorridos_desde_hojas(vehiculo_ids, fecha_desde, fecha_hasta)
    fallback = km_recorridos_fallback_cargas(vehiculo_ids, fecha_desde, fecha_hasta)
    result = {}
    for vid in vehiculo_ids:
        k = desde_hojas.get(vid, 0)
        if k < 1:
            k = fallback.get(vid, 0)
        result[vid] = k
    return result


def agregados_combustible_por_vehiculo(vehiculo_ids, fecha_desde, fecha_hasta):
    """litros y costo_total de CargaCombustible por vehículo."""
    if not vehiculo_ids:
        return {}
    from .models import CargaCombustible

    qs = (
        CargaCombustible.objects.filter(
            patente_vehiculo_id__in=vehiculo_ids,
            fecha__gte=fecha_desde,
            fecha__lte=fecha_hasta,
        )
        .values('patente_vehiculo_id')
        .annotate(litros=Sum('litros'), costo=Sum('costo_total'))
    )
    return {
        row['patente_vehiculo_id']: {
            'litros': row['litros'] or Decimal('0'),
            'costo': row['costo'] or 0,
        }
        for row in qs
    }


def indicadores_costos_combustible(vehiculo_ids, fecha_desde, fecha_hasta):
    """
    Por vehículo: rendimiento (km/l), costo combustible $/km, índice $/l efectivo.
    Valores None donde no aplica; strings para plantilla: 'Sin datos', 'N/A'.
    """
    km_map = km_totales_por_vehiculo(vehiculo_ids, fecha_desde, fecha_hasta)
    comb_map = agregados_combustible_por_vehiculo(vehiculo_ids, fecha_desde, fecha_hasta)
    out = {}
    for vid in vehiculo_ids:
        km = km_map.get(vid, 0)
        comb = comb_map.get(vid, {'litros': Decimal('0'), 'costo': 0})
        litros = comb['litros']
        costo = comb['costo']

        if litros is None or litros <= 0:
            out[vid] = {
                'rendimiento': 'Sin datos',
                'costo_combustible_km': 'N/A' if km < 1 else '-',
                'indice_eficiencia': 'Sin datos',
                '_rendimiento_num': None,
                '_costo_km_num': None,
            }
            continue

        rendimiento = float(km) / float(litros) if litros else 0.0
        costo_km = (Decimal(costo) / Decimal(km)) if km >= 1 else None
        indice = (costo_km * Decimal(str(rendimiento))) if costo_km is not None else None

        out[vid] = {
            'rendimiento': round(rendimiento, 2) if rendimiento else 'Sin datos',
            'costo_combustible_km': round(float(costo_km), 4) if costo_km is not None else 'N/A',
            'indice_eficiencia': round(float(indice), 2) if indice is not None else 'N/A',
            '_rendimiento_num': rendimiento,
            '_costo_km_num': float(costo_km) if costo_km is not None else None,
        }
    return out


def frecuencia_fallas_por_vehiculo(vehiculo_ids, fecha_desde, fecha_hasta):
    """
    (correctivos finalizados) / (km_totales / 10000). Solo mantenimientos con estado Finalizado.
    """
    from .models import Mantenimiento

    km_map = km_totales_por_vehiculo(vehiculo_ids, fecha_desde, fecha_hasta)
    if not vehiculo_ids:
        return {}

    corr_rows = (
        Mantenimiento.objects.filter(
            vehiculo_id__in=vehiculo_ids,
            tipo_mantencion='Correctivo',
            estado='Finalizado',
            fecha_ingreso__gte=fecha_desde,
            fecha_ingreso__lte=fecha_hasta,
        )
        .values('vehiculo_id')
        .annotate(n=Count('id'))
    )
    corr_map = {row['vehiculo_id']: row['n'] for row in corr_rows}

    out = {}
    for vid in vehiculo_ids:
        km = km_map.get(vid, 0)
        n = corr_map.get(vid, 0)
        if km < 1:
            out[vid] = 'N/A'
        else:
            val = (n / km) * 10000.0
            out[vid] = round(val, 6)
    return out


def promedio_dias_indisponibilidad_por_vehiculo(vehiculo_ids, fecha_desde, fecha_hasta):
    """Promedio de (fecha_salida - fecha_ingreso).days para mantenimientos finalizados."""
    from .models import Mantenimiento

    if not vehiculo_ids:
        return {}

    qs = Mantenimiento.objects.filter(
        vehiculo_id__in=vehiculo_ids,
        estado='Finalizado',
        fecha_salida__isnull=False,
        fecha_ingreso__gte=fecha_desde,
        fecha_ingreso__lte=fecha_hasta,
    ).values_list('vehiculo_id', 'fecha_ingreso', 'fecha_salida')

    sums = defaultdict(int)
    counts = defaultdict(int)
    for vid, fi, fs in qs:
        days = (fs - fi).days
        if days < 0:
            days = 0
        sums[vid] += days
        counts[vid] += 1

    out = {}
    for vid in vehiculo_ids:
        if counts[vid]:
            out[vid] = round(sums[vid] / counts[vid], 1)
        else:
            out[vid] = 'N/A'
    return out
