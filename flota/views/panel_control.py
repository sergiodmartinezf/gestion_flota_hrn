from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Q
from django.utils import timezone
import json
from datetime import date, timedelta
from ..models import Vehiculo, Mantenimiento, Presupuesto, CuentaPresupuestaria, CargaCombustible

@login_required
def panel_control(request):
    hoy = timezone.now().date()
    
    # 1. LÓGICA DE FILTROS (Solo Año)
    years_range = range(2023, hoy.year + 2)
    anio_filter = request.GET.get('anio')
    
    if anio_filter and anio_filter.isdigit():
        anio_seleccionado = int(anio_filter)
    else:
        anio_seleccionado = hoy.year
        anio_filter = str(anio_seleccionado)

    # Definir límites del año para cálculos precisos
    inicio_anio = date(anio_seleccionado, 1, 1)
    fin_anio = date(anio_seleccionado, 12, 31)
    
    # Si el año seleccionado es el futuro, el fin es el 31 de dic, 
    # si es el actual, el fin es hoy para no calcular disponibilidad futura.
    fin_calculo = min(hoy, fin_anio) if anio_seleccionado <= hoy.year else inicio_anio

    # 2. QUERIES FILTRADAS POR AÑO
    presupuestos = Presupuesto.objects.filter(anio=anio_seleccionado, activo=True)
    total_asignado = presupuestos.aggregate(Sum('monto_asignado'))['monto_asignado__sum'] or 0
    total_ejecutado = presupuestos.aggregate(Sum('monto_ejecutado'))['monto_ejecutado__sum'] or 0
    
    porcentaje_gasto = (total_ejecutado / total_asignado * 100) if total_asignado > 0 else 0
    
    # Gasto Mensual (Se mantiene igual)
    gasto_mensual = []
    meses_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    for i in range(1, 13):
        g_mant = Mantenimiento.objects.filter(fecha_salida__year=anio_seleccionado, fecha_salida__month=i, estado='Finalizado').aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
        g_comb = CargaCombustible.objects.filter(fecha__year=anio_seleccionado, fecha__month=i).aggregate(Sum('costo_total'))['costo_total__sum'] or 0
        gasto_mensual.append(int(g_mant + g_comb))

    # Top Gasto por Vehículo
    gasto_por_vehiculo = []
    vehiculos = Vehiculo.objects.exclude(estado='Baja')
    for v in vehiculos:
        g_v = Mantenimiento.objects.filter(vehiculo=v, fecha_salida__year=anio_seleccionado, estado='Finalizado').aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
        if g_v > 0:
            gasto_por_vehiculo.append({'patente': v.patente, 'gasto': int(g_v)})
    
    gasto_por_vehiculo.sort(key=lambda x: x['gasto'], reverse=True)
    gasto_por_vehiculo = gasto_por_vehiculo[:10]

    # --- CORRECCIÓN DISPONIBILIDAD ---
    # Solo contamos vehículos que existían o estaban activos en ese año (opcional, aquí usamos todos los activos)
    total_v = vehiculos.count() or 1
    
    # Días transcurridos en el año hasta la fecha de corte (hoy o fin de año)
    dias_del_periodo = (fin_calculo - inicio_anio).days + 1
    if dias_del_periodo < 0: dias_del_periodo = 0
    
    dias_totales_posibles = dias_del_periodo * total_v
    
    # Buscamos mantenimientos que se solapen con el año seleccionado
    mants_anio = Mantenimiento.objects.filter(
        Q(fecha_ingreso__year=anio_seleccionado) | Q(fecha_salida__year=anio_seleccionado) | Q(fecha_salida__isnull=True, fecha_ingreso__lte=fin_anio)
    ).exclude(estado='Cancelado')
    
    dias_preventivo = 0
    dias_correctivo = 0
    
    for m in mants_anio:
        # Calcular la intersección entre el periodo de mantenimiento y el año seleccionado
        fecha_inicio_efectiva = max(m.fecha_ingreso, inicio_anio)
        fecha_fin_temp = m.fecha_salida if m.fecha_salida else hoy
        fecha_fin_efectiva = min(fecha_fin_temp, fin_anio)
        
        # Solo sumamos si el mantenimiento ocurrió realmente dentro del año
        if fecha_fin_efectiva >= fecha_inicio_efectiva:
            duracion = (fecha_fin_efectiva - fecha_inicio_efectiva).days + 1
            if m.tipo_mantencion == 'Preventivo': 
                dias_preventivo += duracion
            else: 
                dias_correctivo += duracion

    dias_operativos = max(0, dias_totales_posibles - (dias_preventivo + dias_correctivo))
    disponibilidad_pct = (dias_operativos / dias_totales_posibles * 100) if dias_totales_posibles > 0 else 100.0

    # --- SALUD DE FLOTA (AJUSTE) ---
    # Si es el año actual, mostramos el KPI real. Si es un año pasado/futuro, 
    # lo ideal es mostrar 100% o "N/A" si no hay datos de kilometraje histórico.
    cumplimiento_ok = 0
    detalle_cumplimiento = []
    
    if anio_seleccionado == hoy.year:
        for v in vehiculos:
            u_m = v.mantenimientos.filter(tipo_mantencion='Preventivo', estado='Finalizado').order_by('-fecha_salida').first()
            km_u = u_m.km_al_ingreso if u_m else 0
            diff = v.kilometraje_actual - km_u
            
            estado, clase = ("OK", "bg-success") if diff < 9000 else (("Pendiente", "bg-warning text-dark") if diff <= 11000 else ("Crítico", "bg-danger"))
            if estado == "OK": cumplimiento_ok += 1
            detalle_cumplimiento.append({'patente': v.patente, 'km_actual': v.kilometraje_actual, 'km_ultimo': km_u, 'diferencia': diff, 'estado': estado, 'clase': clase})
        cumplimiento_pct = round((cumplimiento_ok / total_v) * 100, 1)
    else:
        # Para años que no son el actual, mostramos 100% como valor base o podrías omitirlo
        cumplimiento_pct = 100.0

    context = {
        'years_range': years_range,
        'anio_filter': anio_filter,
        'presupuesto_total': total_asignado,
        'presupuesto_ejecutado': total_ejecutado,
        'presupuesto_pct': porcentaje_gasto,
        'json_gasto_mensual': json.dumps({'labels': meses_labels, 'data': gasto_mensual}),
        'json_gasto_vehiculo': json.dumps([v['gasto'] for v in gasto_por_vehiculo]),
        'json_labels_vehiculo': json.dumps([v['patente'] for v in gasto_por_vehiculo]),
        'cumplimiento_pct': cumplimiento_pct,
        'detalle_cumplimiento': detalle_cumplimiento,
        'disponibilidad_pct': round(disponibilidad_pct, 1),
        'dias_preventivo': dias_preventivo,
        'dias_correctivo': dias_correctivo,
        'dias_operativos': dias_operativos,
    }
    return render(request, 'flota/panel_control.html', context)