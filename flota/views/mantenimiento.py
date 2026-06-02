from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError
from decimal import Decimal
import json
from django.core.serializers.json import DjangoJSONEncoder
from ..constants import mapa_mantenimiento_cuenta_ids
from ..models import Mantenimiento, Vehiculo, Proveedor, Presupuesto, Alerta, CuentaPresupuestaria, OrdenTrabajo, OrdenCompra
from ..forms import MantenimientoForm, ProgramarMantenimientoForm, FinalizarMantenimientoForm
from .utilidades import es_administrador
from ..utils import exportar_planilla_mantenimientos_excel

# RF_18 y RF_19: Programar/registrar mantenimiento (preventivo o correctivo) desde calendario
@login_required
@user_passes_test(es_administrador)
def programar_mantenimiento(request):
    """Vista unificada: GET redirige al calendario; POST crea mantenimiento preventivo o correctivo."""
    if request.method != 'POST':
        return redirect('calendario_mantenciones')

    tipo = (request.POST.get('tipo_mantencion') or '').strip()
    if tipo not in ('Preventivo', 'Correctivo'):
        messages.error(request, 'Debe indicar el tipo de mantenimiento (Preventivo o Correctivo).')
        return redirect('calendario_mantenciones')

    form = ProgramarMantenimientoForm(request.POST)
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
        return redirect('calendario_mantenciones')

    mantenimiento = form.save(commit=False)
    mantenimiento.tipo_mantencion = tipo
    mantenimiento.estado = 'Programado' if tipo == 'Preventivo' else 'En taller'
    mantenimiento.costo_mano_obra = 0
    mantenimiento.costo_repuestos = 0

    if mantenimiento.cuenta_presupuestaria and mantenimiento.vehiculo:
        anio = mantenimiento.fecha_ingreso.year
        presupuesto = Presupuesto.objects.filter(
            cuenta=mantenimiento.cuenta_presupuestaria,
            anio=anio,
            activo=True
        ).first()
        if not presupuesto:
            messages.error(request,
                f"No hay presupuesto asignado para la cuenta {mantenimiento.cuenta_presupuestaria.codigo} "
                f"en el año {anio}. Debe crear un presupuesto primero."
            )
            return redirect('calendario_mantenciones')
        if mantenimiento.costo_estimado and mantenimiento.costo_estimado > 0 and presupuesto.disponible < mantenimiento.costo_estimado:
            messages.error(request,
                f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                f"Requerido: ${mantenimiento.costo_estimado:.0f}"
            )
            return redirect('calendario_mantenciones')

    try:
        mantenimiento.save()
        vehiculo = mantenimiento.vehiculo
        vehiculo.estado = 'En mantenimiento'
        vehiculo.save()
        if tipo == 'Preventivo':
            messages.success(request, 'Mantenimiento preventivo programado exitosamente.')
        else:
            messages.success(request, 'Mantenimiento correctivo registrado exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al guardar: {str(e)}')

    return redirect('listar_mantenimientos')


