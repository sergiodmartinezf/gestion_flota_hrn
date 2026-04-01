from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from ..models import Vehiculo, Mantenimiento, CargaCombustible, Presupuesto, AlertaMantencion, CuentaPresupuestaria
from ..forms import VehiculoForm
from .utilidades import es_administrador

# RF_06: Registrar vehículo
@login_required
@user_passes_test(es_administrador)
def registrar_vehiculo(request):
    if request.method == 'POST':
        form = VehiculoForm(request.POST)
        if form.is_valid():
            vehiculo = form.save()
            messages.success(request, f'Vehículo {vehiculo.patente} registrado exitosamente.')
            return redirect('listar_flota')
    else:
        form = VehiculoForm()
    
    return render(request, 'flota/registrar_vehiculo.html', {'form': form})


# RF_07: Listar flota
@login_required
def listar_flota(request):
    vehiculos = Vehiculo.objects.all().order_by('patente')
    
    # Filtros
    estado_filter = request.GET.get('estado')
    tipo_filter = request.GET.get('tipo_carroceria')
    propiedad_filter = request.GET.get('tipo_propiedad')
    criticidad_filter = request.GET.get('criticidad')
    
    if estado_filter:
        vehiculos = vehiculos.filter(estado=estado_filter)
    if tipo_filter:
        vehiculos = vehiculos.filter(tipo_carroceria=tipo_filter)
    if propiedad_filter:
        vehiculos = vehiculos.filter(tipo_propiedad=propiedad_filter)
    if criticidad_filter:
        vehiculos = vehiculos.filter(criticidad=criticidad_filter)
    
    tipos_distintos = Vehiculo.objects.values_list('tipo_carroceria', flat=True).distinct()
    choices_dict = dict(Vehiculo.TIPOS_CARROCERIA)
    tipos_carroceria = []
    for tipo in tipos_distintos:
        display = choices_dict.get(tipo, tipo)  # si no está en choices, mostrar el valor crudo
        tipos_carroceria.append((tipo, display))

    return render(request, 'flota/listar_flota.html', {
        'vehiculos': vehiculos,
        'estado_filter': estado_filter,
        'tipo_filter': tipo_filter,
        'propiedad_filter': propiedad_filter,
        'criticidad_filter': criticidad_filter,
        'tipos_carroceria': tipos_carroceria,   # ← NUEVO
    })

# RF_08: Visualizar ficha de unidad
@login_required
def ficha_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo).order_by('-fecha_ingreso')[:10]
    alertas = AlertaMantencion.objects.filter(vehiculo=vehiculo, vigente=True)
    presupuestos = Presupuesto.objects.filter(vehiculo=vehiculo).order_by('-anio')
    
    # Calcular costo por kilómetro
    total_mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo).aggregate(
        total=Sum('costo_total_real')
    )['total'] or Decimal('0')
    
    total_combustible = CargaCombustible.objects.filter(patente_vehiculo=vehiculo).aggregate(
        total=Sum('costo_total')
    )['total'] or Decimal('0')
    
    costo_total = total_mantenimientos + total_combustible
    costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
    
    return render(request, 'flota/ficha_vehiculo.html', {
        'vehiculo': vehiculo,
        'mantenimientos': mantenimientos,
        'alertas': alertas,
        'presupuestos': presupuestos,
        'costo_total': costo_total,
        'costo_por_km': costo_por_km,
    })


# RF_09: Modificar datos de unidad
@login_required
@user_passes_test(es_administrador)
def modificar_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    if request.method == 'POST':
        form = VehiculoForm(request.POST, instance=vehiculo)
        if form.is_valid():
            vehiculo = form.save()
            messages.success(request, f'Vehículo {vehiculo.patente} modificado exitosamente.')
            return redirect('ficha_vehiculo', patente=vehiculo.patente)
    else:
        form = VehiculoForm(instance=vehiculo)
    
    return render(request, 'flota/modificar_vehiculo.html', {'form': form, 'vehiculo': vehiculo})
    

# RF_10: Actualizar estado de unidad
@login_required
@user_passes_test(es_administrador)
def actualizar_estado_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Vehiculo.ESTADOS):
            vehiculo.estado = nuevo_estado
            vehiculo.save()
            messages.success(request, f'Estado del vehículo {vehiculo.patente} actualizado a {nuevo_estado}.')
            return redirect('ficha_vehiculo', patente=vehiculo.patente)
    
    return render(request, 'flota/actualizar_estado_vehiculo.html', {'vehiculo': vehiculo})


