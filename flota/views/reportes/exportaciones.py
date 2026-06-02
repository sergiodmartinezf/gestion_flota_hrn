from decimal import Decimal
from datetime import datetime
from calendar import monthrange

from ...models import Vehiculo, Mantenimiento, Presupuesto, FallaReportada
from ...utils import exportar_reporte_excel, MESES
from ...indicadores import (
    frecuencia_fallas_por_vehiculo,
    indicadores_costos_combustible,
    promedio_dias_indisponibilidad_por_vehiculo,
    rango_fechas_reporte,
    km_totales_por_vehiculo,
)
from .calculos import ReporteCalculos, obtener_anios_disponibles_disponibilidad

def exportar_costos_excel(request):
    anio_str = request.GET.get('anio', str(datetime.now().year))
    try:
        anio_excel = int(anio_str)
    except (TypeError, ValueError):
        anio_excel = datetime.now().year
    fecha_desde, fecha_hasta = rango_fechas_reporte(anio_excel, None)

    vehiculos = Vehiculo.objects.all().order_by('patente')
    v_ids = [v.id for v in vehiculos]
    ind_map = indicadores_costos_combustible(v_ids, fecha_desde, fecha_hasta)
    km_periodo_map = km_totales_por_vehiculo(v_ids, fecha_desde, fecha_hasta)
    
    datos = []
    for vehiculo in vehiculos:
        calculos = ReporteCalculos.calcular_costos_vehiculo(vehiculo, fecha_desde, fecha_hasta)
        ind = ind_map.get(vehiculo.id, {})
        km_periodo = km_periodo_map.get(vehiculo.id, 0)
        costo_periodo_total = calculos['costo_total']
        costo_por_km_periodo = (costo_periodo_total / Decimal(km_periodo)) if km_periodo > 0 else Decimal('0')
        
        datos.append({
            'patente': vehiculo.patente,
            'costo_mantenimientos': calculos['costo_mantenimientos'],
            'costo_preventivo': calculos['costo_preventivo'],
            'costo_correctivo': calculos['costo_correctivo'],
            'costo_combustible': calculos['costo_combustible'],
            'costo_arriendos': calculos['costo_arriendos'],
            'costo_total': costo_periodo_total,
            'costo_por_km': costo_por_km_periodo,
            'rendimiento_km_l': ind.get('rendimiento', 'N/A'),
            'costo_combustible_km': ind.get('costo_combustible_km', 'N/A'),
            'indice_eficiencia': ind.get('indice_eficiencia', 'N/A'),
            'presupuesto': Presupuesto.objects.filter(activo=True).aggregate(total=Sum('monto_asignado'))['total'] or Decimal('0'),
        })

    columnas = [
        ('Vehículo', 'patente', 'texto'),
        ('Costo Mantenimientos', 'costo_mantenimientos', 'moneda'),
        ('Costo Preventivo', 'costo_preventivo', 'moneda'),
        ('Costo Correctivo', 'costo_correctivo', 'moneda'),
        ('Costo Combustible', 'costo_combustible', 'moneda'),
        ('Costo Arriendos', 'costo_arriendos', 'moneda'),
        ('Costo Total (período)', 'costo_total', 'moneda'),
        ('Costo por Km (período)', 'costo_por_km', 'decimal'),
        ('Rendimiento km/l (período)', 'rendimiento_km_l', 'texto'),
        ('Costo combustible $/km (período)', 'costo_combustible_km', 'texto'),
        ('Índice eficiencia $/L efectivo (período)', 'indice_eficiencia', 'texto'),
        ('Presupuesto', 'presupuesto', 'moneda'),
    ]
    
    return exportar_reporte_excel(
        f'Reporte de Costos por Vehículo - {anio_excel}',
        datos,
        columnas,
        f'reporte_costos_{anio_excel}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


def exportar_variacion_excel(anio, tipo_mantencion=None):
    reporte, _ = ReporteCalculos.calcular_variacion_anio(anio, tipo_mantencion)
    
    columnas = [
        ('Vehículo', 'vehiculo', 'texto'),
        ('Cuenta SIGFE', 'cuenta_sigfe', 'texto'),
        ('Monto Asignado', 'monto_asignado', 'moneda'),
        ('Monto Ejecutado', 'monto_ejecutado', 'moneda'),
        ('Diferencia', 'diferencia', 'moneda'),
        ('% Variación', 'porcentaje_variacion', 'decimal'),
        ('% Ejecutado', 'porcentaje_ejecutado', 'decimal'),
        ('Alerta', 'tiene_alerta', 'texto'),
    ]
    
    return exportar_reporte_excel(
        f'Reporte de Variación Presupuestaria {anio}',
        reporte,
        columnas,
        f'reporte_variacion_{anio}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


def exportar_disponibilidad_excel(request, anio_disp, mes_disp):
    """Exporta el reporte de disponibilidad a Excel con período en título y nombre."""
    from calendar import monthrange
    if mes_disp:
        dias_periodo = monthrange(anio_disp, mes_disp)[1]
        nombre_mes = f" - {MESES[mes_disp-1]}" if 'MESES' in globals() else f" - Mes {mes_disp}"
    else:
        dias_periodo = 366 if (anio_disp % 4 == 0 and (anio_disp % 100 != 0 or anio_disp % 400 == 0)) else 365
        nombre_mes = " (Año completo)"

    fecha_desde, fecha_hasta = rango_fechas_reporte(anio_disp, mes_disp)
    vehiculos = Vehiculo.objects.all().order_by('patente')
    v_ids = [v.id for v in vehiculos]
    frecuencia_map = frecuencia_fallas_por_vehiculo(v_ids, fecha_desde, fecha_hasta)
    indisp_prom_map = promedio_dias_indisponibilidad_por_vehiculo(v_ids, fecha_desde, fecha_hasta)

    datos = []
    for vehiculo in vehiculos:
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        if mes_disp:
            mantenimientos = mantenimientos.filter(fecha_ingreso__year=anio_disp, fecha_ingreso__month=mes_disp)
        else:
            mantenimientos = mantenimientos.filter(fecha_ingreso__year=anio_disp)

        total_dias_fuera = 0
        for mant in mantenimientos:
            if mant.fecha_salida:
                dias = (mant.fecha_salida - mant.fecha_ingreso).days
                total_dias_fuera += max(0, dias)

        incidentes = FallaReportada.objects.filter(vehiculo=vehiculo).count()
        dias_disponibles = max(0, dias_periodo - total_dias_fuera)

        datos.append({
            'patente': vehiculo.patente,
            'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
            'dias_fuera_servicio': total_dias_fuera,
            'dias_disponibles': dias_disponibles,
            'incidentes': incidentes,
            'frecuencia_fallas': frecuencia_map.get(vehiculo.id, 'N/A'),
            'promedio_indisponibilidad': indisp_prom_map.get(vehiculo.id, 'N/A'),
            'estado': vehiculo.get_estado_display(),
        })

    columnas = [
        ('Vehículo', 'patente', 'texto'),
        ('Marca/Modelo', 'marca_modelo', 'texto'),
        ('Días Fuera de Servicio', 'dias_fuera_servicio', 'entero'),
        ('Días Disponibles', 'dias_disponibles', 'entero'),
        ('Número de Incidentes', 'incidentes', 'entero'),
        ('Frec. fallas /10.000 km', 'frecuencia_fallas', 'texto'),
        ('Prom. días indisponibilidad', 'promedio_indisponibilidad', 'texto'),
        ('Estado Actual', 'estado', 'texto'),
    ]
    
    titulo = f'Reporte de Disponibilidad {anio_disp}{f" - Mes {mes_disp}" if mes_disp else ""}'
    nombre_archivo = f'reporte_disponibilidad_{anio_disp}'
    if mes_disp:
        nombre_archivo += f'_mes_{mes_disp}'
    nombre_archivo += f'_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return exportar_reporte_excel(titulo, datos, columnas, nombre_archivo)

