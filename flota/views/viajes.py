from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
import xlwt
from ..models import HojaRuta, CargaCombustible, FallaReportada, AlertaMantencion, Viaje, Vehiculo, Usuario, Paciente, ViajePaciente
from ..forms import HojaRutaForm, CargaCombustibleForm, FallaReportadaForm, ViajeForm
from .utilidades import es_conductor_o_admin, es_administrador


@login_required
def acceso_bitacora(request):
    """
    Despachador inteligente:
    - Si es Admin/Visualizador -> Lista de bitácoras.
    - Si es Conductor -> Busca hoja abierta HOY.
      - Si tiene hoja abierta -> Pantalla agregar viaje.
      - Si NO tiene hoja abierta -> Pantalla crear nueva hoja.
    """
    if request.user.rol in ['Administrador', 'Visualizador']:
        return redirect('listar_bitacoras')

    if request.user.rol == 'Conductor':
        # Buscamos una hoja de ruta creada HOY por este conductor.
        # Asumimos que si existe una hoja con fecha de hoy, es la activa.
        hoja_activa = HojaRuta.objects.filter(
            conductor=request.user, 
            fecha=timezone.now().date()
        ).order_by('-creado_en').first()

        # Lógica adicional: Si el sistema marca km_fin como cierre definitivo, podríamos filtrar por km_fin__isnull=True
        # Pero como el sistema actual actualiza km_fin con cada viaje, usamos la fecha como indicador de turno activo.
        
        if hoja_activa:
            # Mensaje opcional de bienvenida
            # messages.info(request, f'Retomando turno activo en móvil {hoja_activa.vehiculo.patente}')
            return redirect('agregar_viaje', id=hoja_activa.id)
        else:
            return redirect('registrar_bitacora')
    
    # Fallback por defecto
    return redirect('listar_bitacoras')

@login_required
def cerrar_hoja_ruta(request, id):
    hoja = get_object_or_404(HojaRuta, id=id)
    
    # Seguridad: solo el conductor dueño o un admin pueden cerrar
    if request.user != hoja.conductor and request.user.rol != 'Administrador':
        messages.error(request, "No tienes permiso para cerrar esta hoja de ruta.")
        return redirect('agregar_viaje', id=hoja.id)

    if request.method == 'POST':
        try:
            km_final_input = request.POST.get('km_cierre')
            
            if not km_final_input:
                messages.error(request, "Debe ingresar el kilometraje final.")
                return redirect('agregar_viaje', id=hoja.id)
                
            km_final = int(km_final_input)
            
            # Validación lógica básica
            if km_final < hoja.km_inicio:
                messages.error(request, f"El KM final ({km_final}) no puede ser menor al inicial ({hoja.km_inicio}).")
                return redirect('agregar_viaje', id=hoja.id)

            # Validar contra el último viaje si existe
            ultimo_viaje = hoja.viajes.order_by('km_fin_viaje').last()
            if ultimo_viaje and km_final < ultimo_viaje.km_fin_viaje:
                messages.warning(request, f"Atención: El KM de cierre es menor al del último viaje registrado ({ultimo_viaje.km_fin_viaje}).")
            
            # Guardar cierre
            hoja.km_fin = km_final
            hoja.save()
            
            # Actualizar KM del vehículo también para asegurar sincronía
            vehiculo = hoja.vehiculo
            if km_final > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = km_final
                vehiculo.save()

            messages.success(request, f"Turno cerrado correctamente. KM Final: {km_final}. Total recorrido: {hoja.km_recorridos} km.")
            return redirect('listar_bitacoras')
            
        except ValueError:
            messages.error(request, "El kilometraje debe ser un número válido.")
            return redirect('agregar_viaje', id=hoja.id)
            
    return redirect('agregar_viaje', id=hoja.id)

