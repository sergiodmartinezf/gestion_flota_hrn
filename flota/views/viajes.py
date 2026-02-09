from django import forms
from django.forms import formset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
import xlwt
from ..models import HojaRuta, CargaCombustible, FallaReportada, AlertaMantencion, Viaje, Vehiculo, Usuario, PacienteTraslado
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
    if request.method == 'POST':
        form = HojaRutaForm(request.POST)
        
        if form.is_valid():
            try:
                hoja_ruta = form.save(commit=False)
                hoja_ruta.conductor = request.user
                
                # Si es camioneta, asegurarnos de que los campos estén vacíos
                if hoja_ruta.vehiculo.tipo_carroceria == 'Camioneta':
                    hoja_ruta.no_aplica_enfermero = True
                    hoja_ruta.no_aplica_camillero = True
                    hoja_ruta.enfermero = ''
                    hoja_ruta.camillero = ''
                
                hoja_ruta.save()
                
                es_camioneta = hoja_ruta.vehiculo.tipo_carroceria == 'Camioneta'
                
                request.session['hoja_nueva_id'] = hoja_ruta.id
                request.session['es_camioneta'] = es_camioneta
                
                messages.success(request, f'Hoja de ruta creada exitosamente. Ahora registre el primer viaje.')
                return redirect('agregar_viaje', id=hoja_ruta.id)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = HojaRutaForm()
    
    # Preparar datos para el template
    vehiculos = Vehiculo.objects.filter(
        estado__in=['Disponible', 'En uso']
    ).order_by('patente')
    
    # Crear lista de vehículos con patente, modelo y kilometraje
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
                    
                    # Guardar pacientes
                    pacientes = paciente_formset.save(commit=False)
                    for paciente in pacientes:
                        paciente.viaje = viaje
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

    context = {
        'hoja': hoja,
        'form': form,
        'paciente_formset': paciente_formset,
        'ultimos_viajes': hoja.viajes.all().order_by('-id')[:5]
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
    