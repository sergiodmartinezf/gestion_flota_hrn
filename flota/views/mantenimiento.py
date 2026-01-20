from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import json
from ..models import Mantenimiento, Vehiculo, Proveedor, Presupuesto, AlertaMantencion, CuentaPresupuestaria
from ..forms import MantenimientoForm, ProgramarMantenimientoForm, FinalizarMantenimientoForm
from .utilidades import es_administrador
from ..utils import exportar_planilla_mantenimientos_excel

# RF_18: Programar mantenimiento preventivo
@login_required
@user_passes_test(es_administrador)
def programar_mantenimiento_preventivo(request):
    if request.method == 'POST':
        form = ProgramarMantenimientoForm(request.POST)
        if form.is_valid():
            mantenimiento = form.save(commit=False)
            
            # Se asignan valores
            mantenimiento.tipo_mantencion = 'Preventivo'
            mantenimiento.estado = 'Programado'
            
            # Costos reales parten en 0
            mantenimiento.costo_mano_obra = 0
            mantenimiento.costo_repuestos = 0
            
            # Validar presupuesto antes de guardar
            if mantenimiento.cuenta_presupuestaria and mantenimiento.vehiculo:
                anio = mantenimiento.fecha_ingreso.year
                
                # Buscar presupuesto
                presupuesto = Presupuesto.objects.filter(
                    cuenta=mantenimiento.cuenta_presupuestaria,
                    vehiculo=mantenimiento.vehiculo,
                    anio=anio,
                    activo=True
                ).first()
                
                if not presupuesto:
                    presupuesto = Presupuesto.objects.filter(
                        cuenta=mantenimiento.cuenta_presupuestaria,
                        vehiculo__isnull=True,
                        anio=anio,
                        activo=True
                    ).first()
                
                if not presupuesto:
                    messages.error(request, 
                        f"No hay presupuesto asignado para la cuenta {mantenimiento.cuenta_presupuestaria.codigo} "
                        f"en el año {anio}. Debe crear un presupuesto primero."
                    )
                    return render(request, 'flota/programar_mantenimiento_preventivo.html', {'form': form})
                
                # Verificar si hay saldo suficiente para el costo estimado
                if mantenimiento.costo_estimado and mantenimiento.costo_estimado > 0:
                    if presupuesto.disponible < mantenimiento.costo_estimado:
                        messages.error(request, 
                            f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                            f"Requerido: ${mantenimiento.costo_estimado:.0f}"
                        )
                        return render(request, 'flota/programar_mantenimiento_preventivo.html', {'form': form})
            
            mantenimiento.save()
            
            # Se actualiza el estado del vehículo
            vehiculo = mantenimiento.vehiculo
            vehiculo.estado = 'En mantenimiento'
            vehiculo.save()
            
            messages.success(request, 'Mantenimiento preventivo programado exitosamente.')
            return redirect('listar_mantenimientos')
        else:
            # Errores
            print("Errores del formulario:", form.errors)
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        # Inicializamos el formulario limpio
        form = ProgramarMantenimientoForm()
    
    return render(request, 'flota/programar_mantenimiento_preventivo.html', {'form': form})


# RF_19: Registrar mantenimiento correctivo
@login_required
@user_passes_test(es_administrador)
def registrar_mantenimiento_correctivo(request):
    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            try:
                mantenimiento = form.save(commit=False)
                mantenimiento.tipo_mantencion = 'Correctivo'
                mantenimiento.estado = 'En taller'
                
                # Calcular costo total real si se proporcionaron costos
                if mantenimiento.costo_mano_obra or mantenimiento.costo_repuestos:
                    mantenimiento.costo_total_real = (mantenimiento.costo_mano_obra or 0) + (mantenimiento.costo_repuestos or 0)
                
                # Validar presupuesto antes de guardar
                if mantenimiento.cuenta_presupuestaria and mantenimiento.vehiculo:
                    anio = mantenimiento.fecha_ingreso.year
                    
                    # Buscar presupuesto
                    presupuesto = Presupuesto.objects.filter(
                        cuenta=mantenimiento.cuenta_presupuestaria,
                        vehiculo=mantenimiento.vehiculo,
                        anio=anio,
                        activo=True
                    ).first()
                    
                    if not presupuesto:
                        presupuesto = Presupuesto.objects.filter(
                            cuenta=mantenimiento.cuenta_presupuestaria,
                            vehiculo__isnull=True,
                            anio=anio,
                            activo=True
                        ).first()
                    
                    if not presupuesto:
                        messages.error(request, 
                            f"No hay presupuesto asignado para la cuenta {mantenimiento.cuenta_presupuestaria.codigo} "
                            f"en el año {anio}. Debe crear un presupuesto primero."
                        )
                        # Re-renderizar el formulario con los datos
                        return render(request, 'flota/registrar_mantenimiento_correctivo.html', {'form': form})
                
                mantenimiento.save()
                
                # Actualizar estado del vehículo
                vehiculo = mantenimiento.vehiculo
                vehiculo.estado = 'En mantenimiento'
                vehiculo.save()
                
                messages.success(request, 'Mantenimiento correctivo registrado exitosamente.')
                return redirect('listar_mantenimientos')
            except Exception as e:
                messages.error(request, f'Error al registrar mantenimiento correctivo: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = MantenimientoForm()
        # Filtrar proveedores activos
        form.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True, es_taller=True).order_by('nombre_fantasia')
    
    return render(request, 'flota/registrar_mantenimiento_correctivo.html', {'form': form})


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
    
    patente = request.GET.get('patente')
    mantenimientos = Mantenimiento.objects.all()
    
    if patente:
        mantenimientos = mantenimientos.filter(vehiculo__patente=patente)
    
    mantenimientos = mantenimientos.order_by('-fecha_ingreso')
    
    return render(request, 'flota/listar_mantenimientos.html', {
        'mantenimientos': mantenimientos,
        'patente_filter': patente,
    })