# RF_20: Listar mantenimientos
@login_required
def listar_mantenimientos(request):
    # Exportar planilla Excel si se solicita
    if request.GET.get('exportar') == 'planilla':
        anio = request.GET.get('anio', timezone.now().year)
        try:
            anio = int(anio)
        except (ValueError, TypeError):
            anio = timezone.now().year
        return exportar_planilla_mantenimientos_excel(anio)
    
    mantenimientos = Mantenimiento.objects.all()
    
    # Filtros
    patente_filter = request.GET.get('patente')
    anio_filter = request.GET.get('anio')
    tipo_filter = request.GET.get('tipo')
    estado_filter = request.GET.get('estado')
    desde_filter = request.GET.get('desde', '')
    hasta_filter = request.GET.get('hasta', '')
    proveedor_filter = request.GET.get('proveedor')
    
    if patente_filter:
        mantenimientos = mantenimientos.filter(vehiculo__patente=patente_filter)

    if anio_filter:
        try:
            anio_filter = int(anio_filter)
            mantenimientos = mantenimientos.filter(fecha_ingreso__year=anio_filter)
        except (ValueError, TypeError):
            anio_filter = ''
    
    if tipo_filter:
        mantenimientos = mantenimientos.filter(tipo_mantencion=tipo_filter)
    
    if estado_filter:
        mantenimientos = mantenimientos.filter(estado=estado_filter)
    
    if desde_filter:
        mantenimientos = mantenimientos.filter(fecha_ingreso__gte=desde_filter)
    
    if hasta_filter:
        mantenimientos = mantenimientos.filter(fecha_ingreso__lte=hasta_filter)
    
    if proveedor_filter:
        mantenimientos = mantenimientos.filter(proveedor__id=proveedor_filter)
    
    mantenimientos = mantenimientos.order_by('-fecha_ingreso')
    
    # Obtener datos para filtros
    vehiculos = Vehiculo.objects.all().order_by('patente')
    proveedores = Proveedor.objects.filter(es_taller=True, activo=True).order_by('nombre_fantasia')
    anios_disponibles = Mantenimiento.objects.dates('fecha_ingreso', 'year', order='DESC')
    
    anio_export = anio_filter if anio_filter else timezone.now().year

    return render(request, 'flota/listar_mantenimientos.html', {
        'mantenimientos': mantenimientos,
        'vehiculos': vehiculos,
        'proveedores': proveedores,
        'patente_filter': patente_filter,
        'anio_filter': anio_filter,
        'tipo_filter': tipo_filter,
        'estado_filter': estado_filter,
        'desde_filter': desde_filter,
        'hasta_filter': hasta_filter,
        'proveedor_filter': proveedor_filter,
        'anios_disponibles': anios_disponibles,
        'anio_export': anio_export,
    })