# RF_11: Visualizar disponibilidad de flota
@login_required
def disponibilidad_flota(request):
    vehiculos = Vehiculo.objects.all()
    estados_count = {}
    for estado, nombre in Vehiculo.ESTADOS:
        estados_count[estado] = vehiculos.filter(estado=estado).count()
    
    return render(request, 'flota/disponibilidad_flota.html', {
        'vehiculos': vehiculos,
        'estados_count': estados_count,
    })


# RF_12: Visualizar costo por kilometro
@login_required
def costo_por_kilometro(request):
    vehiculos = Vehiculo.objects.all()
    costos = []
    
    for vehiculo in vehiculos:
        total_mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo).aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        
        total_combustible = CargaCombustible.objects.filter(patente_vehiculo=vehiculo).aggregate(
            total=Sum('costo_total')
        )['total'] or Decimal('0')
        
        costo_total = total_mantenimientos + total_combustible
        costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
        
        costos.append({
            'vehiculo': vehiculo,
            'costo_total': costo_total,
            'costo_por_km': costo_por_km,
        })
    
    costo_promedio = sum(c['costo_por_km'] for c in costos) / len(costos) if costos else Decimal('0')
    
    return render(request, 'flota/costo_por_kilometro.html', {
        'costos': costos,
        'costo_promedio': costo_promedio,
    })


# RF_13: Visualizar gastos de mantenimientos
@login_required
def gastos_mantenimientos(request):
    vehiculos = Vehiculo.objects.all()
    gastos = []
    
    for vehiculo in vehiculos:
        presupuestos = Presupuesto.objects.filter(vehiculo=vehiculo)
        gasto_acumulado = Mantenimiento.objects.filter(vehiculo=vehiculo).aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        
        presupuesto_total = presupuestos.aggregate(
            total=Sum('monto_asignado')
        )['total'] or Decimal('0')
        
        gastos.append({
            'vehiculo': vehiculo,
            'gasto_acumulado': gasto_acumulado,
            'presupuesto_total': presupuesto_total,
            'diferencia': gasto_acumulado - presupuesto_total,
        })
    
    return render(request, 'flota/gastos_mantenimientos.html', {'gastos': gastos})


def _alertas_mantenimiento_no_pausadas():
    """Alertas vigentes excluyendo las pausadas (vehículo en taller con mantenimiento activo)."""
    ids_pausadas = set()
    for a in AlertaMantencion.objects.filter(vigente=True):
        if a.vehiculo.estado == 'En mantenimiento' and Mantenimiento.objects.filter(
            vehiculo=a.vehiculo, estado__in=['En taller', 'Esperando repuestos'], fecha_salida__isnull=True
        ).exists():
            ids_pausadas.add(a.id)
    return AlertaMantencion.objects.filter(vigente=True).exclude(id__in=ids_pausadas).order_by('-generado_en')


# RF_14: Visualizar alertas de mantenimiento
@login_required
def alertas_mantenimiento(request):
    from datetime import timedelta
    # Sincronizar alertas por tiempo: mantenimientos Programado con fecha_programada próxima o vencida
    hoy = timezone.now().date()
    umbral_dias = 7
    for mant in Mantenimiento.objects.filter(estado='Programado', fecha_programada__isnull=False):
        if mant.fecha_programada <= hoy + timedelta(days=umbral_dias):
            if not AlertaMantencion.objects.filter(
                vehiculo=mant.vehiculo, vigente=True,
                descripcion__icontains='Mantenimiento programado'
            ).exists():
                AlertaMantencion.objects.create(
                    vehiculo=mant.vehiculo,
                    descripcion=f'Mantenimiento programado {mant.fecha_programada} ({mant.get_tipo_mantencion_display()})',
                    valor_umbral=mant.km_al_ingreso or 0,
                )

    if request.method == 'POST' and request.POST.get('action') == 'marcar_revisadas':
        AlertaMantencion.objects.filter(vigente=True).update(
            vigente=False,
            resuelta_en=timezone.now()
        )
        messages.success(request, 'Todas las alertas han sido marcadas como revisadas.')
        return redirect('alertas_mantenimiento')

    alertas = _alertas_mantenimiento_no_pausadas()

    # Alertas de presupuesto (presupuestos con ≥80% ejecutado)
    alertas_presupuesto = []
    for presupuesto in Presupuesto.objects.filter(activo=True).exclude(monto_asignado=0).select_related('vehiculo', 'cuenta'):
        porcentaje = presupuesto.porcentaje_ejecutado
        if porcentaje >= 80:
            alertas_presupuesto.append({
                'presupuesto': presupuesto,
                'porcentaje': porcentaje,
                'monto_restante': presupuesto.monto_asignado - presupuesto.monto_ejecutado,
            })

    return render(request, 'flota/alertas_mantenimiento.html', {
        'alertas': alertas,
        'alertas_presupuesto': alertas_presupuesto,
    })