# Cambiar estado de mantenimiento (AJAX)
@login_required
@user_passes_test(es_administrador)
@require_POST
def cambiar_estado_mantenimiento(request, id):
    import json
    mantenimiento = get_object_or_404(Mantenimiento, id=id)
    
    try:
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        if nuevo_estado in dict(Mantenimiento.ESTADOS):
            mantenimiento.estado = nuevo_estado
            mantenimiento.save()
            
            # Actualizar estado del vehículo si es necesario
            vehiculo = mantenimiento.vehiculo
            if nuevo_estado == 'Finalizado' and mantenimiento.fecha_salida:
                vehiculo.estado = 'Disponible'
                vehiculo.save()
            elif nuevo_estado in ['En taller', 'Esperando repuestos']:
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
                form.save()
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
            
            # Calcular costo total real
            costo_anterior = mant.costo_total_real
            mant.costo_total_real = (mant.costo_mano_obra or 0) + (mant.costo_repuestos or 0)
            mant.estado = 'Finalizado'
            
            # REQ: Actualizar ejecución presupuestaria
            if mant.cuenta_presupuestaria and mant.vehiculo:
                presupuesto = Presupuesto.objects.filter(
                    cuenta=mant.cuenta_presupuestaria,
                    vehiculo=mant.vehiculo,
                    anio=mant.fecha_ingreso.year,
                    activo=True
                ).first()

                if not presupuesto:
                    # Buscar global
                    presupuesto = Presupuesto.objects.filter(
                        cuenta=mant.cuenta_presupuestaria,
                        vehiculo__isnull=True,
                        anio=mant.fecha_ingreso.year,
                        activo=True
                    ).first()

                if presupuesto:
                    # Verificar que haya saldo suficiente
                    if presupuesto.disponible < mant.costo_total_real:
                        messages.error(request, 
                            f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                            f"Requerido: ${mant.costo_total_real:.0f}. No se puede finalizar el mantenimiento."
                        )
                        return render(request, 'flota/finalizar_mantenimiento.html', {
                            'form': form, 
                            'mantenimiento': mantenimiento
                        })
                else:
                    messages.error(request, 
                        f"No hay presupuesto asignado para la cuenta {mant.cuenta_presupuestaria.codigo} "
                        f"en el año {mant.fecha_ingreso.year}. No se puede finalizar el mantenimiento."
                    )
                    return render(request, 'flota/finalizar_mantenimiento.html', {
                        'form': form, 
                        'mantenimiento': mantenimiento
                    })

            try:
                mant.save()
            except ValueError as e:
                # Capturar error de presupuesto insuficiente
                messages.error(request, str(e))
                return render(request, 'flota/finalizar_mantenimiento.html', {
                    'form': form, 
                    'mantenimiento': mantenimiento
                })

            # Liberar vehículo
            vehiculo = mant.vehiculo
            vehiculo.estado = 'Disponible'
            vehiculo.save()

            messages.success(request, 'Mantenimiento finalizado y presupuesto actualizado.')
            return redirect('listar_mantenimientos')

    else:
        # Fecha de salida como hoy por defecto
        form = FinalizarMantenimientoForm(instance=mantenimiento, initial={'fecha_salida': timezone.now().date()})

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
    
    # Renderizar una confirmación simple
    return render(request, 'flota/eliminar_mantenimiento.html', {'mantenimiento': mantenimiento})


# RF_23: Visualizar calendario de mantenciones
@login_required
def calendario_mantenciones(request):
    vehiculos = Vehiculo.objects.all().order_by('patente')
    proveedores = Proveedor.objects.filter(es_taller=True, activo=True).order_by('nombre_fantasia')
    return render(request, 'flota/calendario_mantenciones.html', {
        'vehiculos': vehiculos,
        'proveedores': proveedores,
    })


@login_required
def api_mantenimientos(request):
    mantenimientos = Mantenimiento.objects.all()
    eventos = []
    
    for m in mantenimientos:
        # Definir colores según estado
        color = '#3788d8' # Azul (Programado)
        if m.estado == 'En taller':
            color = '#dc3545' # Rojo
        elif m.estado == 'Finalizado':
            color = '#198754' # Verde
            
        # Asegurar que las fechas estén correctamente formateadas
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