# RF_15: Registrar bitácora (Hoja de Ruta)
@login_required
@user_passes_test(es_conductor_o_admin)
def registrar_bitacora(request):
    """
    RF_15: Registrar bitácora (Hoja de Ruta) - VERSIÓN SIMPLIFICADA
    Ahora solo crea la hoja de ruta, luego redirige a agregar_viaje para el primer viaje
    """
    if request.method == 'POST':
        form = HojaRutaForm(request.POST)
        
        if form.is_valid():
            try:
                # 1. Guardar Hoja de Ruta SOLAMENTE
                hoja_ruta = form.save(commit=False)
                hoja_ruta.conductor = request.user
                hoja_ruta.save()
                
                # 2. Determinar si es camioneta para pasar contexto a la siguiente vista
                es_camioneta = False
                if hoja_ruta.vehiculo and hoja_ruta.vehiculo.tipo_carroceria == 'Camioneta':
                    es_camioneta = True
                
                # 3. Guardar flag en sesión para que agregar_viaje sepa que es hoja nueva
                request.session['hoja_nueva_id'] = hoja_ruta.id
                request.session['es_camioneta'] = es_camioneta
                
                messages.success(request, f'Hoja de ruta creada exitosamente. Ahora registre el primer viaje.')
                
                # 4. Redirigir a agregar_viaje para el primer viaje
                return redirect('agregar_viaje', id=hoja_ruta.id)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            # Mostrar errores detallados
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = HojaRutaForm()
    
    return render(request, 'flota/registrar_bitacora_conductor.html', {
        'form': form
    })


@login_required
@user_passes_test(es_conductor_o_admin)
def agregar_viaje(request, id):
    """
    Versión modificada con campos de personal médico en el viaje
    """
    hoja_ruta = get_object_or_404(HojaRuta, id=id)
    
    # Verificar si es una hoja recién creada (primer viaje)
    es_hoja_nueva = request.session.get('hoja_nueva_id') == id
    es_camioneta = hoja_ruta.vehiculo.tipo_carroceria == 'Camioneta' if hoja_ruta.vehiculo else False
    
    # Si es hoja nueva y es camioneta, pre-poblar algunos datos
    initial_data = {}
    if es_hoja_nueva and es_camioneta:
        # Para camionetas, pre-poblar con valores por defecto
        initial_data = {
            'tipo_servicio': 'Otros',
            'km_inicio_viaje': hoja_ruta.km_inicio or hoja_ruta.vehiculo.kilometraje_actual
        }
        # Limpiar la sesión
        if 'hoja_nueva_id' in request.session:
            del request.session['hoja_nueva_id']
        if 'es_camioneta' in request.session:
            del request.session['es_camioneta']
    
    if request.method == 'POST':
        form = ViajeForm(request.POST, hoja_ruta=hoja_ruta)
        if form.is_valid():
            viaje = form.save(commit=False)
            viaje.hoja_ruta = hoja_ruta
            
            # Establecer campos vacíos para camionetas
            if es_camioneta:
                viaje.medico = ''
                viaje.enfermero = ''
                viaje.tens = ''
                viaje.camillero = ''
                viaje.sin_enfermero = True
                viaje.sin_camillero = True
            
            viaje.save()

            # --- Pacientes adicionales ---
            pacientes_extra_rut = request.POST.getlist('pacientes_extra_rut[]')
            pacientes_extra_nombre = request.POST.getlist('pacientes_extra_nombre[]')
            pacientes_extra_servicio = request.POST.getlist('pacientes_extra_servicio[]')
            for rut, nombre, servicio in zip(pacientes_extra_rut, pacientes_extra_nombre, pacientes_extra_servicio):
                rut = (rut or '').strip()
                nombre = (nombre or '').strip()
                
                if not rut and not nombre:
                    continue
                
                if rut:
                    paciente, _ = Paciente.objects.get_or_create(
                        rut=rut,
                        defaults={'nombre': nombre or rut}
                    )
                    if nombre and paciente.nombre != nombre:
                        paciente.nombre = nombre
                        paciente.save(update_fields=['nombre'])
                else:
                    paciente = Paciente.objects.create(
                        rut=f"SIN-RUT-{timezone.now().timestamp()}",
                        nombre=nombre
                    )
                
                ViajePaciente.objects.create(
                    viaje=viaje, 
                    paciente=paciente,
                    tipo_servicio=servicio
                )
                
            # Actualizar vehículo con el KM más alto registrado
            vehiculo = hoja_ruta.vehiculo
            if viaje.km_fin_viaje > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = viaje.km_fin_viaje
                vehiculo.save()
                
                # Alertas por kilometraje
                if vehiculo.umbral_mantencion > 0 and vehiculo.kilometraje_para_mantencion <= 1000:
                    if not AlertaMantencion.objects.filter(
                        vehiculo=vehiculo, vigente=True,
                        descripcion__icontains='Próximo mantenimiento por km'
                    ).exists():
                        AlertaMantencion.objects.create(
                            vehiculo=vehiculo,
                            descripcion=f'Próximo mantenimiento por km ({vehiculo.kilometraje_para_mantencion} km restantes)',
                            valor_umbral=vehiculo.kilometraje_actual,
                        )
            
            # Actualizar KM de la hoja de ruta
            primer_viaje = hoja_ruta.viajes.order_by('hora_salida', 'km_inicio_viaje').first()
            ultimo_viaje = hoja_ruta.viajes.order_by('hora_salida', 'km_inicio_viaje').last()
            
            if primer_viaje:
                hoja_ruta.km_inicio = primer_viaje.km_inicio_viaje
            
            if ultimo_viaje:
                hoja_ruta.km_fin = ultimo_viaje.km_fin_viaje
            
            hoja_ruta.save()

            # Mensaje diferente si es primer viaje
            if es_hoja_nueva:
                messages.success(request, f'Primer viaje registrado: {viaje.km_recorridos_calculados} km recorridos. Puede agregar más viajes o cerrar el turno.')
            else:
                messages.success(request, f'Viaje registrado: {viaje.km_recorridos_calculados} km recorridos')
            
            return redirect('agregar_viaje', id=hoja_ruta.id)
        else:
            messages.error(request, 'No se pudo registrar el viaje. Verifique los errores arriba del formulario.')
            print("Errores formulario viaje:", form.errors)

    else:
        # Pre-llenado inteligente para el siguiente viaje
        ultimo_viaje = hoja_ruta.viajes.last()
        
        if ultimo_viaje:
            initial_data['km_inicio_viaje'] = ultimo_viaje.km_fin_viaje
        else:
            # Si es el PRIMER viaje, sugerimos el kilometraje actual del vehículo
            initial_data['km_inicio_viaje'] = hoja_ruta.vehiculo.kilometraje_actual
            
        form = ViajeForm(hoja_ruta=hoja_ruta, initial=initial_data)
    
    # Calcular resumen
    total_km_viajes = sum(v.km_recorridos_calculados for v in hoja_ruta.viajes.all())
    
    return render(request, 'flota/agregar_viaje.html', {
        'form': form,
        'hoja_ruta': hoja_ruta,
        'viajes_existentes': hoja_ruta.viajes.all(),
        'total_km_viajes': total_km_viajes,
        'es_hoja_nueva': es_hoja_nueva,
        'es_camioneta': es_camioneta
    })

    
