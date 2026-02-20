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
    
    # Eliminamos el límite de "hoy" para que siempre proyecte los 365/366 días del año
    fin_calculo = fin_anio
    dias_del_periodo = (fin_calculo - inicio_anio).days + 1

    # --- Presupuestos: monto asignado total ---
    presupuestos = Presupuesto.objects.filter(anio=anio_seleccionado, activo=True)
    total_asignado = presupuestos.aggregate(Sum('monto_asignado'))['monto_asignado__sum'] or 0

    # --- Ejecución real: suma de costos de mantenimientos finalizados en el año ---
    mantenimientos_anio = Mantenimiento.objects.filter(
        fecha_salida__year=anio_seleccionado,
        estado='Finalizado',
        cuenta_presupuestaria__isnull=False   # excluir registros sin cuenta
    )

    # Definir códigos de cuenta para preventivo y correctivo
    preventive_codes = ['22.06.002.001', '22.06.002.003']
    corrective_codes = ['22.06.002.002', '22.06.002.004']

    # --- Gasto mensual desglosado (preventivo vs correctivo) usando cuenta ---
    meses_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    monthly_prev = [0]*12
    monthly_corr = [0]*12
    for m in mantenimientos_anio:
        if m.fecha_salida:
            month = m.fecha_salida.month - 1
            codigo = m.cuenta_presupuestaria.codigo
            if codigo in preventive_codes:
                monthly_prev[month] += m.costo_total_real
            elif codigo in corrective_codes:
                monthly_corr[month] += m.costo_total_real
    monthly_prev = [int(x) for x in monthly_prev]
    monthly_corr = [int(x) for x in monthly_corr]

    # --- Totales anuales por tipo (según cuenta) ---
    total_preventivo = mantenimientos_anio.filter(cuenta_presupuestaria__codigo__in=preventive_codes).aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
    total_correctivo = mantenimientos_anio.filter(cuenta_presupuestaria__codigo__in=corrective_codes).aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0

    # --- Top 10 vehículos con más gasto (desglosado por cuenta) ---
    vehiculos = Vehiculo.objects.exclude(estado='Baja')
    gasto_por_vehiculo_detalle = []
    for v in vehiculos:
        prev = mantenimientos_anio.filter(vehiculo=v, cuenta_presupuestaria__codigo__in=preventive_codes).aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
        corr = mantenimientos_anio.filter(vehiculo=v, cuenta_presupuestaria__codigo__in=corrective_codes).aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
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
        # Buscamos mantenimientos que toquen el año seleccionado
        mants_v = mants_anio.filter(vehiculo=v)
        prev_dias = 0
        corr_dias = 0
        
        for m in mants_v:
            # LÓGICA DE RECORTE DE FECHAS
            # El inicio es el máximo entre cuando empezó el mant. y el 1 de enero
            inicio = max(m.fecha_ingreso, inicio_anio)
            
            # El fin es el mínimo entre cuando terminó (o hoy si sigue abierto) y el 31 de diciembre
            fecha_termino_real = m.fecha_salida if m.fecha_salida else hoy
            fin = min(fecha_termino_real, fin_anio)
            
            if fin >= inicio:
                # Calculamos la duración en ese rango específico
                duracion = (fin - inicio).days + 1
                
                if m.tipo_mantencion == 'Preventivo':
                    prev_dias += duracion
                else:
                    corr_dias += duracion
        
        # IMPORTANTE: Asegurar que un vehículo no tenga más de 365 días de mantención
        # (pasa si hay mantenimientos superpuestos en la base de datos)
        total_off = min(prev_dias + corr_dias, dias_del_periodo)
        operativo = dias_del_periodo - total_off
        
        dias_por_vehiculo.append({
            'patente': v.patente,
            'preventivo': prev_dias,
            'correctivo': corr_dias,
            'total': total_off,
            'operativo': operativo
        })
        dias_preventivo += prev_dias
        dias_correctivo += corr_dias
        
    # --- Disponibilidad total ---
    n_vehiculos = len(vehiculos)
    dias_totales_posibles = n_vehiculos * dias_del_periodo
    dias_operativos = max(0, dias_totales_posibles - (dias_preventivo + dias_correctivo))
    disponibilidad_pct = (dias_operativos / dias_totales_posibles * 100) if dias_totales_posibles > 0 else 100.0

    # --- Separar ambulancias y camioneta para gráficos específicos (LÓGICA CORREGIDA) ---
    ambulancias_qs = vehiculos.filter(tipo_carroceria='Ambulancia')
    patentes_ambulancia = set(ambulancias_qs.values_list('patente', flat=True))
    
    camioneta_qs = vehiculos.filter(tipo_carroceria='Camioneta').first()
    patente_camioneta = camioneta_qs.patente if camioneta_qs else None

    # Sumamos directamente desde el array procesado 'dias_por_vehiculo' para evitar discrepancias
    # entre el cálculo individual y el cálculo grupal.
    dias_preventivo_amb = sum(d['preventivo'] for d in dias_por_vehiculo if d['patente'] in patentes_ambulancia)
    dias_correctivo_amb = sum(d['correctivo'] for d in dias_por_vehiculo if d['patente'] in patentes_ambulancia)
    dias_operativos_amb = sum(d['operativo'] for d in dias_por_vehiculo if d['patente'] in patentes_ambulancia)
    
    # Cálculo total teórico (solo referencial ahora, la suma real manda)
    dias_totales_amb = ambulancias_qs.count() * dias_del_periodo
        
    # --- Promedios por vehículo ---
    if n_vehiculos > 0:
        avg_operativo = sum((d.get('operativo', 0) or 0) for d in dias_por_vehiculo) / n_vehiculos
        avg_preventivo = sum((d.get('preventivo', 0) or 0) for d in dias_por_vehiculo) / n_vehiculos
        avg_correctivo = sum((d.get('correctivo', 0) or 0) for d in dias_por_vehiculo) / n_vehiculos
    else:
        avg_operativo = avg_preventivo = avg_correctivo = 0.0

    # --- Salud de flota (kilómetros) ---
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

    # Usamos los totales calculados con cuenta
    ejec_prev = total_preventivo
    ejec_corr = total_correctivo
    total_ejecutado_real = ejec_prev + ejec_corr

    porcentaje_gasto = (total_ejecutado_real / total_asignado * 100) if total_asignado > 0 else 0

    # --- Factor Plata (drill‑down financiero) - restaurado con cuenta ---
    gasto_mensual = []
    finance_data = {
        'labels': meses_labels,
        'monthly_totals': gasto_mensual,
        'drilldown': []  # Cada elemento será lista de {patente, preventivo, correctivo}
    }
    for i in range(1, 13):
        # Total del mes (para el gráfico de línea)
        total_mes = mantenimientos_anio.filter(fecha_salida__month=i).aggregate(Sum('costo_total_real'))['costo_total_real__sum'] or 0
        gasto_mensual.append(int(total_mes or 0))

        # Desglose por vehículo y tipo según cuenta
        qs_mes = mantenimientos_anio.filter(fecha_salida__month=i)
        vehiculos_mes = {}
        for m in qs_mes:
            if m.vehiculo and m.vehiculo.patente and m.cuenta_presupuestaria:
                pat = m.vehiculo.patente
                if pat not in vehiculos_mes:
                    vehiculos_mes[pat] = {'preventivo': 0, 'correctivo': 0}
                costo = m.costo_total_real or 0
                codigo = m.cuenta_presupuestaria.codigo
                if codigo in preventive_codes:
                    vehiculos_mes[pat]['preventivo'] += costo
                elif codigo in corrective_codes:
                    vehiculos_mes[pat]['correctivo'] += costo
        # Convertir a lista y ordenar por total (desc)
        drill_list = []
        for pat, montos in vehiculos_mes.items():
            prev = int(montos.get('preventivo', 0) or 0)
            corr = int(montos.get('correctivo', 0) or 0)
            drill_list.append({
                'patente': pat or '',
                'preventivo': prev,
                'correctivo': corr,
                'total': prev + corr
            })
        drill_list.sort(key=lambda x: x['total'], reverse=True)
        finance_data['drilldown'].append(drill_list)

    dias_por_vehiculo_limpio = []
    for d in dias_por_vehiculo:
        d_clean = {
            'patente': d['patente'] or '',
            'preventivo': int(d['preventivo'] or 0),
            'correctivo': int(d['correctivo'] or 0),
            'total': int(d['total'] or 0),
            'operativo': int(d['operativo'] or 0),
        }
        dias_por_vehiculo_limpio.append(d_clean)

    # --- Contexto final ---
    context = {
        'years_disponibles': years_disponibles,
        'anio_filter': anio_filter,
        'presupuesto_total': total_asignado,
        'presupuesto_ejecutado': total_ejecutado_real,
        'presupuesto_pct': porcentaje_gasto,
        'json_monthly_split': json.dumps({
            'labels': meses_labels,
            'preventivo': monthly_prev,
            'correctivo': monthly_corr
        }),
        'json_gasto_vehiculo_detalle': json.dumps(gasto_por_vehiculo_detalle),
        'json_gasto_vehiculo': json.dumps([v['total'] for v in gasto_por_vehiculo_detalle]),
        'json_labels_vehiculo': json.dumps([v['patente'] for v in gasto_por_vehiculo_detalle]),
        'cumplimiento_pct': cumplimiento_pct,
        'detalle_cumplimiento': detalle_cumplimiento,
        'disponibilidad_pct': round(disponibilidad_pct, 1),
        'dias_preventivo': dias_preventivo,
        'dias_correctivo': dias_correctivo,
        'dias_operativos': dias_operativos,
        'dias_por_vehiculo': dias_por_vehiculo,
        'dias_del_periodo': dias_del_periodo,
        'inicio_anio': inicio_anio,
        'fin_calculo': fin_calculo,
        'ambulancias_count': ambulancias_qs.count(),
        'dias_totales_amb': int(dias_totales_amb),
        'dias_operativos_amb': int(dias_operativos_amb),
        'dias_preventivo_amb': int(dias_preventivo_amb),
        'dias_correctivo_amb': int(dias_correctivo_amb),
        'camioneta': camioneta_qs,
        'avg_operativo': float(round(avg_operativo, 1)) if avg_operativo else 0.0,
        'avg_preventivo': float(round(avg_preventivo, 1)) if avg_preventivo else 0.0,
        'avg_correctivo': float(round(avg_correctivo, 1)) if avg_correctivo else 0.0,
        'json_km_barras': json.dumps(detalle_cumplimiento),
        'json_comparativa_global': json.dumps({
            'labels': ['Mantenimiento Preventivo', 'Mantenimiento Correctivo'],
            'programado': [int(prog_prev), int(prog_corr)],
            'ejecutado': [int(ejec_prev), int(ejec_corr)]
        }),
        'total_prog': prog_prev + prog_corr,
        'total_ejec': ejec_prev + ejec_corr,
        'vehiculos': vehiculos,
        'json_finance': json.dumps(finance_data),
        'dias_por_vehiculo_json': json.dumps(dias_por_vehiculo_limpio),
    }

    logger.info(f"Contexto generado con {len(gasto_por_vehiculo_detalle)} vehículos con gasto.")
    return render(request, 'flota/panel_control.html', context)
    