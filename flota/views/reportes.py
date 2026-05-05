from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count
from decimal import Decimal
from calendar import monthrange
from datetime import datetime
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
        # Todos los IDs posibles (según tu mapeo)
        return [1, 2, 3, 4]
    
    cuentas_ids = set()
    for (tipo, _), ids in MANTENIMIENTO_CUENTAS_MAP.items():
        if tipo == tipo_mantencion:
            cuentas_ids.update(ids)
    return list(cuentas_ids)


class ReporteCalculos:
    """Clase para cálculos reutilizables"""
    
    @staticmethod
    def calcular_costos_vehiculo(vehiculo, fecha_desde=None, fecha_hasta=None):
        """
        Calcula costos de mantenimiento, combustible y arriendos.
        Si se proporcionan fechas, filtra por ese período.
        """
        # Mantenimientos
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
        
        # Combustible
        cargas_qs = CargaCombustible.objects.filter(patente_vehiculo=vehiculo)
        if fecha_desde:
            cargas_qs = cargas_qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            cargas_qs = cargas_qs.filter(fecha__lte=fecha_hasta)
        costo_combustible = cargas_qs.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        # Arriendos (vehículo reemplazado)
        arriendos_qs = Arriendo.objects.filter(vehiculo_reemplazado=vehiculo)
        if fecha_desde:
            arriendos_qs = arriendos_qs.filter(fecha_inicio__gte=fecha_desde)
        if fecha_hasta:
            arriendos_qs = arriendos_qs.filter(fecha_inicio__lte=fecha_hasta)
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
    def calcular_variacion_anio(anio, tipo_mantencion=None):
        """
        Calcula la variación presupuestaria para un año dado.
        tipo_mantencion puede ser 'Preventivo', 'Correctivo' o None (ambos).
        Ahora filtra los presupuestos según el tipo, mostrando solo las cuentas correspondientes.
        """
        # 1. Obtener IDs de cuentas según el tipo de mantenimiento
        cuentas_ids = obtener_cuentas_por_tipo_mantencion(tipo_mantencion)
        
        # 2. Filtrar presupuestos por año y por las cuentas permitidas
        presupuestos = Presupuesto.objects.filter(anio=anio, cuenta_id__in=cuentas_ids).select_related('cuenta')
        
        reporte = []
        alertas = []

        for presupuesto in presupuestos:
            # Construir filtro base para mantenimientos
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
    def obtener_datos_graficos_costos():
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
            calculos = ReporteCalculos.calcular_costos_vehiculo(vehiculo)
            datos['patentes'].append(vehiculo.patente)
            datos['costos_mantenimiento'].append(float(calculos['costo_mantenimientos']))
            datos['costos_combustible'].append(float(calculos['costo_combustible']))
            datos['costos_arriendo'].append(float(calculos['costo_arriendos']))
            datos['costos_totales'].append(float(calculos['costo_total']))
            # Calcular días fuera de servicio
            total_dias = 0
            for mant in vehiculo.mantenimientos.all():
                if mant.fecha_salida:
                    total_dias += (mant.fecha_salida - mant.fecha_ingreso).days
            datos['dias_fuera_servicio'].append(total_dias)
        
        return datos