@login_required
def listar_bitacoras(request):
    # Filtro base según rol de usuario
    if request.user.rol == 'Conductor':
        bitacoras = HojaRuta.objects.filter(conductor=request.user).order_by('-fecha', '-creado_en')
    else:
        bitacoras = HojaRuta.objects.all()

    messages.info(request, f'Mostrando {bitacoras.count()} bitácoras')

    # Filtro por vehículo
    vehiculo_filtro = request.GET.get('vehiculo')
    if vehiculo_filtro:
        bitacoras = bitacoras.filter(vehiculo__patente=vehiculo_filtro)

    bitacoras = bitacoras.order_by('-fecha', '-creado_en')

    # Obtener lista de vehículos para el filtro
    vehiculos = Vehiculo.objects.all().order_by('patente')

    return render(request, 'flota/listar_bitacoras.html', {
        'bitacoras': bitacoras,
        'vehiculos': vehiculos,
        'vehiculo_filtro': vehiculo_filtro
    })


# --- NUEVA VISTA MODIFICAR BITÁCORA (REQ: Admin edita info de conductor) ---
@login_required
@user_passes_test(es_administrador)
def modificar_bitacora(request, id):
    hoja = get_object_or_404(HojaRuta, id=id)
    
    if request.method == 'POST':
        form = HojaRutaForm(request.POST, instance=hoja)
        if form.is_valid():
            form.save()
            messages.success(request, f'Hoja de ruta {hoja.id} actualizada exitosamente.')
            return redirect('detalle_bitacora', id=hoja.id)
    else:
        form = HojaRutaForm(instance=hoja)
    
    return render(request, 'flota/modificar_bitacora.html', {
        'form': form,
        'hoja': hoja
    })


