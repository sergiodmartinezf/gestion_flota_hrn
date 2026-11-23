from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from ..models import Presupuesto, Mantenimiento, CargaCombustible, Arriendo, OrdenCompra
from ..forms import PresupuestoForm
from .utilidades import es_administrador


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
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'
    
    presupuestos = Presupuesto.objects.all() if mostrar_deshabilitados else Presupuesto.objects.filter(activo=True)
    presupuestos = presupuestos.order_by('-anio', 'cuenta__codigo')
    
    anio_filter = request.GET.get('anio')
    if anio_filter:
        presupuestos = presupuestos.filter(anio=anio_filter)
    
    total_asignado = presupuestos.aggregate(total=Sum('monto_asignado'))['total'] or 0
    total_ejecutado = presupuestos.aggregate(total=Sum('monto_ejecutado'))['total'] or 0
    
    # Obtener años únicos correctamente
    years_range = Presupuesto.objects.values_list('anio', flat=True).distinct().order_by('anio')
    
    return render(request, 'flota/listar_presupuestos.html', {
        'presupuestos': presupuestos,
        'anio_filter': anio_filter,
        'total_asignado': total_asignado,
        'total_ejecutado': total_ejecutado,
        'total_disponible': total_asignado - total_ejecutado,
        'mostrar_deshabilitados': mostrar_deshabilitados,
        'years_range': years_range,
    })
@login_required
def desglose_presupuesto(request, id):
    """Muestra las fuentes que componen el monto ejecutado del presupuesto."""
    presupuesto = get_object_or_404(Presupuesto.objects.select_related('cuenta'), id=id)
    cuenta = presupuesto.cuenta
    anio = presupuesto.anio

    mantenimientos = Mantenimiento.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha_ingreso__year=anio,
        estado='Finalizado',
    ).select_related('vehiculo', 'proveedor').order_by('fecha_ingreso', 'id')

    combustibles = CargaCombustible.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha__year=anio,
    ).select_related('patente_vehiculo', 'conductor').order_by('fecha', 'id')

    arriendos = Arriendo.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha_inicio__year=anio,
        estado='Activo',
        activo=True,
    ).select_related('vehiculo_arrendado', 'proveedor').order_by('fecha_inicio', 'id')

    ids_oc_contabilizadas = set(mantenimientos.filter(
        orden_compra_id__isnull=False
    ).values_list('orden_compra_id', flat=True))
    ordenes_compra = OrdenCompra.objects.filter(
        cuenta_presupuestaria=cuenta,
        fecha_emision__year=anio,
    ).exclude(estado='Anulada')
    if ids_oc_contabilizadas:
        ordenes_compra = ordenes_compra.exclude(id__in=ids_oc_contabilizadas)
    ordenes_compra = ordenes_compra.select_related('proveedor').order_by('fecha_emision', 'id')

    secciones = [
        {
            'titulo': 'Mantenciones finalizadas',
            'items': [{
                'fecha': m.fecha_ingreso,
                'referencia': f'Mantención #{m.id} · {m.vehiculo.patente}',
                'detalle': f'{m.get_tipo_mantencion_display()} · {m.descripcion_trabajo or "Sin descripción"}',
                'monto': m.costo_total_real or 0,
            } for m in mantenimientos],
        },
        {
            'titulo': 'Combustible',
            'items': [{
                'fecha': c.fecha,
                'referencia': f'{c.patente_vehiculo.patente} · Carga #{c.id}',
                'detalle': f'{c.litros} litros · Boleta {c.nro_boleta or "Sin número"}',
                'monto': c.costo_total or 0,
            } for c in combustibles],
        },
        {
            'titulo': 'Arriendos activos',
            'items': [{
                'fecha': a.fecha_inicio,
                'referencia': f'Arriendo #{a.id} · {a.vehiculo_arrendado.patente}',
                'detalle': f'{a.proveedor.nombre_fantasia} · hasta {a.fecha_fin or "sin fecha de término"}',
                'monto': a.costo_total or 0,
            } for a in arriendos],
        },
        {
            'titulo': 'Órdenes de compra no anuladas',
            'items': [{
                'fecha': oc.fecha_emision,
                'referencia': f'OC {oc.nro_oc}',
                'detalle': f'{oc.proveedor.nombre_fantasia} · {oc.descripcion or "Sin descripción"}',
                'monto': oc.monto_total or 0,
            } for oc in ordenes_compra],
        },
    ]
    total_desglosado = 0
    for seccion in secciones:
        seccion['total'] = sum(item['monto'] for item in seccion['items'])
        total_desglosado += seccion['total']

    return render(request, 'flota/desglose_presupuesto.html', {
        'presupuesto': presupuesto,
        'secciones': secciones,
        'total_desglosado': total_desglosado,
        'diferencia': presupuesto.monto_ejecutado - total_desglosado,
    })

