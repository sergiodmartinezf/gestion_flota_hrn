from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count
from decimal import Decimal
from calendar import monthrange
from datetime import datetime, timedelta
import json

from django.utils import timezone as tz
from ..models import Vehiculo, Mantenimiento, CargaCombustible, Arriendo, Presupuesto, FallaReportada, HojaRuta, Alerta, PacienteTraslado
from ..utils import exportar_reporte_excel, MESES
from ..indicadores import (
    frecuencia_fallas_por_vehiculo,
    indicadores_costos_combustible,
    promedio_dias_indisponibilidad_por_vehiculo,
    rango_fechas_reporte,
    km_totales_por_vehiculo,
)

from ..constants import MANTENIMIENTO_CUENTAS_MAP


def obtener_cuentas_por_tipo_mantencion(tipo_mantencion):
    """
    Retorna lista de IDs de CuentaPresupuestaria que corresponden al tipo de mantenimiento.
    Si tipo_mantencion es None o vacío, retorna todos los IDs (1,2,3,4).
    """
    if not tipo_mantencion:
        return [1, 2, 3, 4]
    
    cuentas_ids = set()
    for (tipo, _), ids in MANTENIMIENTO_CUENTAS_MAP.items():
        if tipo == tipo_mantencion:
            cuentas_ids.update(ids)
    return list(cuentas_ids)


