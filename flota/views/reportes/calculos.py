from django.db.models import Sum, Count
from decimal import Decimal
from datetime import datetime, timedelta

from ...models import Vehiculo, Mantenimiento, CargaCombustible, Arriendo, Presupuesto, FallaReportada
from ...indicadores import (
    frecuencia_fallas_por_vehiculo,
    indicadores_costos_combustible,
    promedio_dias_indisponibilidad_por_vehiculo,
    rango_fechas_reporte,
    km_totales_por_vehiculo,
)
from ...constants import ids_cuentas_por_tipo_mantencion as _ids_cuentas_por_tipo_mantencion

def obtener_cuentas_por_tipo_mantencion(tipo_mantencion):
    """IDs de cuentas SIGFE asociadas al tipo de mantención (resueltos desde BD)."""
    return _ids_cuentas_por_tipo_mantencion(tipo_mantencion)


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
