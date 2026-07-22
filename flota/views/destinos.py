from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from ..models import DireccionDestino, PacienteTraslado
from ..forms import DireccionDestinoForm
from .utilidades import es_administrador


@login_required
@user_passes_test(es_administrador)
def listar_direcciones(request):
    direcciones = DireccionDestino.objects.all().order_by('texto')
    q = request.GET.get('q', '').strip()
    if q:
        direcciones = direcciones.filter(texto__icontains=q)

    return render(request, 'flota/listar_direcciones.html', {
        'direcciones': direcciones,
        'q': q,
    })


@login_required
@user_passes_test(es_administrador)
def modificar_direccion(request, id):
    direccion = get_object_or_404(DireccionDestino, id=id)

    if request.method == 'POST':
        form = DireccionDestinoForm(request.POST, instance=direccion)
        if form.is_valid():
            texto = form.cleaned_data['texto']
            existente = DireccionDestino.objects.filter(
                texto__iexact=texto,
            ).exclude(pk=direccion.pk).first()

            if existente:
                PacienteTraslado.objects.filter(direccion_destino=direccion).update(
                    direccion_destino=existente,
                    direccion_especifica=existente.texto,
                )
                direccion.delete()
                messages.success(
                    request,
                    f'Se fusionó con "{existente.texto}".',
                )
                return redirect('listar_direcciones')

            direccion = form.save()
            PacienteTraslado.objects.filter(direccion_destino=direccion).update(
                direccion_especifica=direccion.texto,
            )
            messages.success(request, 'Dirección actualizada correctamente.')
            return redirect('listar_direcciones')
    else:
        form = DireccionDestinoForm(instance=direccion)

    return render(request, 'flota/modificar_direccion.html', {
        'form': form,
        'direccion': direccion,
        'titulo': 'Modificar dirección',
    })


@login_required
@user_passes_test(es_administrador)
def eliminar_direccion(request, id):
    direccion = get_object_or_404(DireccionDestino, id=id)
    usos = PacienteTraslado.objects.filter(direccion_destino=direccion).count()

    if request.method == 'POST':
        texto = direccion.texto
        direccion.delete()
        messages.success(
            request,
            f'"{texto}" eliminada del catálogo de direcciones.',
        )
        return redirect('listar_direcciones')

    return render(request, 'flota/eliminar_direccion.html', {
        'direccion': direccion,
        'usos': usos,
    })
