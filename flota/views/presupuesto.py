from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from ..models import Presupuesto
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