class ReporteCalculos:
    """Cálculos compartidos entre exportación y vista HTML de reportes."""
    
    @staticmethod
    def calcular_costos_vehiculo(vehiculo, fecha_desde=None, fecha_hasta=None):
        """
        Calcula costos de mantenimiento, combustible y arriendos.
        Si se proporcionan fechas, filtra por ese período.
        """
        mantenimientos_qs = Mantenimiento.objects.filter(vehiculo=vehiculo)
        if fecha_desde:
            mantenimientos_qs = mantenimientos_qs.filter(fecha_ingreso__gte=fecha_desde)
        if fecha_hasta:
            mantenimientos_qs = mantenimientos_qs.filter(fecha_ingreso__lte=fecha_hasta)
        
        costo_mantenimientos = mantenimientos_qs.aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        costo_preventivo = mantenimientos_qs.filter(tipo_mantencion='Preventivo').aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        costo_correctivo = mantenimientos_qs.filter(tipo_mantencion='Correctivo').aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        
        cargas_qs = CargaCombustible.objects.filter(patente_vehiculo=vehiculo)
        if fecha_desde:
            cargas_qs = cargas_qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            cargas_qs = cargas_qs.filter(fecha__lte=fecha_hasta)
        costo_combustible = cargas_qs.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        arriendos_qs = Arriendo.objects.filter(vehiculo_reemplazado=vehiculo)
        costo_arriendos = Decimal('0')
        if fecha_desde and fecha_hasta:
            for arriendo in arriendos_qs:
                inicio = arriendo.fecha_inicio
                fin = arriendo.fecha_fin if arriendo.fecha_fin else fecha_hasta
                inter_inicio = max(inicio, fecha_desde)
                inter_fin = min(fin, fecha_hasta)
                if inter_fin >= inter_inicio:
                    dias_intersec = (inter_fin - inter_inicio).days + 1
                    if arriendo.costo_diario:
                        costo_arriendos += arriendo.costo_diario * dias_intersec
                    elif arriendo.dias_arriendo > 0:
                        costo_arriendos += (arriendo.costo_total / arriendo.dias_arriendo) * dias_intersec
        else:
            costo_arriendos = arriendos_qs.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        costo_total = costo_mantenimientos + costo_combustible + costo_arriendos
        
        return {
            'vehiculo': vehiculo,
            'costo_mantenimientos': costo_mantenimientos,
            'costo_preventivo': costo_preventivo,
            'costo_correctivo': costo_correctivo,
            'costo_combustible': costo_combustible,
            'costo_arriendos': costo_arriendos,
            'costo_total': costo_total,
        }


    @staticmethod
    def calcular_costos_combustible_avanzado(vehiculo, fecha_desde, fecha_hasta):
        """
        Retorna total litros y costo por litro para un vehículo en el período.
        """
        from decimal import Decimal
        cargas = CargaCombustible.objects.filter(
            patente_vehiculo=vehiculo,
            fecha__gte=fecha_desde,
            fecha__lte=fecha_hasta
        )
        total_litros = cargas.aggregate(total=Sum('litros'))['total'] or Decimal('0')
        total_costo = cargas.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        costo_por_litro = (total_costo / total_litros) if total_litros > 0 else None
        return {
            'total_litros': float(total_litros),
            'costo_por_litro': float(costo_por_litro) if costo_por_litro is not None else None,
        }

    @staticmethod
    def calcular_tiempo_mantenimiento(vehiculo, fecha_desde, fecha_hasta):
        """
        Calcula horas totales en mantenimiento y costo por hora detenida.
        Solo considera mantenimientos finalizados con fecha_salida.
        """
        from decimal import Decimal
        mants = Mantenimiento.objects.filter(
            vehiculo=vehiculo,
            fecha_ingreso__gte=fecha_desde,
            fecha_ingreso__lte=fecha_hasta,
            estado='Finalizado',
            fecha_salida__isnull=False
        )
        horas_totales = 0
        costo_total = Decimal('0')
        for mant in mants:
            delta = mant.fecha_salida - mant.fecha_ingreso
            horas_totales += delta.days * 24 + (delta.seconds // 3600)
            costo_total += mant.costo_total_real or Decimal('0')
        costo_por_hora = (costo_total / horas_totales) if horas_totales > 0 else None
        return {
            'horas_mantenimiento': horas_totales,
            'costo_mantenimiento_total': float(costo_total),
            'costo_por_hora_mantenimiento': float(costo_por_hora) if costo_por_hora is not None else None,
        }


    @staticmethod
    def calcular_variacion_anio(anio, tipo_mantencion=None):
        """
        Variación presupuestaria por año.
        tipo_mantencion: 'Preventivo', 'Correctivo' o None (filtra cuentas y mantenimientos).
        """
        cuentas_ids = obtener_cuentas_por_tipo_mantencion(tipo_mantencion)
        presupuestos = Presupuesto.objects.filter(anio=anio, cuenta_id__in=cuentas_ids).select_related('cuenta')
        
        reporte = []
        alertas = []

        for presupuesto in presupuestos:
            filtros = {
                'cuenta_presupuestaria': presupuesto.cuenta,
                'fecha_ingreso__year': anio,
                'estado': 'Finalizado'
            }
            if tipo_mantencion:
                filtros['tipo_mantencion'] = tipo_mantencion

            monto_ejecutado = Mantenimiento.objects.filter(**filtros).aggregate(
                total=Sum('costo_total_real')
            )['total'] or Decimal('0')

            diferencia = monto_ejecutado - presupuesto.monto_asignado
            porcentaje_variacion = (diferencia / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
            tiene_alerta = porcentaje_variacion > 10

            item = {
                'vehiculo': 'Flota General',
                'marca_modelo': 'N/A',
                'cuenta_sigfe': presupuesto.cuenta.codigo,
                'nombre_cuenta': presupuesto.cuenta.nombre,
                'monto_asignado': presupuesto.monto_asignado,
                'monto_ejecutado': monto_ejecutado,
                'diferencia': diferencia,
                'porcentaje_variacion': porcentaje_variacion,
                'porcentaje_ejecutado': (monto_ejecutado / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0,
                'tiene_alerta': tiene_alerta,
                'activo': presupuesto.activo,
            }
            reporte.append(item)
            if tiene_alerta:
                alertas.append(item)

        return reporte, alertas
    
    @staticmethod
    def obtener_datos_graficos_costos(fecha_desde=None, fecha_hasta=None):
        vehiculos = Vehiculo.objects.all()
        datos = {
            'patentes': [],
            'costos_mantenimiento': [],
            'costos_combustible': [],
            'costos_arriendo': [],
            'costos_totales': [],
            'dias_fuera_servicio': []
        }
        for vehiculo in vehiculos:
            calculos = ReporteCalculos.calcular_costos_vehiculo(vehiculo, fecha_desde, fecha_hasta)
            datos['patentes'].append(vehiculo.patente)
            datos['costos_mantenimiento'].append(float(calculos['costo_mantenimientos']))
            datos['costos_combustible'].append(float(calculos['costo_combustible']))
            datos['costos_arriendo'].append(float(calculos['costo_arriendos']))
            datos['costos_totales'].append(float(calculos['costo_total']))
            
            total_dias = 0
            mantenimientos = vehiculo.mantenimientos.all()
            if fecha_desde:
                mantenimientos = mantenimientos.filter(fecha_ingreso__gte=fecha_desde)
            if fecha_hasta:
                mantenimientos = mantenimientos.filter(fecha_ingreso__lte=fecha_hasta)
            for mant in mantenimientos:
                if mant.fecha_salida:
                    total_dias += (mant.fecha_salida - mant.fecha_ingreso).days
            datos['dias_fuera_servicio'].append(total_dias)
        return datos


class TabManager:
    """Estado de pestañas vía query string."""
    
    def __init__(self, request):
        self.active = request.GET.get('tab', 'costos')
        self.request = request
    
    def is_active(self, tab_name):
        return self.active == tab_name
    
    def url(self, tab_name, **params):
        """Genera URL para pestaña manteniendo parámetros"""
        from django.http import QueryDict
        query_dict = self.request.GET.copy()
        query_dict['tab'] = tab_name
        for key, value in params.items():
            if value is None:
                query_dict.pop(key, None)
            else:
                query_dict[key] = value
        return f"?{query_dict.urlencode()}"


def obtener_anios_disponibles_disponibilidad():
    """
    Retorna lista de años únicos ordenados descendente que tengan
    al menos un mantenimiento o falla reportada.
    """
    years_mant = Mantenimiento.objects.dates('fecha_ingreso', 'year').values_list('fecha_ingreso__year', flat=True).distinct()
    years_falla = FallaReportada.objects.dates('fecha_reporte', 'year').values_list('fecha_reporte__year', flat=True).distinct()
    anios = sorted(set(list(years_mant) + list(years_falla)), reverse=True)
    if not anios:
        anios = [datetime.now().year]  # sin registros: permite filtrar por año corriente
    return anios


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


@login_required
def reportes(request):
    """Reportes: costos, variación presupuestaria y disponibilidad (HTML o Excel)."""
    if request.GET.get('exportar') == 'excel':
        tab = request.GET.get('tab', 'costos')
        if tab == 'variacion':
            anio_str = request.GET.get('anio', str(datetime.now().year))
            import re
            anio_limpio = re.sub(r'\D', '', anio_str)
            if not anio_limpio:
                anio_limpio = str(datetime.now().year)
            anio = int(anio_limpio)
            tipo_mant = request.GET.get('tipo_mantencion', '')
            return exportar_variacion_excel(anio, tipo_mant if tipo_mant else None)
        elif tab == 'disponibilidad':
            anio_disp = request.GET.get('anio_disp', str(datetime.now().year))
            mes_disp = request.GET.get('mes_disp')
            try:
                anio_disp = int(anio_disp)
            except ValueError:
                anio_disp = datetime.now().year
            if mes_disp and str(mes_disp).isdigit():
                mes_disp = int(mes_disp)
            else:
                mes_disp = None
            return exportar_disponibilidad_excel(request, anio_disp, mes_disp)
        else:
            return exportar_costos_excel(request)

    active_tab = request.GET.get('tab', 'costos')
    tab_manager = TabManager(request)

    anios_disponibles = sorted(Presupuesto.objects.values_list('anio', flat=True).distinct(), reverse=True)
    if not anios_disponibles:
        anios_disponibles = [datetime.now().year]

    try:
        anio_costos = int(request.GET.get('anio', anios_disponibles[0]))
    except (TypeError, ValueError):
        anio_costos = anios_disponibles[0]
    if anio_costos not in anios_disponibles:
        anio_costos = anios_disponibles[0]

    fecha_desde_c, fecha_hasta_c = rango_fechas_reporte(anio_costos, None)

    vehiculos = Vehiculo.objects.all().order_by('patente')
    v_ids = [v.id for v in vehiculos]
    ind_costos_map = indicadores_costos_combustible(v_ids, fecha_desde_c, fecha_hasta_c)
    km_periodo_map = km_totales_por_vehiculo(v_ids, fecha_desde_c, fecha_hasta_c)
    
    reporte_costos_data = []
    for vehiculo in vehiculos:
        calculos = ReporteCalculos.calcular_costos_vehiculo(vehiculo, fecha_desde_c, fecha_hasta_c)
        ind_c = ind_costos_map.get(vehiculo.id, {})
        km_periodo = km_periodo_map.get(vehiculo.id, 0)
        
        comb_avanzado = ReporteCalculos.calcular_costos_combustible_avanzado(vehiculo, fecha_desde_c, fecha_hasta_c)
        tiempos_mant = ReporteCalculos.calcular_tiempo_mantenimiento(vehiculo, fecha_desde_c, fecha_hasta_c)
        
        costo_total_sin_arriendo = calculos['costo_mantenimientos'] + calculos['costo_combustible']

        if km_periodo > 0:
            km = Decimal(km_periodo)
            costo_mant_por_km = calculos['costo_mantenimientos'] / km
            costo_preventivo_km = calculos['costo_preventivo'] / km
            costo_correctivo_km = calculos['costo_correctivo'] / km
            costo_total_km_sin_arriendo = costo_total_sin_arriendo / km
            costo_total_con_arriendos_km = calculos['costo_total'] / km
        else:
            costo_mant_por_km = None
            costo_preventivo_km = None
            costo_correctivo_km = None
            costo_total_km_sin_arriendo = None
            costo_total_con_arriendos_km = None
        
        reporte_costos_data.append({
            'vehiculo': vehiculo,
            'patente': vehiculo.patente,
            'km_periodo': km_periodo,
            'costo_combustible': calculos['costo_combustible'],
            'rendimiento_km_l': ind_c.get('rendimiento', '—'),
            'costo_combustible_km': ind_c.get('costo_combustible_km', 'N/A'),
            'costo_por_litro': comb_avanzado['costo_por_litro'],
            'total_litros': comb_avanzado['total_litros'],
            'costo_preventivo': calculos['costo_preventivo'],
            'costo_correctivo': calculos['costo_correctivo'],
            'costo_mantenimiento_total': calculos['costo_mantenimientos'],
            'costo_mant_por_km': float(costo_mant_por_km) if costo_mant_por_km is not None else None,
            'costo_preventivo_km': float(costo_preventivo_km) if costo_preventivo_km is not None else None,
            'costo_correctivo_km': float(costo_correctivo_km) if costo_correctivo_km is not None else None,
            'costo_arriendos': calculos['costo_arriendos'],
            'costo_total_combustible_mantenciones': float(costo_total_sin_arriendo),
            'costo_total_combustible_mantenciones_km': float(costo_total_km_sin_arriendo) if costo_total_km_sin_arriendo is not None else None,
            'horas_mantenimiento': tiempos_mant['horas_mantenimiento'],
            'costo_por_hora_mantenimiento': tiempos_mant['costo_por_hora_mantenimiento'],
            'costo_total_con_arriendos': calculos['costo_total'],
            'costo_total_con_arriendos_km': float(costo_total_con_arriendos_km) if costo_total_con_arriendos_km is not None else None,
        })

    patentes_list = [item['patente'] for item in reporte_costos_data]
    rendimientos_list = [float(item['rendimiento_km_l']) if item['rendimiento_km_l'] not in ('—','N/A','Sin datos') else 0 for item in reporte_costos_data]
    costo_por_litro_list = [item['costo_por_litro'] if item['costo_por_litro'] is not None else 0 for item in reporte_costos_data]
    costo_preventivo_km_list = [item['costo_preventivo_km'] for item in reporte_costos_data]
    costo_correctivo_km_list = [item['costo_correctivo_km'] for item in reporte_costos_data]

    anio = request.GET.get('anio')
    try:
        anio = int(anio) if anio else anios_disponibles[0]
    except ValueError:
        anio = anios_disponibles[0]

    if anio not in anios_disponibles:
        anio = anios_disponibles[0]

    tipo_mant = request.GET.get('tipo_mantencion', '')
    vehiculo_filter = request.GET.get('vehiculo', '')
    
    reporte_variacion, alertas_variacion = ReporteCalculos.calcular_variacion_anio(anio, tipo_mantencion=tipo_mant if tipo_mant else None)

    datos_graficos = ReporteCalculos.obtener_datos_graficos_costos(fecha_desde_c, fecha_hasta_c)
    graficos_json = json.dumps(datos_graficos)

    anios_disponibles_disp = obtener_anios_disponibles_disponibilidad()
    anio_disp = request.GET.get('anio_disp')
    try:
        anio_disp = int(anio_disp) if anio_disp else anios_disponibles_disp[0]
    except (TypeError, ValueError):
        anio_disp = anios_disponibles_disp[0]

    if anio_disp not in anios_disponibles_disp:
        anio_disp = anios_disponibles_disp[0]

    mes_disp = request.GET.get('mes_disp')
    if mes_disp and mes_disp.isdigit():
        mes_disp = int(mes_disp)
        if not (1 <= mes_disp <= 12):
            mes_disp = None
    else:
        mes_disp = None

    if mes_disp:
        dias_periodo = monthrange(anio_disp, mes_disp)[1]
    else:
        dias_periodo = 366 if (anio_disp % 4 == 0 and (anio_disp % 100 != 0 or anio_disp % 400 == 0)) else 365

    fecha_desde_disp, fecha_hasta_disp = rango_fechas_reporte(anio_disp, mes_disp)
    vehiculos_disp = Vehiculo.objects.all().order_by('patente')
    v_ids_disp = [v.id for v in vehiculos_disp]
    frecuencia_map = frecuencia_fallas_por_vehiculo(v_ids_disp, fecha_desde_disp, fecha_hasta_disp)
    indisp_prom_map = promedio_dias_indisponibilidad_por_vehiculo(v_ids_disp, fecha_desde_disp, fecha_hasta_disp)
    tiempos_hbo = calcular_tiempos_retencion_hbo(v_ids_disp, fecha_desde_disp, fecha_hasta_disp)

    reporte_disponibilidad = []
    for vehiculo in vehiculos_disp:
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        if mes_disp:
            mantenimientos = mantenimientos.filter(fecha_ingreso__year=anio_disp, fecha_ingreso__month=mes_disp)
        else:
            mantenimientos = mantenimientos.filter(fecha_ingreso__year=anio_disp)

        total_dias_fuera = 0
        correctivos = Mantenimiento.objects.filter(
            vehiculo=vehiculo,
            tipo_mantencion='Correctivo',
            estado='Finalizado',
            fecha_ingreso__gte=fecha_desde_disp,
            fecha_ingreso__lte=fecha_hasta_disp
        ).count()

        km_periodo_vehiculo = km_totales_por_vehiculo([vehiculo.id], fecha_desde_disp, fecha_hasta_disp).get(vehiculo.id, 0)

        for mant in mantenimientos:
            if mant.fecha_salida:
                dias = (mant.fecha_salida - mant.fecha_ingreso).days
                total_dias_fuera += max(0, dias)

        incidentes = FallaReportada.objects.filter(vehiculo=vehiculo).count()
        dias_disponibles = max(0, dias_periodo - total_dias_fuera)

        tiempo_hbo = tiempos_hbo.get(vehiculo.id)
        tiempo_hbo_formateado = f"{tiempo_hbo:.0f} min" if tiempo_hbo is not None else "N/D"

        reporte_disponibilidad.append({
            'vehiculo': vehiculo,
            'patente': vehiculo.patente,
            'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
            'dias_fuera_servicio': total_dias_fuera,
            'dias_disponibles': dias_disponibles,
            'dias_periodo': dias_periodo,
            'incidentes': incidentes,
            'estado': vehiculo.get_estado_display(),
            'frecuencia_fallas': frecuencia_map.get(vehiculo.id, 'N/A'),
            'promedio_indisponibilidad': indisp_prom_map.get(vehiculo.id, 'N/A'),
            'tiempo_hbo': tiempo_hbo_formateado,
            'correctivos': correctivos,
            'km_periodo': km_periodo_vehiculo,
        })

    patentes_disp_list = []
    frecuencias_list = []
    promedios_list = []
    tiempos_hbo_list = []

    for item in reporte_disponibilidad:
        patentes_disp_list.append(item['patente'])

        freq = item['frecuencia_fallas']
        if freq != 'N/A' and freq is not None:
            try:
                frecuencias_list.append(float(freq))
            except (ValueError, TypeError):
                frecuencias_list.append(None)
        else:
            frecuencias_list.append(None)

        prom = item['promedio_indisponibilidad']
        if prom != 'N/A' and prom is not None:
            try:
                promedios_list.append(float(prom))
            except (ValueError, TypeError):
                promedios_list.append(None)
        else:
            promedios_list.append(None)

        tiempo_str = item['tiempo_hbo']
        if tiempo_str and tiempo_str != 'N/D' and 'min' in tiempo_str:
            try:
                minutos = int(tiempo_str.split()[0])
                tiempos_hbo_list.append(minutos)
            except (ValueError, IndexError):
                tiempos_hbo_list.append(None)
        else:
            tiempos_hbo_list.append(None)

    patentes_disp = [item['patente'] for item in reporte_disponibilidad]
    dias_fuera_disp = [item['dias_fuera_servicio'] for item in reporte_disponibilidad]
    pares = sorted(zip(patentes_disp, dias_fuera_disp), key=lambda x: x[1], reverse=True)
    patentes_disp_ordenadas, dias_fuera_disp_ordenadas = zip(*pares) if pares else ([], [])
    
    disponibilidad_global = calcular_disponibilidad_global(vehiculos_disp, fecha_desde_disp, fecha_hasta_disp, dias_periodo)
    dias_fuera_mensual = calcular_dias_fuera_por_mes(vehiculos_disp, anio_disp)

    disponibilidad_global_json = json.dumps(disponibilidad_global)
    dias_fuera_mensual_json = json.dumps(dias_fuera_mensual)

    return render(request, 'flota/reportes.html', {
        'reporte': reporte_costos_data,
        'reporte_variacion': reporte_variacion,
        'alertas_variacion': alertas_variacion,
        'anio': anio,
        'anio_costos': anio_costos,
        'anios_disponibles': anios_disponibles,
        'active_tab': active_tab,
        'tab_manager': tab_manager,
        'graficos_json': graficos_json,
        'tipo_mantencion': tipo_mant,
        'vehiculos': vehiculos,
        'vehiculo_filter': vehiculo_filter,
        'reporte_disponibilidad': reporte_disponibilidad,
        'anios_disponibles_disp': anios_disponibles_disp,
        'anio_disp': anio_disp,
        'mes_disp': mes_disp,
        'dias_periodo_disp': dias_periodo,
        'patentes_list': patentes_list,
        'rendimientos_list': rendimientos_list,
        'costo_por_litro_list': costo_por_litro_list,
        'costo_preventivo_km_list': costo_preventivo_km_list,
        'costo_correctivo_km_list': costo_correctivo_km_list,
        'disponibilidad_global_json': disponibilidad_global_json,
        'dias_fuera_mensual_json': dias_fuera_mensual_json,
        'patentes_disp': list(patentes_disp_ordenadas),
        'dias_fuera_disp': list(dias_fuera_disp_ordenadas),
        'patentes_disp_list_json': json.dumps(patentes_disp_list),
        'frecuencias_list_json': json.dumps(frecuencias_list),
        'promedios_list_json': json.dumps(promedios_list),
        'tiempos_hbo_list_json': json.dumps(tiempos_hbo_list),
    })
    

# RF_25: Generar reporte de disponibilidad (disponibilidad efectiva: días disponibles en período)
@login_required
def reporte_disponibilidad(request):
    from calendar import monthrange
    vehiculos = Vehiculo.objects.all()
    anio = request.GET.get('anio')
    mes = request.GET.get('mes')
    if anio:
        try:
            anio = int(anio)
        except ValueError:
            anio = datetime.now().year
    else:
        anio = datetime.now().year
    mes = int(mes) if mes and str(mes).isdigit() and 1 <= int(mes) <= 12 else None
    
    if mes:
        dias_periodo = monthrange(anio, mes)[1]
    else:
        dias_periodo = 366 if (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)) else 365
    
    fecha_desde_d, fecha_hasta_d = rango_fechas_reporte(anio, mes)
    v_ids = list(vehiculos.values_list('id', flat=True))
    frecuencia_map = frecuencia_fallas_por_vehiculo(v_ids, fecha_desde_d, fecha_hasta_d)
    indisp_prom_map = promedio_dias_indisponibilidad_por_vehiculo(v_ids, fecha_desde_d, fecha_hasta_d)

    reporte = []
    for vehiculo in vehiculos:
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        if mes:
            mantenimientos = mantenimientos.filter(
                fecha_ingreso__year=anio, fecha_ingreso__month=mes
            )
        else:
            mantenimientos = mantenimientos.filter(fecha_ingreso__year=anio)
        
        total_dias_fuera = 0
        for mant in mantenimientos:
            if mant.fecha_salida:
                dias = (mant.fecha_salida - mant.fecha_ingreso).days
                total_dias_fuera += max(0, dias)
        
        incidentes = FallaReportada.objects.filter(vehiculo=vehiculo).count()
        dias_disponibles = max(0, dias_periodo - total_dias_fuera)
        
        reporte.append({
            'patente': vehiculo.patente,
            'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
            'dias_fuera_servicio': total_dias_fuera,
            'dias_disponibles': dias_disponibles,
            'dias_periodo': dias_periodo,
            'incidentes': incidentes,
            'estado': vehiculo.get_estado_display(),
            'vehiculo': vehiculo,
            'frecuencia_fallas': frecuencia_map.get(vehiculo.id, 'N/A'),
            'promedio_indisponibilidad': indisp_prom_map.get(vehiculo.id, 'N/A'),
        })
    
    if request.GET.get('exportar') == 'excel':
        columnas = [
            ('Vehículo', 'patente', 'texto'),
            ('Marca/Modelo', 'marca_modelo', 'texto'),
            ('Días Fuera de Servicio', 'dias_fuera_servicio', 'entero'),
            ('Días Disponibles (disponibilidad efectiva)', 'dias_disponibles', 'entero'),
            ('Número de Incidentes', 'incidentes', 'entero'),
            ('Frec. fallas /10.000 km', 'frecuencia_fallas', 'texto'),
            ('Prom. días indisponibilidad', 'promedio_indisponibilidad', 'texto'),
            ('Estado Actual', 'estado', 'texto'),
        ]
        return exportar_reporte_excel(
            'Reporte de Disponibilidad de Flota',
            reporte,
            columnas,
            f'reporte_disponibilidad_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    
    return render(request, 'flota/reporte_disponibilidad.html', {
        'reporte': reporte,
        'anio': anio,
        'mes': mes,
        'dias_periodo': dias_periodo,
    })


# RF_28: Generar reporte de historial por unidad
@login_required
def reporte_historial_unidad(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    filtros = {'vehiculo': vehiculo}
    filtros_combustible = {'patente_vehiculo': vehiculo}
    filtros_hoja = {'vehiculo': vehiculo}
    
    if fecha_inicio:
        filtros['fecha_ingreso__gte'] = fecha_inicio
        filtros_combustible['fecha__gte'] = fecha_inicio
        filtros_hoja['fecha__gte'] = fecha_inicio
    
    if fecha_fin:
        filtros['fecha_ingreso__lte'] = fecha_fin
        filtros_combustible['fecha__lte'] = fecha_fin
        filtros_hoja['fecha__lte'] = fecha_fin
    
    mantenimientos = Mantenimiento.objects.filter(**filtros).order_by('-fecha_ingreso')
    cargas_combustible = CargaCombustible.objects.filter(**filtros_combustible).order_by('-fecha')
    hojas_ruta = HojaRuta.objects.filter(**filtros_hoja).order_by('-fecha')
    incidentes = FallaReportada.objects.filter(vehiculo=vehiculo).order_by('-fecha_reporte')
    
    return render(request, 'flota/reporte_historial_unidad.html', {
        'vehiculo': vehiculo,
        'mantenimientos': mantenimientos,
        'cargas_combustible': cargas_combustible,
        'hojas_ruta': hojas_ruta,
        'incidentes': incidentes,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })


def calcular_tiempos_retencion_hbo(vehiculo_ids, fecha_desde, fecha_hasta):
    """
    Retorna un diccionario {vehiculo_id: minutos_promedio_en_HBO}
    para cada vehículo en el período.
    """
    from ..models import Viaje
    resultados = {}
    for vid in vehiculo_ids:
        viajes = Viaje.objects.filter(
            hoja_ruta__vehiculo_id=vid,
            hora_salida_hbo__isnull=False,
            hora_llegada_hbo__isnull=False,
            hoja_ruta__fecha__gte=fecha_desde,
            hoja_ruta__fecha__lte=fecha_hasta
        )
        total_minutos = 0
        count = 0
        for viaje in viajes:
            fecha = viaje.hoja_ruta.fecha
            salida = datetime.combine(fecha, viaje.hora_salida_hbo)
            llegada = datetime.combine(fecha, viaje.hora_llegada_hbo)
            if llegada < salida:
                llegada += timedelta(days=1)
            minutos = (llegada - salida).total_seconds() / 60
            total_minutos += minutos
            count += 1
        promedio = (total_minutos / count) if count > 0 else None
        resultados[vid] = promedio
    return resultados


@login_required
def reporte_servicios(request):
    servicios = PacienteTraslado.objects.values('prevision').annotate(
        total=Count('id')
    ).order_by('-total')

    labels = []
    data = []
    for s in servicios:
        prev = s['prevision'] or 'Sin especificar'
        labels.append(prev)
        data.append(s['total'])
    
    return render(request, 'flota/reporte_servicios.html', {
        'servicios': [{'prevision': labels[i], 'total': data[i]} for i in range(len(labels))],
        'chart_labels': labels,
        'chart_data': data
    })


def calcular_disponibilidad_global(vehiculos, fecha_desde, fecha_hasta, dias_periodo):
    total_dias_posibles = dias_periodo * vehiculos.count()
    total_dias_fuera = 0
    for v in vehiculos:
        mants = Mantenimiento.objects.filter(
            vehiculo=v,
            fecha_ingreso__gte=fecha_desde,
            fecha_ingreso__lte=fecha_hasta,
            estado='Finalizado',
            fecha_salida__isnull=False
        )
        for m in mants:
            total_dias_fuera += max(0, (m.fecha_salida - m.fecha_ingreso).days)
    disponibilidad = max(0, total_dias_posibles - total_dias_fuera)
    porcentaje = (disponibilidad / total_dias_posibles * 100) if total_dias_posibles > 0 else 0
    return {
        'total_dias_posibles': total_dias_posibles,
        'total_dias_fuera': total_dias_fuera,
        'dias_disponibles': disponibilidad,
        'porcentaje_disponibilidad': round(porcentaje, 2),
    }


def calcular_dias_fuera_por_mes(vehiculos, anio):
    """
    Retorna una lista de 12 elementos con la suma de días fuera de servicio
    cuyos mantenimientos comenzaron en cada mes del año.
    """
    meses_dias = [0] * 12
    for v in vehiculos:
        mants = Mantenimiento.objects.filter(
            vehiculo=v,
            fecha_ingreso__year=anio,
            estado='Finalizado',
            fecha_salida__isnull=False
        )
        for m in mants:
            duracion = max(0, (m.fecha_salida - m.fecha_ingreso).days)
            mes_idx = m.fecha_ingreso.month - 1
            meses_dias[mes_idx] += duracion
    return meses_dias
