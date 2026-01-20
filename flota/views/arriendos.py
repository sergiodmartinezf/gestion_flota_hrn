from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from ..models import Arriendo, Mantenimiento, Vehiculo
from ..forms import ArriendoForm
from .utilidades import es_administrador

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
                vehiculo.estado = 'Fuera de servicio'
                vehiculo.save()
            messages.success(request, 'Arriendo registrado exitosamente.')
            return redirect('listar_arriendos')
    else:
        form = ArriendoForm()
    
    return render(request, 'flota/registrar_arriendo.html', {'form': form})


@login_required
def listar_arriendos(request):
    arriendos = Arriendo.objects.all().order_by('-fecha_inicio')
    return render(request, 'flota/listar_arriendos.html', {'arriendos': arriendos})


@login_required
@user_passes_test(es_administrador)
def finalizar_arriendo(request, id):
    arriendo = get_object_or_404(Arriendo, id=id)
    
    if request.method == 'POST':
        # Actualizar arriendo
        arriendo.estado = 'Finalizado'
        arriendo.fecha_fin = timezone.now().date()
        arriendo.save()
        
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
        
        messages.success(request, f'Arriendo {arriendo.patente_arrendada} finalizado.')
        return redirect('listar_arriendos')
    
    return render(request, 'flota/finalizar_arriendo.html', {'arriendo': arriendo})