class TabManager:
    """Maneja el estado de pestañas sin JavaScript complejo"""
    
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
    # Si no hay ningún dato, al menos mostrar el año actual para permitir búsqueda
    if not anios:
        anios = [datetime.now().year]
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
def reportes(request):  # antes se llamaba reporte_costos
    """Vista principal unificada - incluye costos, variación, dashboard y disponibilidad"""
    # Detectar si es exportación
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
            # Exportar disponibilidad a Excel
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

    # Procesamiento normal para HTML
    active_tab = request.GET.get('tab', 'costos')
    tab_manager = TabManager(request)

    # ========== Pestaña COSTOS ==========
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
        costo_periodo_total = calculos['costo_total']
        costo_por_km_periodo = (costo_periodo_total / Decimal(km_periodo)) if km_periodo > 0 else Decimal('0')
        
        reporte_costos_data.append({
            'vehiculo': vehiculo,
            'costo_mantenimientos': calculos['costo_mantenimientos'],
            'costo_preventivo': calculos['costo_preventivo'],
            'costo_correctivo': calculos['costo_correctivo'],
            'costo_combustible': calculos['costo_combustible'],
            'costo_arriendos': calculos['costo_arriendos'],
            'costo_total': costo_periodo_total,
            'costo_por_km': costo_por_km_periodo,
            'rendimiento_km_l': ind_c.get('rendimiento', '—'),
            'costo_combustible_km': ind_c.get('costo_combustible_km', 'N/A'),
            'indice_eficiencia': ind_c.get('indice_eficiencia', '—'),
            'presupuesto': Presupuesto.objects.filter(activo=True).aggregate(total=Sum('monto_asignado'))['total'] or Decimal('0'),
        })


    # ========== Pestaña VARIACIÓN PRESUPUESTARIA ==========
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
    
    # Años disponibles
    anio_actual = datetime.now().year
    anios_con_presupuestos = list(Presupuesto.objects.values_list('anio', flat=True).distinct())
    anios_disponibles = sorted(Presupuesto.objects.values_list('anio', flat=True).distinct(), reverse=True)

    # ========== Datos para gráficos (dashboard) ==========
    datos_graficos = ReporteCalculos.obtener_datos_graficos_costos()
    graficos_json = json.dumps(datos_graficos)

    # ========== Pestaña DISPONIBILIDAD ==========
    anios_disponibles_disp = obtener_anios_disponibles_disponibilidad()
    anio_disp = request.GET.get('anio_disp')
    try:
        anio_disp = int(anio_disp) if anio_disp else anios_disponibles_disp[0]
    except (TypeError, ValueError):
        anio_disp = anios_disponibles_disp[0]

    if anio_disp not in anios_disponibles_disp:
        anio_disp = anios_disponibles_disp[0]

    mes_disp = request.GET.get('mes_disp')
    # Convertir mes a entero si es válido
    if mes_disp and mes_disp.isdigit():
        mes_disp = int(mes_disp)
        if not (1 <= mes_disp <= 12):
            mes_disp = None
    else:
        mes_disp = None

    # Días del período
    if mes_disp:
        dias_periodo = monthrange(anio_disp, mes_disp)[1]
    else:
        dias_periodo = 366 if (anio_disp % 4 == 0 and (anio_disp % 100 != 0 or anio_disp % 400 == 0)) else 365

    fecha_desde_disp, fecha_hasta_disp = rango_fechas_reporte(anio_disp, mes_disp)
    vehiculos_disp = Vehiculo.objects.all().order_by('patente')
    v_ids_disp = [v.id for v in vehiculos_disp]
    frecuencia_map = frecuencia_fallas_por_vehiculo(v_ids_disp, fecha_desde_disp, fecha_hasta_disp)
    indisp_prom_map = promedio_dias_indisponibilidad_por_vehiculo(v_ids_disp, fecha_desde_disp, fecha_hasta_disp)

    reporte_disponibilidad = []
    for vehiculo in vehiculos_disp:
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
        })

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
        # Datos de disponibilidad
        'reporte_disponibilidad': reporte_disponibilidad,
        'anios_disponibles_disp': anios_disponibles_disp,
        'anio_disp': anio_disp,
        'mes_disp': mes_disp,
        'dias_periodo_disp': dias_periodo,
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
    
    # Filtrar por fechas si se proporcionan
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


@login_required
def reporte_servicios(request):
    # Cuenta por tipo de servicio/previsión a nivel de paciente (PacienteTraslado)
    servicios = PacienteTraslado.objects.values('prevision').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Normalizar etiquetas: previsión vacía como "Sin especificar"
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
    