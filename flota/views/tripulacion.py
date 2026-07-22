from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..models import PersonaTripulacion, TripulacionViaje, ROL_TRIPULACION
from ..forms import PersonaTripulacionForm
from .utilidades import es_administrador


@login_required
@user_passes_test(es_administrador)
def listar_tripulacion(request):
    personas = PersonaTripulacion.objects.all().order_by('rol', 'nombre')

    rol = request.GET.get('rol', '').strip()
    q = request.GET.get('q', '').strip()
    if rol:
        personas = personas.filter(rol=rol)
    if q:
        personas = personas.filter(nombre__icontains=q)

    return render(request, 'flota/listar_tripulacion.html', {
        'personas': personas,
        'roles': ROL_TRIPULACION,
        'rol_filtro': rol,
        'q': q,
    })


@login_required
@user_passes_test(es_administrador)
def modificar_tripulacion(request, id):
    persona = get_object_or_404(PersonaTripulacion, id=id)

    if request.method == 'POST':
        form = PersonaTripulacionForm(request.POST, instance=persona)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            rol = form.cleaned_data['rol']

            existente = PersonaTripulacion.objects.filter(
                nombre__iexact=nombre, rol=rol,
            ).exclude(pk=persona.pk).first()

            if existente:
                # Fusionar duplicado: reasignar viajes al registro canónico
                TripulacionViaje.objects.filter(persona_tripulacion=persona).update(
                    persona_tripulacion=existente,
                    nombre=existente.nombre,
                    rol=existente.rol,
                )
                persona.delete()
                messages.success(
                    request,
                    f'Se fusionó con "{existente.nombre}" ({existente.get_rol_display()}).',
                )
                return redirect('listar_tripulacion')

            persona = form.save()
            TripulacionViaje.objects.filter(persona_tripulacion=persona).update(
                nombre=persona.nombre,
                rol=persona.rol,
            )
            messages.success(
                request,
                f'Tripulación "{persona.nombre}" actualizada correctamente.',
            )
            return redirect('listar_tripulacion')
    else:
        form = PersonaTripulacionForm(instance=persona)

    return render(request, 'flota/modificar_tripulacion.html', {
        'form': form,
        'persona': persona,
        'titulo': 'Modificar tripulación',
    })


@login_required
@user_passes_test(es_administrador)
def eliminar_tripulacion(request, id):
    persona = get_object_or_404(PersonaTripulacion, id=id)
    usos = TripulacionViaje.objects.filter(persona_tripulacion=persona).count()

    if request.method == 'POST':
        nombre = persona.nombre
        persona.delete()
        messages.success(
            request,
            f'"{nombre}" eliminado del catálogo de tripulación.',
        )
        return redirect('listar_tripulacion')

    return render(request, 'flota/eliminar_tripulacion.html', {
        'persona': persona,
        'usos': usos,
    })
