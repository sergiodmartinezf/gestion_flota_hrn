from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from ..models import Arriendo, Mantenimiento, Vehiculo, Proveedor
from ..forms import ArriendoForm, VehiculoForm
from .utilidades import es_administrador


@login_required
def listar_arriendos(request):
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'
    
    if mostrar_deshabilitados:
        arriendos = Arriendo.objects.all().order_by('-fecha_inicio')
    else:
        arriendos = Arriendo.objects.filter(activo=True).order_by('-fecha_inicio')

    estado_filter = request.GET.get('estado')
    proveedor_filter = request.GET.get('proveedor')
    desde_filter = request.GET.get('desde', '')
    hasta_filter = request.GET.get('hasta', '')
    
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
        'mostrar_deshabilitados': mostrar_deshabilitados,
    })


# RF_26: Registrar arriendo
@login_required
@user_passes_test(es_administrador)
def registrar_arriendo(request):
    existen_arrendados = Vehiculo.objects.filter(tipo_propiedad='Arrendado').exists()
    modo_inicial = 'existente' if existen_arrendados else 'nuevo'
    
    if request.method == 'POST':
        modo = request.POST.get('modo_vehiculo_arriendo')
        arriendo_form = ArriendoForm(request.POST)
        
        if modo == 'existente':
            if arriendo_form.is_valid():
                arriendo = arriendo_form.save()
                messages.success(request, 'Arriendo registrado exitosamente.')
                return redirect('listar_arriendos')
            else:
                vehiculo_form = VehiculoForm()
                modo_inicial = 'existente'
        else:  # nuevo
            vehiculo_form = VehiculoForm(request.POST)
            if arriendo_form.is_valid() and vehiculo_form.is_valid():
                nuevo_vehiculo = vehiculo_form.save(commit=False)
                nuevo_vehiculo.tipo_propiedad = 'Arrendado'
                nuevo_vehiculo.estado = 'Disponible'
                nuevo_vehiculo.save()
                
                arriendo = arriendo_form.save(commit=False)
                arriendo.vehiculo_arrendado = nuevo_vehiculo
                arriendo.save()
                messages.success(request, 'Arriendo registrado exitosamente con nuevo vehículo.')
                return redirect('listar_arriendos')
            else:
                modo_inicial = 'nuevo'
    else:
        arriendo_form = ArriendoForm()
        vehiculo_form = VehiculoForm(initial={
            'tipo_propiedad': 'Arrendado',
            'estado': 'Disponible',
            'establecimiento': 'Hospital Río Negro',
            'criticidad': 'No crítico',
            'anio_adquisicion': timezone.now().year,
            'es_samu': False,
            'es_backup': False,
        })
    
    return render(request, 'flota/registrar_arriendo.html', {
        'arriendo_form': arriendo_form,
        'vehiculo_form': vehiculo_form,
        'existen_arrendados': existen_arrendados,
        'modo_inicial': modo_inicial,
    })


@login_required
@user_passes_test(es_administrador)
def finalizar_arriendo(request, id):
    arriendo = get_object_or_404(Arriendo, id=id)
    
    if request.method == 'POST':
        arriendo.estado = 'Finalizado'
        arriendo.fecha_fin = timezone.now().date()
        arriendo.save()

        vehiculo_arrendado = arriendo.vehiculo_arrendado
        vehiculo_arrendado.estado = 'Fuera de servicio'
        vehiculo_arrendado.save()
        messages.info(request, f'Vehículo arrendado {vehiculo_arrendado.patente} marcado como Fuera de servicio.')

        if arriendo.vehiculo_reemplazado:
            vehiculo = arriendo.vehiculo_reemplazado
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
    