# --- NUEVA VISTA DETALLE BITÁCORA ---
@login_required
def detalle_bitacora(request, id):
    hoja = get_object_or_404(HojaRuta, id=id)
    viajes = hoja.viajes.all()
    
    # Calcular totales
    total_km_viajes = sum(v.km_recorridos_calculados for v in viajes)
    
    # Calcular KM final de la hoja (máximo KM de los viajes)
    if viajes.exists():
        km_fin_hoja = max(v.km_fin_viaje for v in viajes)
        hoja.km_fin = km_fin_hoja
        hoja.save(update_fields=['km_fin'])
    else:
        km_fin_hoja = hoja.km_inicio

    return render(request, 'flota/detalle_bitacora.html', {
        'hoja': hoja,
        'viajes': viajes,
        'total_km_viajes': total_km_viajes,
        'km_fin_hoja': km_fin_hoja,
    })


# RF_16: Registrar carga de combustible
@login_required
@user_passes_test(es_conductor_o_admin)
def registrar_carga_combustible(request):
    if request.method == 'POST':
        form = CargaCombustibleForm(request.POST)
        if form.is_valid():
            try:
                carga = form.save(commit=False)
                if request.user.rol == 'Conductor':
                    carga.conductor = request.user
                carga.save()
                # Actualizar kilometraje del vehículo
                if carga.kilometraje_al_cargar:
                    vehiculo = carga.patente_vehiculo
                    if carga.kilometraje_al_cargar > vehiculo.kilometraje_actual:
                        vehiculo.kilometraje_actual = carga.kilometraje_al_cargar
                        vehiculo.save()
                messages.success(request, 'Carga de combustible registrada exitosamente.')
                return redirect('listar_cargas_combustible')
            except Exception as e:
                messages.error(request, f'Error al registrar carga de combustible: {str(e)}')
        else:
            # Mostrar errores específicos
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CargaCombustibleForm()
    
    return render(request, 'flota/registrar_carga_combustible.html', {'form': form})


@login_required
def listar_cargas_combustible(request):
    # Filtro base según rol de usuario
    if request.user.rol == 'Conductor':
        cargas = CargaCombustible.objects.filter(conductor=request.user).order_by('-fecha')
    else:
        cargas = CargaCombustible.objects.all()

    # Filtro por vehículo
    vehiculo_filtro = request.GET.get('vehiculo')
    if vehiculo_filtro:
        cargas = cargas.filter(patente_vehiculo__patente=vehiculo_filtro)

    cargas = cargas.order_by('-fecha')

    # Obtener lista de vehículos para el filtro
    vehiculos = Vehiculo.objects.all().order_by('patente')

    return render(request, 'flota/listar_cargas_combustible.html', {
        'cargas': cargas,
        'vehiculos': vehiculos,
        'vehiculo_filtro': vehiculo_filtro
    })