# Cambiar estado de mantenimiento (AJAX)
# El paso a "Finalizado" solo se permite desde finalizar_mantenimiento (con OC y costos).
@login_required
@user_passes_test(es_administrador)
@require_POST
def cambiar_estado_mantenimiento(request, id):
    import json
    mantenimiento = get_object_or_404(Mantenimiento, id=id)
    
    try:
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        if nuevo_estado == 'Finalizado':
            return JsonResponse({
                'success': False,
                'error': 'Para finalizar use la opción "Finalizar mantenimiento" e ingrese costos y Orden de Compra.'
            }, status=400)
        
        if nuevo_estado in dict(Mantenimiento.ESTADOS):
            mantenimiento.estado = nuevo_estado
            mantenimiento.save()
            
            vehiculo = mantenimiento.vehiculo
            if nuevo_estado in ['En taller', 'Esperando repuestos']:
                vehiculo.estado = 'En mantenimiento'
                vehiculo.save()
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Estado inválido'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(es_administrador)
def editar_mantenimiento(request, id):
    mantenimiento = get_object_or_404(Mantenimiento, id=id)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        if form.is_valid():
            try:
                mant = form.save()
                if mant.estado == 'Finalizado':
                    mant.ejecutar_cierre_presupuestario()
                messages.success(request, 'Mantenimiento actualizado correctamente.')
                return redirect('listar_mantenimientos')
            except Exception as e:
                messages.error(request, f'Error al actualizar mantenimiento: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = MantenimientoForm(instance=mantenimiento)
    
    return render(request, 'flota/editar_mantenimiento.html', {
        'form': form, 
        'mantenimiento': mantenimiento
    })


@login_required
@user_passes_test(es_administrador)
def finalizar_mantenimiento(request, id):
    mantenimiento = get_object_or_404(Mantenimiento, id=id)
    
    if request.method == 'POST':
        form = FinalizarMantenimientoForm(request.POST, request.FILES, instance=mantenimiento)
        if form.is_valid():
            mant = form.save(commit=False)
            mant.costo_total_real = (mant.costo_mano_obra or 0) + (mant.costo_repuestos or 0)
            mant.estado = 'Finalizado'

            if not mant.cuenta_presupuestaria and mant.orden_compra:
                mant.cuenta_presupuestaria = mant.orden_compra.cuenta_presupuestaria
                if not mant.cuenta_presupuestaria:
                    messages.error(request, "La Orden de Compra seleccionada no tiene cuenta presupuestaria. No se puede finalizar.")
                    return render(request, 'flota/finalizar_mantenimiento.html', {'form': form, 'mantenimiento': mantenimiento})

            try:
                mant.save()
            except (ValueError, ValidationError) as e:
                messages.error(request, str(e))
                return render(request, 'flota/finalizar_mantenimiento.html', {
                    'form': form,
                    'mantenimiento': mantenimiento
                })
            try:
                mant.ejecutar_cierre_presupuestario()
            except ValueError as e:
                messages.error(request, str(e))
                return render(request, 'flota/finalizar_mantenimiento.html', {
                    'form': form,
                    'mantenimiento': mantenimiento
                })

            vehiculo = mant.vehiculo
            vehiculo.estado = 'Disponible'
            vehiculo.save()

            messages.success(request, 'Mantenimiento finalizado y presupuesto actualizado.')
            return redirect('listar_mantenimientos')

    else:
        form = FinalizarMantenimientoForm(instance=mantenimiento, initial={'fecha_salida': timezone.now().date()})
        form.fields['orden_compra'].queryset = OrdenCompra.objects.filter(
            vehiculo=mantenimiento.vehiculo,
            estado__in=['EMITIDA', 'ACEPTADA']
        ).order_by('-fecha_emision')

    return render(request, 'flota/finalizar_mantenimiento.html', {
        'form': form,
        'mantenimiento': mantenimiento
    })
    

@login_required
@user_passes_test(es_administrador)
def eliminar_mantenimiento(request, id):
    mantenimiento = get_object_or_404(Mantenimiento, id=id)
    if request.method == 'POST':
        mantenimiento.delete()
        messages.success(request, 'Mantenimiento eliminado correctamente.')
        return redirect('calendario_mantenciones')

    return render(request, 'flota/eliminar_mantenimiento.html', {'mantenimiento': mantenimiento})


# RF_23: Visualizar calendario de mantenciones
@login_required
def calendario_mantenciones(request):
    vehiculos = Vehiculo.objects.all().order_by('patente')
    proveedores = Proveedor.objects.filter(es_taller=True, activo=True).order_by('nombre_fantasia')
    cuentas = CuentaPresupuestaria.objects.all().order_by('codigo')
    orden_trabajo_id = request.GET.get('orden_trabajo', '').strip()
    orden_trabajo = get_object_or_404(OrdenTrabajo, id=orden_trabajo_id) if orden_trabajo_id else None
    abrir_modal = request.GET.get('abrir_modal') == '1' or bool(orden_trabajo_id)
    cuentas_list = [
        {'id': c.id, 'codigo': c.codigo, 'nombre': c.nombre}
        for c in cuentas
    ]

    mapa_json = {
        f"{tipo}_{criticidad}": ids
        for (tipo, criticidad), ids in mapa_mantenimiento_cuenta_ids().items()
    }

    return render(request, 'flota/calendario_mantenciones.html', {
        'vehiculos': vehiculos,
        'proveedores': proveedores,
        'cuentas': cuentas,
        'cuentas_json': json.dumps(cuentas_list),
        'mapa_cuentas_json': json.dumps(mapa_json),
        'orden_trabajo': orden_trabajo,
        'abrir_modal': abrir_modal,
    })


@login_required
def api_mantenimientos(request):
    mantenimientos = Mantenimiento.objects.all()
    eventos = []
    
    for m in mantenimientos:
        color = '#3788d8'
        if m.estado == 'En taller':
            color = '#dc3545'
        elif m.estado == 'Finalizado':
            color = '#198754'

        start_date = m.fecha_ingreso.isoformat() if m.fecha_ingreso else None
        end_date = m.fecha_salida.isoformat() if m.fecha_salida else None
        
        eventos.append({
            'id': m.id,
            'title': f"{m.vehiculo.patente} - {m.get_tipo_mantencion_display()}",
            'start': start_date,
            'end': end_date,
            'color': color,
            'extendedProps': {
                'descripcion': m.descripcion_trabajo or 'Sin observaciones',
                'estado': m.get_estado_display(),
                'costo': str(m.costo_total_real) if m.costo_total_real else '0'
            }
        })
        
    return JsonResponse(eventos, safe=False)
