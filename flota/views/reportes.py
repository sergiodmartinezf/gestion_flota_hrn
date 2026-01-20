from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from decimal import Decimal
from datetime import datetime
import json

from ..models import Vehiculo, Mantenimiento, CargaCombustible, Arriendo, Presupuesto, FallaReportada, HojaRuta
from ..utils import exportar_reporte_excel


class ReporteCalculos:
    """Clase para cálculos reutilizables"""
    
    @staticmethod
    def calcular_costos_vehiculo(vehiculo):
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        costo_mantenimientos = mantenimientos.aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        
        cargas = CargaCombustible.objects.filter(patente_vehiculo=vehiculo)
        costo_combustible = cargas.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        arriendos = Arriendo.objects.filter(vehiculo_reemplazado=vehiculo)
        costo_arriendos = arriendos.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        costo_total = costo_mantenimientos + costo_combustible + costo_arriendos
        costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
        
        return {
            'vehiculo': vehiculo,
            'costo_mantenimientos': costo_mantenimientos,
            'costo_combustible': costo_combustible,
            'costo_arriendos': costo_arriendos,
            'costo_total': costo_total,
            'costo_por_km': costo_por_km,
        }
    
    @staticmethod
    def calcular_variacion_anio(anio):
        presupuestos = Presupuesto.objects.filter(anio=anio, activo=True).select_related('vehiculo', 'cuenta')
        reporte = []
        alertas = []
        
        for presupuesto in presupuestos:
            monto_ejecutado = Mantenimiento.objects.filter(
                cuenta_presupuestaria=presupuesto.cuenta,
                vehiculo=presupuesto.vehiculo,
                fecha_ingreso__year=anio,
                tipo_mantencion='Preventivo'
            ).aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
            
            diferencia = monto_ejecutado - presupuesto.monto_asignado
            porcentaje_variacion = (diferencia / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
            tiene_alerta = porcentaje_variacion > 10
            
            item = {
                'vehiculo': presupuesto.vehiculo.patente if presupuesto.vehiculo else 'Flota General',
                'marca_modelo': f"{presupuesto.vehiculo.marca} {presupuesto.vehiculo.modelo}" if presupuesto.vehiculo else 'N/A',
                'cuenta_sigfe': presupuesto.cuenta.codigo,
                'nombre_cuenta': presupuesto.cuenta.nombre,
                'monto_asignado': presupuesto.monto_asignado,
                'monto_ejecutado': monto_ejecutado,
                'diferencia': diferencia,
                'porcentaje_variacion': porcentaje_variacion,
                'porcentaje_ejecutado': (monto_ejecutado / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0,
                'tiene_alerta': tiene_alerta,
            }
            
            reporte.append(item)
            if tiene_alerta:
                alertas.append(item)
        
        return reporte, alertas

    # Gráficos
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


def exportar_costos_excel(request):
    """Exporta reporte de costos a Excel"""
    vehiculos = Vehiculo.objects.all()
    datos = []
    
    for vehiculo in vehiculos:
        calculos = ReporteCalculos.calcular_costos_vehiculo(vehiculo)
        datos.append({
            'patente': vehiculo.patente,
            'costo_mantenimientos': calculos['costo_mantenimientos'],
            'costo_combustible': calculos['costo_combustible'],
            'costo_arriendos': calculos['costo_arriendos'],
            'costo_total': calculos['costo_total'],
            'costo_por_km': calculos['costo_por_km'],
            'presupuesto': Presupuesto.objects.filter(
                vehiculo=vehiculo
            ).aggregate(total=Sum('monto_asignado'))['total'] or Decimal('0'),
        })
    
    columnas = [
        ('Vehículo', 'patente', 'texto'),
        ('Costo Mantenimientos', 'costo_mantenimientos', 'moneda'),
        ('Costo Combustible', 'costo_combustible', 'moneda'),
        ('Costo Arriendos', 'costo_arriendos', 'moneda'),
        ('Costo Total', 'costo_total', 'moneda'),
        ('Costo por Km', 'costo_por_km', 'decimal'),
        ('Presupuesto', 'presupuesto', 'moneda'),
    ]
    
    return exportar_reporte_excel(
        'Reporte de Costos por Vehículo',
        datos,
        columnas,
        f'reporte_costos_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


def exportar_variacion_excel(anio):
    """Exporta reporte de variación a Excel"""
    reporte, _ = ReporteCalculos.calcular_variacion_anio(anio)
    
    columnas = [
        ('Vehículo', 'vehiculo', 'texto'),
        ('Marca/Modelo', 'marca_modelo', 'texto'),
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


@login_required
def reporte_costos(request):
    """Vista principal unificada - compatibilidad total"""
    # Detectar si es exportación
    if request.GET.get('exportar') == 'excel':
        tab = request.GET.get('tab', 'costos')
        if tab == 'variacion':
            anio = request.GET.get('anio', datetime.now().year)
            return exportar_variacion_excel(int(anio))
        else:
            return exportar_costos_excel(request)
    
    # Procesamiento normal para HTML
    active_tab = request.GET.get('tab', 'costos')
    tab_manager = TabManager(request)
    
    # Datos para pestaña de costos
    vehiculos = Vehiculo.objects.all()
    reporte_costos_data = []
    
    for vehiculo in vehiculos:
        calculos = ReporteCalculos.calcular_costos_vehiculo(vehiculo)
        reporte_costos_data.append({
            **calculos,
            'patente': vehiculo.patente,
            'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
            'presupuesto': Presupuesto.objects.filter(
                vehiculo=vehiculo
            ).aggregate(total=Sum('monto_asignado'))['total'] or Decimal('0'),
        })
    
    # Datos para pestaña de variación
    anio = request.GET.get('anio', datetime.now().year)
    try:
        anio = int(anio)
    except ValueError:
        anio = datetime.now().year
    
    reporte_variacion, alertas_variacion = ReporteCalculos.calcular_variacion_anio(anio)
    
    # Años disponibles
    from django.utils import timezone
    anio_actual = timezone.now().year
    anios_con_presupuestos = list(Presupuesto.objects.values_list('anio', flat=True).distinct())
    anios_disponibles = sorted(set([anio_actual] + anios_con_presupuestos), reverse=True)

    # Para gráficos
    datos_graficos = ReporteCalculos.obtener_datos_graficos_costos()
    graficos_json = json.dumps(datos_graficos)
    
    return render(request, 'flota/reporte_costos.html', {
        'reporte': reporte_costos_data,
        'reporte_variacion': reporte_variacion,
        'alertas_variacion': alertas_variacion,
        'anio': anio,
        'anios_disponibles': anios_disponibles,
        'active_tab': active_tab,
        'tab_manager': tab_manager,
        'graficos_json': graficos_json,
    })


# RF_25: Generar reporte de disponibilidad (ahora parte de reporte_costos)
@login_required
def reporte_disponibilidad(request):
    vehiculos = Vehiculo.objects.all()
    reporte = []
    
    for vehiculo in vehiculos:
        # Calcular días fuera de servicio sumando duración de mantenimientos
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        total_dias_fuera = 0
        
        for mant in mantenimientos:
            if mant.fecha_salida:
                dias = (mant.fecha_salida - mant.fecha_ingreso).days
                total_dias_fuera += max(0, dias)
        
        incidentes = FallaReportada.objects.filter(vehiculo=vehiculo).count()
        
        reporte.append({
            'patente': vehiculo.patente,
            'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
            'dias_fuera_servicio': total_dias_fuera,
            'incidentes': incidentes,
            'estado': vehiculo.get_estado_display(),
            'vehiculo': vehiculo,  # Para el template
        })
    
    # Exportar a Excel si se solicita
    if request.GET.get('exportar') == 'excel':
        columnas = [
            ('Vehículo', 'patente', 'texto'),
            ('Marca/Modelo', 'marca_modelo', 'texto'),
            ('Días Fuera de Servicio', 'dias_fuera_servicio', 'entero'),
            ('Número de Incidentes', 'incidentes', 'entero'),
            ('Estado Actual', 'estado', 'texto'),
        ]
        return exportar_reporte_excel(
            'Reporte de Disponibilidad de Flota',
            reporte,
            columnas,
            f'reporte_disponibilidad_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    
    return render(request, 'flota/reporte_disponibilidad.html', {'reporte': reporte})


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
