from django import forms
from django.forms import formset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font
from ..models import HojaRuta, CargaCombustible, FallaReportada, AlertaMantencion, Viaje, Vehiculo, Usuario, PacienteTraslado, PacienteViaje
from ..forms import HojaRutaForm, CargaCombustibleForm, FallaReportadaForm, ViajeForm, PacienteFormSet
from .utilidades import es_conductor_o_admin, es_administrador
from datetime import datetime, timedelta


TIPOS_SERVICIO = [
    ('Llamado', 'Llamado'),
    ('Rescate de Paciente', 'Rescate de Paciente'),
    ('A Urgencia HBO', 'A Urgencia HBO'),
    ('Exámenes', 'Exámenes'),
    ('Alta a Domicilio', 'Alta a Domicilio'),
    ('Interconsulta', 'Interconsulta'),
    ('Horas a especialista', 'Horas a especialista'),
    ('Imagen', 'Imagen'),
    ('Otro', 'Otro'),
]


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

            # Validar contra el último viaje si existe (Viaje usa km_llegada, no km_fin_viaje)
            ultimo_viaje = hoja.viajes.order_by('-km_llegada').first()
            if ultimo_viaje and ultimo_viaje.km_llegada and km_final < ultimo_viaje.km_llegada:
                messages.warning(request, f"Atención: El KM de cierre es menor al del último viaje registrado ({ultimo_viaje.km_llegada}).")
            
            # Guardar cierre y marcar hoja como cerrada
            hoja.km_fin = km_final
            hoja.abierta = False
            hoja.save(update_fields=['km_fin', 'abierta'])
            
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
    if request.method == 'POST':
        form = HojaRutaForm(request.POST)
        if form.is_valid():
            hoja_ruta = form.save(commit=False)
            hoja_ruta.conductor = request.user
            hoja_ruta.save()
            messages.success(request, 'Hoja de ruta creada exitosamente.')
            return redirect('agregar_viaje', id=hoja_ruta.id)
        else:
            # Mostrar errores de forma clara
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = HojaRutaForm()

    vehiculos = Vehiculo.objetos_operativos().order_by('patente')
    vehiculos_info = [
        {
            'patente': v.patente,
            'texto': f"{v.patente} - {v.marca} {v.modelo} ({v.tipo_carroceria}) - {v.kilometraje_actual} km",
            'kilometraje': v.kilometraje_actual,
            'es_camioneta': v.tipo_carroceria == 'Camioneta'
        }
        for v in vehiculos
    ]
    return render(request, 'flota/registrar_hoja_ruta.html', {
        'form': form,
        'vehiculos': vehiculos,
        'vehiculos_info': vehiculos_info
    })


@login_required
@user_passes_test(es_conductor_o_admin)
def agregar_viaje(request, id):
    hoja = get_object_or_404(HojaRuta, id=id)
    
    # Calcular KM sugerido
    ultimo_viaje = hoja.viajes.order_by('-km_llegada').first()
    km_sugerido = ultimo_viaje.km_llegada if ultimo_viaje and ultimo_viaje.km_llegada else hoja.km_inicio

    if request.method == 'POST':
        form = ViajeForm(request.POST)
        # Usar request.POST y request.FILES para el formset
        paciente_formset = PacienteFormSet(request.POST, request.FILES)
        
        if form.is_valid():
            viaje = form.save(commit=False)
            viaje.hoja_ruta = hoja
            
            # Validación de KM
            if viaje.km_salida < km_sugerido:
                messages.error(request, f'Error: KM salida ({viaje.km_salida}) es menor al anterior ({km_sugerido}).')
            else:
                if paciente_formset.is_valid():
                    viaje.save()  # Guardar viaje primero
                    
                    # Guardar pacientes y actualizar tabla maestra PacienteViaje
                    pacientes = paciente_formset.save(commit=False)
                    for paciente in pacientes:
                        paciente.viaje = viaje
                        if paciente.rut and paciente.nombre:
                            pv, _ = PacienteViaje.objects.get_or_create(
                                rut=paciente.rut.strip(),
                                defaults={'nombre': paciente.nombre, 'prevision': paciente.prevision or ''}
                            )
                            paciente.paciente_viaje = pv
                        paciente.save()
                    
                    # Guardar también los que se marcaron para eliminar
                    for form in paciente_formset.deleted_forms:
                        if form.instance.pk:
                            form.instance.delete()
                    
                    messages.success(request, 'Viaje registrado correctamente.')
                    return redirect('agregar_viaje', id=hoja.id)
                else:
                    messages.error(request, 'Error en los datos de los pacientes.')
    else:
        form = ViajeForm(initial={
            'km_salida': km_sugerido,
            'hora_salida': timezone.now().strftime('%H:%M')
        })
        # Formset vacío inicialmente
        paciente_formset = PacienteFormSet(queryset=PacienteTraslado.objects.none())

    # En viajes.py, dentro de agregar_viaje (GET)
    if request.method == 'GET':
        km_sugerido = ultimo_viaje.km_llegada if ultimo_viaje and ultimo_viaje.km_llegada else hoja.km_inicio
        initial_data = {
            'km_salida': km_sugerido,
            'km_llegada': km_sugerido + 1 if km_sugerido is not None else None,
            'hora_salida': timezone.now().strftime('%H:%M')
        }
        form = ViajeForm(initial=initial_data)

    # Lista de pacientes de traslados anteriores para el desplegable
    pacientes_anteriores = PacienteViaje.objects.all().order_by('nombre')[:300]

    km_actual_vehiculo = hoja.vehiculo.kilometraje_actual
    if km_actual_vehiculo < hoja.km_inicio:
        km_actual_vehiculo = hoja.km_inicio
    
    context = {
        'hoja': hoja,
        'form': form,
        'paciente_formset': paciente_formset,
        'ultimos_viajes': hoja.viajes.all().order_by('-id')[:5],
        'pacientes_anteriores': pacientes_anteriores,
        'km_actual_vehiculo': km_actual_vehiculo,
    }
    return render(request, 'flota/registrar_viaje.html', context)