# RF_17: Registrar incidente (Falla Reportada)
@login_required
@user_passes_test(es_conductor_o_admin)
def registrar_incidente(request):
    if request.method == 'POST':
        form = FallaReportadaForm(request.POST)
        if form.is_valid():
            try:
                falla = form.save(commit=False)
                falla.conductor = request.user
                falla.save()
                
                # Crear alerta: por falla (km >= umbral) o por reporte de desempeño del conductor
                vehiculo = falla.vehiculo
                if falla.tipo_reporte == 'Desempeño':
                    AlertaMantencion.objects.create(
                        vehiculo=vehiculo,
                        descripcion=f'Reporte de desempeño del conductor: {falla.descripcion}',
                        valor_umbral=vehiculo.kilometraje_actual,
                    )
                elif vehiculo.umbral_mantencion > 0 and vehiculo.kilometraje_actual >= vehiculo.umbral_mantencion:
                    AlertaMantencion.objects.create(
                        vehiculo=vehiculo,
                        descripcion=f'Falla reportada: {falla.descripcion}',
                        valor_umbral=vehiculo.kilometraje_actual,
                    )
                
                messages.success(request, 'Incidente registrado exitosamente.')
                return redirect('listar_incidentes')
            except Exception as e:
                messages.error(request, f'Error al registrar incidente: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = FallaReportadaForm()
        # Establecer fecha actual por defecto
        if not form.instance.pk:
            from datetime import date
            form.fields['fecha_reporte'].initial = date.today()
    
    return render(request, 'flota/registrar_incidente.html', {'form': form})


@login_required
def listar_incidentes(request):
    # Filtro base según rol de usuario
    if request.user.rol == 'Conductor':
        incidentes = FallaReportada.objects.filter(conductor=request.user).order_by('-fecha_reporte')
    else:
        incidentes = FallaReportada.objects.all()

    # Filtro por vehículo
    vehiculo_filtro = request.GET.get('vehiculo')
    if vehiculo_filtro:
        incidentes = incidentes.filter(vehiculo__patente=vehiculo_filtro)

    incidentes = incidentes.order_by('-fecha_reporte')

    # Obtener lista de vehículos para el filtro
    vehiculos = Vehiculo.objects.all().order_by('patente')
    print(f"DEBUG incidentes: {vehiculos.count()} vehículos encontrados para filtro")

    return render(request, 'flota/listar_incidentes.html', {
        'incidentes': incidentes,
        'vehiculos': vehiculos,
        'vehiculo_filtro': vehiculo_filtro
    })


# --- Formulario para exportar traslados con filtros ---
@login_required
def exportar_traslados_form(request):
    """Muestra formulario con filtros (desde, hasta, vehículo, conductor) para exportar Excel."""
    vehiculos = Vehiculo.objects.all().order_by('patente')
    conductores = Usuario.objects.filter(rol='Conductor', activo=True).order_by('nombre', 'apellido')
    return render(request, 'flota/exportar_traslados.html', {
        'vehiculos': vehiculos,
        'conductores': conductores,
    })


# --- NUEVA VISTA EXPORTAR VIAJES (REQ: Exportar datos consolidados) ---
@login_required
def exportar_consolidado_viajes(request):
    # Filtros opcionales: desde, hasta, vehiculo, conductor
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    vehiculo_filtro = request.GET.get('vehiculo')
    conductor_filtro = request.GET.get('conductor')

    viajes = Viaje.objects.select_related('hoja_ruta', 'hoja_ruta__vehiculo', 'hoja_ruta__conductor').all()
    if desde:
        try:
            from datetime import datetime as dt
            fecha_desde = dt.strptime(desde, '%Y-%m-%d').date()
            viajes = viajes.filter(hoja_ruta__fecha__gte=fecha_desde)
        except ValueError:
            pass
    if hasta:
        try:
            from datetime import datetime as dt
            fecha_hasta = dt.strptime(hasta, '%Y-%m-%d').date()
            viajes = viajes.filter(hoja_ruta__fecha__lte=fecha_hasta)
        except ValueError:
            pass
    if vehiculo_filtro:
        viajes = viajes.filter(hoja_ruta__vehiculo__patente=vehiculo_filtro)
    if conductor_filtro:
        viajes = viajes.filter(hoja_ruta__conductor__rut=conductor_filtro)
    viajes = viajes.order_by('-hoja_ruta__fecha')

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="consolidado_traslados_{timezone.now().date()}.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Traslados')

    # Encabezados
    headers = ['Fecha', 'Vehículo', 'Conductor', 'Turno', 'Hora Salida', 'Hora Llegada',
               'Destino', 'Paciente', 'RUT Paciente', 'Tipo Servicio', 'Kms Viaje']

    for col_num, header in enumerate(headers):
        ws.write(0, col_num, header, xlwt.easyxf('font: bold on'))

    # Datos

    for row_num, viaje in enumerate(viajes, 1):
        ws.write(row_num, 0, viaje.hoja_ruta.fecha.strftime('%d-%m-%Y'))
        ws.write(row_num, 1, viaje.hoja_ruta.vehiculo.patente)
        ws.write(row_num, 2, viaje.hoja_ruta.conductor.nombre_completo)
        ws.write(row_num, 3, viaje.hoja_ruta.turno)
        ws.write(row_num, 4, viaje.hora_salida.strftime('%H:%M'))
        ws.write(row_num, 5, viaje.hora_llegada.strftime('%H:%M') if viaje.hora_llegada else '-')
        ws.write(row_num, 6, viaje.destino)
        ws.write(row_num, 7, viaje.nombre_paciente)
        ws.write(row_num, 8, viaje.rut_paciente)
        ws.write(row_num, 9, viaje.tipo_servicio)
        ws.write(row_num, 10, viaje.km_recorridos_calculados)

    wb.save(response)
    return response
    