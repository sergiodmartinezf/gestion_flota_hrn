from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, F
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from ..models import Presupuesto, Mantenimiento, Vehiculo, CuentaPresupuestaria
from ..forms import PresupuestoForm
from .utilidades import es_administrador
from ..utils import exportar_reporte_excel

# RF_21: Registrar presupuesto anual por convenio
@login_required
@user_passes_test(es_administrador)
def registrar_presupuesto(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST)
        if form.is_valid():
            try:
                presupuesto = form.save()
                messages.success(request, 'Presupuesto registrado exitosamente.')
                return redirect('listar_presupuestos')
            except Exception as e:
                messages.error(request, f'Error al registrar presupuesto: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PresupuestoForm()
    
    return render(request, 'flota/registrar_presupuesto.html', {'form': form})


@login_required
@user_passes_test(es_administrador)
def modificar_presupuesto(request, id):
    presupuesto = get_object_or_404(Presupuesto, id=id)
    if request.method == 'POST':
        form = PresupuestoForm(request.POST, instance=presupuesto)
        if form.is_valid():
            try:
                presupuesto = form.save()
                messages.success(request, 'Presupuesto modificado exitosamente.')
                return redirect('listar_presupuestos')
            except Exception as e:
                messages.error(request, f'Error al modificar presupuesto: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PresupuestoForm(instance=presupuesto)
    
    return render(request, 'flota/modificar_presupuesto.html', {'form': form, 'presupuesto': presupuesto})


@login_required
@user_passes_test(es_administrador)
def deshabilitar_presupuesto(request, id):
    presupuesto = get_object_or_404(Presupuesto, id=id)
    if request.method == 'POST':
        presupuesto.activo = False
        presupuesto.save()
        messages.success(request, 'Presupuesto deshabilitado exitosamente.')
        return redirect('listar_presupuestos')
    
    return render(request, 'flota/deshabilitar_presupuesto.html', {'presupuesto': presupuesto})


@login_required
def listar_presupuestos(request):
    # REQ: Manejo de visualización de deshabilitados
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'

    if mostrar_deshabilitados:
        presupuestos = Presupuesto.objects.all().order_by('-anio', 'vehiculo')
    else:
        presupuestos = Presupuesto.objects.filter(activo=True).order_by('-anio', 'vehiculo')

    # Filtros
    anio_filter = request.GET.get('anio')
    vehiculo_filter = request.GET.get('vehiculo')

    if anio_filter:
        presupuestos = presupuestos.filter(anio=anio_filter)
    if vehiculo_filter:
        presupuestos = presupuestos.filter(vehiculo__patente=vehiculo_filter)

    # Calcular totales
    total_asignado = presupuestos.aggregate(
        total=Sum('monto_asignado')
    )['total'] or Decimal('0')

    total_ejecutado = presupuestos.aggregate(
        total=Sum('monto_ejecutado')
    )['total'] or Decimal('0')

    total_disponible = total_asignado - total_ejecutado

    vehiculos = Vehiculo.objects.all().order_by('patente')

    return render(request, 'flota/listar_presupuestos.html', {
        'presupuestos': presupuestos,
        'vehiculos': vehiculos,
        'anio_filter': anio_filter,
        'vehiculo_filter': vehiculo_filter,
        'total_asignado': total_asignado,
        'total_ejecutado': total_ejecutado,
        'total_disponible': total_disponible,
        # Pasar variable al template
        'mostrar_deshabilitados': mostrar_deshabilitados,
    })


# RF_22: Visualizar alertas de presupuesto
@login_required
def alertas_presupuesto(request):
    presupuestos = Presupuesto.objects.filter(activo=True)
    alertas = []
    
    for presupuesto in presupuestos:
        porcentaje = presupuesto.porcentaje_ejecutado
        if porcentaje >= 80:  # Alerta cuando se ha gastado el 80% o más
            alertas.append({
                'presupuesto': presupuesto,
                'porcentaje': porcentaje,
                'monto_restante': presupuesto.monto_asignado - presupuesto.monto_ejecutado,
            })
    
    return render(request, 'flota/alertas_presupuesto.html', {'alertas': alertas})


# Reporte de Variación Presupuestaria (ahora parte de reporte_costos, pero se mantiene para exportación)
@login_required
def reporte_variacion_presupuestaria(request):
    """
    Reporte que compara presupuesto planificado vs ejecutado.
    Alerta cuando la variación es mayor al 10% (requisito crítico).
    """
    anio = request.GET.get('anio', timezone.now().year)
    try:
        anio = int(anio)
    except (ValueError, TypeError):
        anio = timezone.now().year

    # NOTA: Según requisito, este reporte es para "presupuesto anual para lo preventivo"
    # El monto_ejecutado ya está calculado solo con mantenimientos preventivos en signals.py
    presupuestos = Presupuesto.objects.filter(anio=anio, activo=True).select_related('vehiculo', 'cuenta')
    
    reporte = []
    alertas_variacion = []
    
    for presupuesto in presupuestos:
        # Recalcular monto ejecutado solo con mantenimientos preventivos para este reporte
        monto_ejecutado_preventivo = Mantenimiento.objects.filter(
            cuenta_presupuestaria=presupuesto.cuenta,
            vehiculo=presupuesto.vehiculo,
            fecha_ingreso__year=anio,
            tipo_mantencion='Preventivo'
        ).aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
        
        # Calcular variación usando el monto ejecutado de preventivos
        diferencia = monto_ejecutado_preventivo - presupuesto.monto_asignado
        porcentaje_variacion = (diferencia / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
        
        # Determinar si hay alerta (solo cuando se sobrepasa el presupuesto en más del 10%)
        # No alertar si hay mucho presupuesto sin usar, solo cuando se excede
        tiene_alerta = porcentaje_variacion > 10
        
        porcentaje_ejecutado = (monto_ejecutado_preventivo / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
        
        item_reporte = {
            'vehiculo': presupuesto.vehiculo.patente if presupuesto.vehiculo else 'Flota General',
            'marca_modelo': f"{presupuesto.vehiculo.marca} {presupuesto.vehiculo.modelo}" if presupuesto.vehiculo else 'N/A',
            'cuenta_sigfe': presupuesto.cuenta.codigo,
            'nombre_cuenta': presupuesto.cuenta.nombre,
            'monto_asignado': presupuesto.monto_asignado,
            'monto_ejecutado': monto_ejecutado_preventivo,  # Solo preventivos
            'diferencia': diferencia,
            'porcentaje_variacion': porcentaje_variacion,
            'porcentaje_ejecutado': porcentaje_ejecutado,
            'tiene_alerta': tiene_alerta,
            'presupuesto': presupuesto,  # Para el template
        }
        
        reporte.append(item_reporte)
        
        if tiene_alerta:
            alertas_variacion.append(item_reporte)
    
    # Exportar a Excel si se solicita
    if request.GET.get('exportar') == 'excel':
        columnas = [
            ('Vehículo', 'vehiculo', 'texto'),
            ('Marca/Modelo', 'marca_modelo', 'texto'),
            ('Cuenta SIGFE', 'cuenta_sigfe', 'texto'),
            ('Nombre Cuenta', 'nombre_cuenta', 'texto'),
            ('Monto Asignado', 'monto_asignado', 'moneda'),
            ('Monto Ejecutado', 'monto_ejecutado', 'moneda'),
            ('Diferencia', 'diferencia', 'moneda'),
            ('% Variación', 'porcentaje_variacion', 'decimal'),
            ('% Ejecutado', 'porcentaje_ejecutado', 'decimal'),
        ]
        return exportar_reporte_excel(
            f'Análisis de Variación Presupuestaria - Año {anio}',
            reporte,
            columnas,
            f'variacion_presupuestaria_{anio}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    
    # Obtener años disponibles: desde el año actual hacia atrás hasta 5 años
    anio_actual = timezone.now().year
    anios_disponibles = list(range(anio_actual, anio_actual - 6, -1))
    # Agregar años que tienen presupuestos registrados
    anios_con_presupuestos = list(Presupuesto.objects.values_list('anio', flat=True).distinct())
    anios_disponibles = sorted(set(anios_disponibles + anios_con_presupuestos), reverse=True)
    
    return render(request, 'flota/reporte_variacion_presupuestaria.html', {
        'reporte': reporte,
        'alertas_variacion': alertas_variacion,
        'anio': anio,
        'anios_disponibles': anios_disponibles,
    })


