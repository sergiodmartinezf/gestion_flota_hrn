from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from ..models import Arriendo, Mantenimiento, Vehiculo, Proveedor
from ..forms import ArriendoForm
from .utilidades import es_administrador


@login_required
def listar_arriendos(request):
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'
    
    if mostrar_deshabilitados:
        arriendos = Arriendo.objects.all().order_by('-fecha_inicio')
    else:
        arriendos = Arriendo.objects.filter(activo=True).order_by('-fecha_inicio')
    
    # El resto de los filtros (estado, proveedor, fechas) se aplican después
    estado_filter = request.GET.get('estado')
    proveedor_filter = request.GET.get('proveedor')
    desde_filter = request.GET.get('desde')
    hasta_filter = request.GET.get('hasta')
    
    if estado_filter:
        arriendos = arriendos.filter(estado=estado_filter)
    
    if proveedor_filter:
        arriendos = arriendos.filter(proveedor__id=proveedor_filter)
    
    if desde_filter:
        arriendos = arriendos.filter(fecha_inicio__gte=desde_filter)
    
    if hasta_filter:
        arriendos = arriendos.filter(fecha_inicio__lte=hasta_filter)
    
    arriendos = arriendos.order_by('-fecha_inicio')
    
    proveedores = Proveedor.objects.filter(es_arrendador=True, activo=True).order_by('nombre_fantasia')
    
    return render(request, 'flota/listar_arriendos.html', {
        'arriendos': arriendos,
        'proveedores': proveedores,
        'estado_filter': estado_filter,
        'proveedor_filter': proveedor_filter,
        'desde_filter': desde_filter,
        'hasta_filter': hasta_filter,
        'mostrar_deshabilitados': mostrar_deshabilitados,  # Nuevo
    })


# RF_26: Registrar arriendo
@login_required
@user_passes_test(es_administrador)
def registrar_arriendo(request):
    if request.method == 'POST':
        form = ArriendoForm(request.POST)
        if form.is_valid():
            arriendo = form.save()
            # Actualizar estado del vehículo reemplazado
            if arriendo.vehiculo_reemplazado:
                vehiculo = arriendo.vehiculo_reemplazado
                # Verificar si ya está fuera de servicio
                if vehiculo.estado != 'Fuera de servicio':
                    vehiculo.estado = 'Fuera de servicio'
                    vehiculo.save()
                    messages.info(request, f'Vehículo {vehiculo.patente} marcado como Fuera de servicio.')
            messages.success(request, 'Arriendo registrado exitosamente.')
            return redirect('listar_arriendos')
    else:
        form = ArriendoForm()
    
    vehiculos_arrendados_existentes = Vehiculo.objects.filter(
        tipo_propiedad='Arrendado'
    ).exists()

    return render(request, 'flota/registrar_arriendo.html', {
        'form': form,
        'vehiculos_arrendados_existentes': vehiculos_arrendados_existentes,
    })

@login_required
@user_passes_test(es_administrador)
def finalizar_arriendo(request, id):
    arriendo = get_object_or_404(Arriendo, id=id)
    
    if request.method == 'POST':
        # Actualizar arriendo
        arriendo.estado = 'Finalizado'
        arriendo.fecha_fin = timezone.now().date()
        arriendo.save()
        
        # ACTUALIZAR ESTADO DEL VEHÍCULO ARRENDADO (CORRECCIÓN)
        vehiculo_arrendado = arriendo.vehiculo_arrendado
        vehiculo_arrendado.estado = 'Fuera de servicio'
        vehiculo_arrendado.save()
        messages.info(request, f'Vehículo arrendado {vehiculo_arrendado.patente} marcado como Fuera de servicio.')
        
        # Reactivar el vehículo propio si ya está disponible
        if arriendo.vehiculo_reemplazado:
            vehiculo = arriendo.vehiculo_reemplazado
            # Verificar si el vehículo sigue en taller o ya está listo
            mantenimientos_activos = Mantenimiento.objects.filter(
                vehiculo=vehiculo,
                estado__in=['En taller', 'Esperando repuestos']
            )
            
            if mantenimientos_activos.exists():
                vehiculo.estado = 'En mantenimiento'
                messages.info(request, f'Vehículo {vehiculo.patente} sigue en mantenimiento.')
            else:
                vehiculo.estado = 'Disponible'
                messages.success(request, f'Vehículo {vehiculo.patente} reactivado y disponible.')
            
            vehiculo.save()
        
        # CORRECCIÓN: Usar vehiculo_arrendado.patente
        messages.success(request, f'Arriendo {arriendo.vehiculo_arrendado.patente} finalizado.')
        return redirect('listar_arriendos')
    
    return render(request, 'flota/finalizar_arriendo.html', {'arriendo': arriendo})
    
@login_required
@user_passes_test(es_administrador)
def deshabilitar_arriendo(request, id):
    arriendo = get_object_or_404(Arriendo, id=id)
    
    if request.method == 'POST':
        arriendo.activo = False
        arriendo.save()
        messages.success(request, f'Arriendo {arriendo.vehiculo_arrendado.patente} deshabilitado.')
        return redirect('listar_arriendos')
    
    return render(request, 'flota/deshabilitar_arriendo.html', {'arriendo': arriendo})

@login_required
@user_passes_test(es_administrador)
def habilitar_arriendo(request, id):
    arriendo = get_object_or_404(Arriendo, id=id)
    
    if request.method == 'POST':
        arriendo.activo = True
        arriendo.save()
        messages.success(request, f'Arriendo {arriendo.vehiculo_arrendado.patente} habilitado.')
        return redirect('listar_arriendos')
    
    return render(request, 'flota/habilitar_arriendo.html', {'arriendo': arriendo})
    