from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
import xlwt
from ..models import HojaRuta, CargaCombustible, FallaReportada, AlertaMantencion, Viaje, Vehiculo
from ..forms import HojaRutaForm, CargaCombustibleForm, FallaReportadaForm, ViajeForm
from .utilidades import es_conductor_o_admin, es_administrador

# RF_15: Registrar bitácora (Hoja de Ruta)
@login_required
@user_passes_test(es_conductor_o_admin)
def registrar_bitacora(request):
    if request.method == 'POST':
        form = HojaRutaForm(request.POST)
        if form.is_valid():
            hoja_ruta = form.save(commit=False)
            hoja_ruta.conductor = request.user  # ¡IMPORTANTE!
            hoja_ruta.save()
            
            # DEBUG: Mostrar mensaje de éxito
            messages.success(request, f'Hoja de ruta creada exitosamente (ID: {hoja_ruta.id})')
            
            return redirect('agregar_viaje', id=hoja_ruta.id)
        else:
            # DEBUG: Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error en {field}: {error}')
    else:
        form = HojaRutaForm()
    
    template = 'flota/registrar_bitacora_conductor.html' if request.user.rol == 'Conductor' else 'flota/registrar_bitacora.html'
    return render(request, template, {'form': form})


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
            # Nota: Si se corrige el KM fin, se debería evaluar si actualizar el KM del vehículo
            # pero es complejo si hay hojas posteriores. Por seguridad, solo editamos el registro.
            messages.success(request, f'Hoja de ruta {hoja.id} corregida exitosamente.')
            return redirect('detalle_bitacora', id=hoja.id)
    else:
        form = HojaRutaForm(instance=hoja)

    return render(request, 'flota/modificar_bitacora.html', {'form': form, 'hoja': hoja})


# --- NUEVA VISTA DETALLE BITÁCORA ---
@login_required
def detalle_bitacora(request, id):
    hoja = get_object_or_404(HojaRuta, id=id)
    viajes = hoja.viajes.all()
    
    # Calcular totales usando la propiedad calculada
    total_km_viajes = sum(v.km_recorridos_calculados for v in viajes)

    return render(request, 'flota/detalle_bitacora.html', {
        'hoja': hoja,
        'viajes': viajes,
        'total_km_viajes': total_km_viajes
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
                
                # Crear alerta si es necesario
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


# --- NUEVA VISTA EXPORTAR VIAJES (REQ: Exportar datos consolidados) ---
@login_required
def exportar_consolidado_viajes(request):
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
    viajes = Viaje.objects.select_related('hoja_ruta', 'hoja_ruta__vehiculo', 'hoja_ruta__conductor').all().order_by('-hoja_ruta__fecha')

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
        ws.write(row_num, 10, viaje.km_recorridos_viaje)

    wb.save(response)
    return response


@login_required
@user_passes_test(es_conductor_o_admin)
def agregar_viaje(request, id):
    hoja_ruta = get_object_or_404(HojaRuta, id=id)
    
    if request.method == 'POST':
        form = ViajeForm(request.POST, hoja_ruta=hoja_ruta)
        if form.is_valid():
            viaje = form.save(commit=False)
            viaje.hoja_ruta = hoja_ruta
            viaje.save()
            
            # ✅ Actualizar vehículo con el KM más alto registrado
            vehiculo = hoja_ruta.vehiculo
            if viaje.km_fin_viaje > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = viaje.km_fin_viaje
                vehiculo.save()
                
                # Verificar alertas de mantenimiento
                if vehiculo.kilometraje_para_mantencion <= 500:
                    messages.warning(request, 
                        f'⚠️ Al vehículo {vehiculo.patente} le quedan {vehiculo.kilometraje_para_mantencion} km para mantenimiento')
            
            messages.success(request, 
                f'Viaje registrado: {viaje.km_recorridos_calculados} km recorridos')
            
            # ✅ Redirigir para agregar otro viaje (con KM inicial prellenado)
            return redirect('agregar_viaje', id=hoja_ruta.id)
    else:
        form = ViajeForm(hoja_ruta=hoja_ruta)
    
    # Calcular resumen
    total_km_viajes = sum(v.km_recorridos_calculados for v in hoja_ruta.viajes.all())
    
    return render(request, 'flota/agregar_viaje.html', {
        'form': form,
        'hoja_ruta': hoja_ruta,
        'viajes_existentes': hoja_ruta.viajes.all(),
        'total_km_viajes': total_km_viajes
    })
    