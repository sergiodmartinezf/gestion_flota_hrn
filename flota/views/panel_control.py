from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
import json
import logging
from datetime import date
from ..models import Vehiculo, Mantenimiento, Presupuesto, CuentaPresupuestaria

logger = logging.getLogger(__name__)

@login_required
def panel_control(request):
    hoy = timezone.now().date()
    
    # --- Años disponibles ---
    anos_en_mant = Mantenimiento.objects.dates('fecha_ingreso', 'year').values_list('fecha_ingreso__year', flat=True)
    anos_en_presup = Presupuesto.objects.values_list('anio', flat=True).distinct()
    anos_con_datos = set(anos_en_mant) | set(anos_en_presup)
    anos_con_datos.add(hoy.year)
    years_disponibles = sorted(anos_con_datos)

    # --- Filtro por año ---
    anio_filter = request.GET.get('anio')
    if anio_filter and anio_filter.isdigit() and int(anio_filter) in anos_con_datos:
        anio_seleccionado = int(anio_filter)
    else:
        anio_seleccionado = hoy.year
        anio_filter = str(anio_seleccionado)

    inicio_anio = date(anio_seleccionado, 1, 1)
    fin_anio = date(anio_seleccionado, 12, 31)
    fin_calculo = min(hoy, fin_anio) if anio_seleccionado <= hoy.year else inicio_anio
    dias_del_periodo = (fin_calculo - inicio_anio).days + 1
    if dias_del_periodo < 0:
        dias_del_periodo = 0

    # --- Presupuestos: monto asignado total ---
    presupuestos = Presupuesto.objects.filter(anio=anio_seleccionado, activo=True)
    total_asignado = presupuestos.aggregate(Sum('monto_asignado'))['monto_asignado__sum'] or 0

    # --- Ejecución real: suma de costos de mantenimientos finalizados en el año ---
    mantenimientos_anio = Mantenimiento.objects.filter(
        fecha_salida__year=anio_seleccionado,
        estado='Finalizado'
    )
    total_ejecutado_real = mantenimientos_anio.aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0

    # --- Gasto mensual desglosado (preventivo vs correctivo) ---
    meses_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    monthly_prev = [0]*12
    monthly_corr = [0]*12
    for m in mantenimientos_anio:
        if m.fecha_salida:
            month = m.fecha_salida.month - 1
            if m.tipo_mantencion == 'Preventivo':
                monthly_prev[month] += m.costo_total_real
            else:
                monthly_corr[month] += m.costo_total_real
    monthly_prev = [int(x) for x in monthly_prev]
    monthly_corr = [int(x) for x in monthly_corr]

    # --- Top 10 vehículos con más gasto (desglosado) ---
    vehiculos = Vehiculo.objects.exclude(estado='Baja')
    gasto_por_vehiculo_detalle = []
    for v in vehiculos:
        prev = mantenimientos_anio.filter(vehiculo=v, tipo_mantencion='Preventivo').aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
        corr = mantenimientos_anio.filter(vehiculo=v, tipo_mantencion='Correctivo').aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
        if prev > 0 or corr > 0:
            gasto_por_vehiculo_detalle.append({
                'patente': v.patente,
                'preventivo': int(prev),
                'correctivo': int(corr),
                'total': int(prev+corr)
            })
    gasto_por_vehiculo_detalle.sort(key=lambda x: x['total'], reverse=True)

    # --- Disponibilidad (días fuera de servicio) ---
    mants_anio = Mantenimiento.objects.filter(
        Q(fecha_ingreso__year=anio_seleccionado) |
        Q(fecha_salida__year=anio_seleccionado) |
        Q(fecha_salida__isnull=True, fecha_ingreso__lte=fin_anio)
    ).exclude(estado='Cancelado')

    dias_preventivo = 0
    dias_correctivo = 0
    dias_por_vehiculo = []

    for v in vehiculos:
        mants_v = mants_anio.filter(vehiculo=v)
        prev_dias = 0
        corr_dias = 0
        for m in mants_v:
            inicio = max(m.fecha_ingreso, inicio_anio)
            fin_temp = m.fecha_salida if m.fecha_salida else hoy
            fin = min(fin_temp, fin_anio)
            if fin >= inicio:
                duracion = (fin - inicio).days + 1
                if m.tipo_mantencion == 'Preventivo':
                    prev_dias += duracion
                else:
                    corr_dias += duracion
        total_off = prev_dias + corr_dias
        operativo = max(0, dias_del_periodo - total_off)
        dias_por_vehiculo.append({
            'patente': v.patente,
            'preventivo': prev_dias,
            'correctivo': corr_dias,
            'total': total_off,
            'operativo': operativo
        })
        dias_preventivo += prev_dias
        dias_correctivo += corr_dias

    # --- Disponibilidad total (todos los vehículos) ---
    n_vehiculos = len(vehiculos)
    dias_totales_posibles = n_vehiculos * dias_del_periodo
    dias_operativos = max(0, dias_totales_posibles - (dias_preventivo + dias_correctivo))
    disponibilidad_pct = (dias_operativos / dias_totales_posibles * 100) if dias_totales_posibles > 0 else 100.0

    # --- Separar ambulancias y camioneta para gráficos específicos ---
    ambulancias = vehiculos.filter(tipo_carroceria='Ambulancia')
    camioneta = vehiculos.filter(tipo_carroceria='Camioneta').first()

    dias_totales_amb = ambulancias.count() * dias_del_periodo
    dias_preventivo_amb = sum(d['preventivo'] for d in dias_por_vehiculo if d['patente'] in ambulancias.values_list('patente', flat=True))
    dias_correctivo_amb = sum(d['correctivo'] for d in dias_por_vehiculo if d['patente'] in ambulancias.values_list('patente', flat=True))
    dias_operativos_amb = max(0, dias_totales_amb - (dias_preventivo_amb + dias_correctivo_amb))

    # --- Promedios por vehículo ---
    if n_vehiculos > 0:
        avg_operativo = sum(d['operativo'] for d in dias_por_vehiculo) / n_vehiculos
        avg_preventivo = sum(d['preventivo'] for d in dias_por_vehiculo) / n_vehiculos
        avg_correctivo = sum(d['correctivo'] for d in dias_por_vehiculo) / n_vehiculos
    else:
        avg_operativo = avg_preventivo = avg_correctivo = 0

    # --- Salud de flota (kilómetros) con nuevos umbrales ---
    detalle_cumplimiento = []
    cumplimiento_ok = 0
    for v in vehiculos:
        ultimo_mant = v.mantenimientos.filter(
            tipo_mantencion='Preventivo',
            estado='Finalizado'
        ).order_by('-fecha_salida').first()
        km_ultimo = ultimo_mant.km_al_ingreso if ultimo_mant else 0
        recorrido = v.kilometraje_actual - km_ultimo

        if recorrido < 8000:
            estado = "OK"
            clase = "bg-success"
            color = "#198754"
        elif recorrido < 12000:
            estado = "Próximo a mantenimiento"
            clase = "bg-warning text-dark"
            color = "#ffc107"
        else:
            estado = "Excedido (Bloqueado)"
            clase = "bg-danger"
            color = "#dc3545"

        if estado == "OK":
            cumplimiento_ok += 1

        detalle_cumplimiento.append({
            'patente': v.patente,
            'km_actual': v.kilometraje_actual,
            'km_ultimo': km_ultimo,
            'recorrido': recorrido,
            'valor_grafico': max(recorrido, 50),
            'color': color,
            'estado': estado,
            'clase': clase,
            'proxima': km_ultimo + 10000
        })
    cumplimiento_pct = round((cumplimiento_ok / len(vehiculos)) * 100, 1) if vehiculos else 0

    # --- Comparativa Preventivo vs Correctivo (global) ---
    cuenta_prev_amb = CuentaPresupuestaria.objects.filter(codigo='22.06.002.001').first()
    cuenta_corr_amb = CuentaPresupuestaria.objects.filter(codigo='22.06.002.002').first()
    cuenta_prev_cam = CuentaPresupuestaria.objects.filter(codigo='22.06.002.003').first()
    cuenta_corr_cam = CuentaPresupuestaria.objects.filter(codigo='22.06.002.004').first()

    prog_prev = 0
    prog_corr = 0
    if cuenta_prev_amb:
        prog_prev += presupuestos.filter(cuenta=cuenta_prev_amb).aggregate(Sum('monto_asignado'))['monto_asignado__sum'] or 0
    if cuenta_prev_cam:
        prog_prev += presupuestos.filter(cuenta=cuenta_prev_cam).aggregate(Sum('monto_asignado'))['monto_asignado__sum'] or 0
    if cuenta_corr_amb:
        prog_corr += presupuestos.filter(cuenta=cuenta_corr_amb).aggregate(Sum('monto_asignado'))['monto_asignado__sum'] or 0
    if cuenta_corr_cam:
        prog_corr += presupuestos.filter(cuenta=cuenta_corr_cam).aggregate(Sum('monto_asignado'))['monto_asignado__sum'] or 0

    ejec_prev = mantenimientos_anio.filter(tipo_mantencion='Preventivo').aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
    ejec_corr = mantenimientos_anio.filter(tipo_mantencion='Correctivo').aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0

    porcentaje_gasto = (total_ejecutado_real / total_asignado * 100) if total_asignado > 0 else 0

    # --- Factor Plata (drill‑down financiero) - restaurado ---
    gasto_mensual = []
    finance_data = {
        'labels': meses_labels,
        'monthly_totals': gasto_mensual,
        'drilldown': []  # Cada elemento será lista de {patente, preventivo, correctivo}
    }
    for i in range(1, 13):
        # Total del mes (para el gráfico de línea)
        total_mes = mantenimientos_anio.filter(fecha_salida__month=i).aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
        gasto_mensual.append(int(total_mes))

        # Desglose por vehículo y tipo
        qs_mes = mantenimientos_anio.filter(fecha_salida__month=i)
        vehiculos_mes = {}
        for m in qs_mes:
            pat = m.vehiculo.patente
            if pat not in vehiculos_mes:
                vehiculos_mes[pat] = {'preventivo': 0, 'correctivo': 0}
            if m.tipo_mantencion == 'Preventivo':
                vehiculos_mes[pat]['preventivo'] += m.costo_total_real
            else:
                vehiculos_mes[pat]['correctivo'] += m.costo_total_real
        # Convertir a lista y ordenar por total (desc)
        drill_list = []
        for pat, montos in vehiculos_mes.items():
            drill_list.append({
                'patente': pat,
                'preventivo': int(montos['preventivo']),
                'correctivo': int(montos['correctivo']),
                'total': int(montos['preventivo'] + montos['correctivo'])
            })
        drill_list.sort(key=lambda x: x['total'], reverse=True)
        finance_data['drilldown'].append(drill_list)

    # --- Contexto final ---
    context = {
        'years_disponibles': years_disponibles,
        'anio_filter': anio_filter,
        'presupuesto_total': total_asignado,
        'presupuesto_ejecutado': total_ejecutado_real,
        'presupuesto_pct': porcentaje_gasto,
        # Gasto mensual desglosado (para el nuevo gráfico de barras agrupadas - opcional, pero lo dejamos)
        'json_monthly_split': json.dumps({
            'labels': meses_labels,
            'preventivo': monthly_prev,
            'correctivo': monthly_corr
        }),
        # Gasto por vehículo desglosado
        'json_gasto_vehiculo_detalle': json.dumps(gasto_por_vehiculo_detalle),
        # Para mantener compatibilidad con gráficos antiguos (opcional)
        'json_gasto_vehiculo': json.dumps([v['total'] for v in gasto_por_vehiculo_detalle]),
        'json_labels_vehiculo': json.dumps([v['patente'] for v in gasto_por_vehiculo_detalle]),
        # Cumplimiento de km
        'cumplimiento_pct': cumplimiento_pct,
        'detalle_cumplimiento': detalle_cumplimiento,
        # Disponibilidad general
        'disponibilidad_pct': round(disponibilidad_pct, 1),
        'dias_preventivo': dias_preventivo,
        'dias_correctivo': dias_correctivo,
        'dias_operativos': dias_operativos,
        'dias_por_vehiculo': dias_por_vehiculo,
        'dias_del_periodo': dias_del_periodo,
        'inicio_anio': inicio_anio,
        'fin_calculo': fin_calculo,
        # Datos para gráficos de disponibilidad específicos
        'ambulancias_count': ambulancias.count(),
        'dias_totales_amb': dias_totales_amb,
        'dias_operativos_amb': dias_operativos_amb,
        'dias_preventivo_amb': dias_preventivo_amb,
        'dias_correctivo_amb': dias_correctivo_amb,
        'camioneta': camioneta,
        # Promedios
        'avg_operativo': round(avg_operativo, 1),
        'avg_preventivo': round(avg_preventivo, 1),
        'avg_correctivo': round(avg_correctivo, 1),
        # Datos para gráfico de km
        'json_km_barras': json.dumps(detalle_cumplimiento),
        'json_comparativa_global': json.dumps({
            'labels': ['Mantenimiento Preventivo', 'Mantenimiento Correctivo'],
            'programado': [int(prog_prev), int(prog_corr)],
            'ejecutado': [int(ejec_prev), int(ejec_corr)]
        }),
        'total_prog': prog_prev + prog_corr,
        'total_ejec': ejec_prev + ejec_corr,
        'vehiculos': vehiculos,
        # Drill-down financiero (restaurado)
        'json_finance': json.dumps(finance_data),
        'dias_por_vehiculo_json': json.dumps(dias_por_vehiculo),
    }

    logger.info(f"Contexto generado con {len(gasto_por_vehiculo_detalle)} vehículos con gasto.")
    return render(request, 'flota/panel_control.html', context)