@login_required
def listar_bitacoras(request):
    # Filtro base según rol de usuario
    if request.user.rol == 'Conductor':
        bitacoras = HojaRuta.objects.filter(conductor=request.user).order_by('-fecha', '-creado_en')
    else:
        bitacoras = HojaRuta.objects.all()

    # Filtros
    desde_filtro = request.GET.get('desde')
    hasta_filtro = request.GET.get('hasta')
    conductor_filtro = request.GET.get('conductor')
    estado_filtro = request.GET.get('estado')
    vehiculo_filtro = request.GET.get('vehiculo')

    if desde_filtro:
        bitacoras = bitacoras.filter(fecha__gte=desde_filtro)

    if hasta_filtro:
        bitacoras = bitacoras.filter(fecha__lte=hasta_filtro)

    if conductor_filtro:
        bitacoras = bitacoras.filter(conductor__rut=conductor_filtro)

    if estado_filtro:
        if estado_filtro == 'abierta':
            bitacoras = bitacoras.filter(abierta=True)
        elif estado_filtro == 'cerrada':
            bitacoras = bitacoras.filter(abierta=False)

    if vehiculo_filtro:
        bitacoras = bitacoras.filter(vehiculo__patente=vehiculo_filtro)

    bitacoras = bitacoras.order_by('-fecha', '-creado_en')

    # Obtener datos para filtros
    vehiculos = Vehiculo.objects.all().order_by('patente')
    conductores = Usuario.objects.filter(rol='Conductor', activo=True).order_by('nombre', 'apellido')

    return render(request, 'flota/listar_bitacoras.html', {
        'bitacoras': bitacoras,
        'vehiculos': vehiculos,
        'conductores': conductores,
        'vehiculo_filtro': vehiculo_filtro,
        'desde_filtro': desde_filtro,
        'hasta_filtro': hasta_filtro,
        'conductor_filtro': conductor_filtro,
        'estado_filtro': estado_filtro,
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
    viajes = hoja.viajes.prefetch_related('pacientes').all()
    
    # Calcular totales con atributos reales del modelo (km_salida, km_llegada)
    total_km_viajes = sum(v.km_recorridos_calculados for v in viajes)
    
    # KM final de la hoja: el mayor km_llegada de los viajes o el ya guardado en la hoja
    if viajes.exists():
        km_llegadas = [v.km_llegada for v in viajes if v.km_llegada is not None]
        km_fin_hoja = max(km_llegadas) if km_llegadas else hoja.km_fin or hoja.km_inicio
    else:
        km_fin_hoja = hoja.km_fin or hoja.km_inicio

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

    # Filtros
    desde_filtro = request.GET.get('desde')
    hasta_filtro = request.GET.get('hasta')
    conductor_filtro = request.GET.get('conductor')
    vehiculo_filtro = request.GET.get('vehiculo')

    if desde_filtro:
        cargas = cargas.filter(fecha__gte=desde_filtro)

    if hasta_filtro:
        cargas = cargas.filter(fecha__lte=hasta_filtro)

    if conductor_filtro:
        cargas = cargas.filter(conductor__rut=conductor_filtro)

    if vehiculo_filtro:
        cargas = cargas.filter(patente_vehiculo__patente=vehiculo_filtro)

    cargas = cargas.order_by('-fecha')

    # Obtener datos para filtros
    vehiculos = Vehiculo.objects.all().order_by('patente')
    conductores = Usuario.objects.filter(rol='Conductor', activo=True).order_by('nombre', 'apellido')

    return render(request, 'flota/listar_cargas_combustible.html', {
        'cargas': cargas,
        'vehiculos': vehiculos,
        'conductores': conductores,
        'vehiculo_filtro': vehiculo_filtro,
        'desde_filtro': desde_filtro,
        'hasta_filtro': hasta_filtro,
        'conductor_filtro': conductor_filtro,
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

                # Crear alerta por falla cuando se supera el umbral de mantención
                vehiculo = falla.vehiculo
                if vehiculo.umbral_mantencion > 0 and vehiculo.kilometraje_actual >= vehiculo.umbral_mantencion:
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

    # Filtros
    desde_filtro = request.GET.get('desde')
    hasta_filtro = request.GET.get('hasta')
    conductor_filtro = request.GET.get('conductor')
    vehiculo_filtro = request.GET.get('vehiculo')

    if desde_filtro:
        incidentes = incidentes.filter(fecha_reporte__gte=desde_filtro)

    if hasta_filtro:
        incidentes = incidentes.filter(fecha_reporte__lte=hasta_filtro)

    if conductor_filtro:
        incidentes = incidentes.filter(conductor__rut=conductor_filtro)

    if vehiculo_filtro:
        incidentes = incidentes.filter(vehiculo__patente=vehiculo_filtro)

    incidentes = incidentes.order_by('-fecha_reporte')

    # Obtener datos para filtros
    vehiculos = Vehiculo.objects.all().order_by('patente')
    conductores = Usuario.objects.filter(rol='Conductor', activo=True).order_by('nombre', 'apellido')

    return render(request, 'flota/listar_incidentes.html', {
        'incidentes': incidentes,
        'vehiculos': vehiculos,
        'conductores': conductores,
        'vehiculo_filtro': vehiculo_filtro,
        'desde_filtro': desde_filtro,
        'hasta_filtro': hasta_filtro,
        'conductor_filtro': conductor_filtro,
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


# --- EXPORTAR VIAJES CONSOLIDADO (openpyxl, una fila por paciente) ---
@login_required
def exportar_consolidado_viajes(request):
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    vehiculo_filtro = request.GET.get('vehiculo')
    conductor_filtro = request.GET.get('conductor')

    viajes = Viaje.objects.select_related(
        'hoja_ruta', 'hoja_ruta__vehiculo', 'hoja_ruta__conductor'
    ).prefetch_related('pacientes').all()

    if desde:
        try:
            fecha_desde = datetime.strptime(desde, '%Y-%m-%d').date()
            viajes = viajes.filter(hoja_ruta__fecha__gte=fecha_desde)
        except ValueError:
            pass
    if hasta:
        try:
            fecha_hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
            viajes = viajes.filter(hoja_ruta__fecha__lte=fecha_hasta)
        except ValueError:
            pass
    if vehiculo_filtro:
        viajes = viajes.filter(hoja_ruta__vehiculo__patente=vehiculo_filtro)
    if conductor_filtro:
        viajes = viajes.filter(hoja_ruta__conductor__rut=conductor_filtro)
    viajes = viajes.order_by('-hoja_ruta__fecha')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Traslados'

    headers = [
        'Fecha', 'Vehículo', 'Conductor', 'Turno', 'Hora Salida', 'Hora Llegada',
        'Destino', 'Paciente', 'RUT Paciente', 'Tipo Servicio', 'Kms Viaje'
    ]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True)

    row_num = 2
    for viaje in viajes:
        hoja = viaje.hoja_ruta
        fecha_str = hoja.fecha.strftime('%d-%m-%Y')
        vehiculo_patente = hoja.vehiculo.patente
        conductor_nombre = hoja.conductor.nombre_completo
        turno = hoja.turno
        hora_salida = viaje.hora_salida.strftime('%H:%M')
        hora_llegada = viaje.hora_llegada.strftime('%H:%M') if viaje.hora_llegada else '-'
        km_viaje = viaje.km_recorridos_calculados

        pacientes = list(viaje.pacientes.all())
        if not pacientes:
            ws.cell(row=row_num, column=1, value=fecha_str)
            ws.cell(row=row_num, column=2, value=vehiculo_patente)
            ws.cell(row=row_num, column=3, value=conductor_nombre)
            ws.cell(row=row_num, column=4, value=turno)
            ws.cell(row=row_num, column=5, value=hora_salida)
            ws.cell(row=row_num, column=6, value=hora_llegada)
            ws.cell(row=row_num, column=7, value='-')
            ws.cell(row=row_num, column=8, value='Sin pacientes')
            ws.cell(row=row_num, column=9, value='')
            ws.cell(row=row_num, column=10, value='')
            ws.cell(row=row_num, column=11, value=km_viaje)
            row_num += 1
        else:
            for p in pacientes:
                destino_display = p.get_destino_tipo_display()
                if p.direccion_especifica and p.destino_tipo == 'DOMICILIO':
                    destino_display += f" - {p.direccion_especifica}"
                ws.cell(row=row_num, column=1, value=fecha_str)
                ws.cell(row=row_num, column=2, value=vehiculo_patente)
                ws.cell(row=row_num, column=3, value=conductor_nombre)
                ws.cell(row=row_num, column=4, value=turno)
                ws.cell(row=row_num, column=5, value=hora_salida)
                ws.cell(row=row_num, column=6, value=hora_llegada)
                ws.cell(row=row_num, column=7, value=destino_display)
                ws.cell(row=row_num, column=8, value=p.nombre)
                ws.cell(row=row_num, column=9, value=p.rut or '')
                ws.cell(row=row_num, column=10, value=p.prevision or '')
                ws.cell(row=row_num, column=11, value=km_viaje)
                row_num += 1

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="consolidado_traslados_{timezone.now().date()}.xlsx"'
    )
    wb.save(response)
    return response
    