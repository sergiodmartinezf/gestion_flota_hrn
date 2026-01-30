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
        form_hoja = HojaRutaForm(request.POST)
        form_viaje = ViajeForm(request.POST)
        
        print("=== DATOS RECIBIDOS ===")
        print("POST data:", dict(request.POST))
        print("=========================")
        
        if form_hoja.is_valid() and form_viaje.is_valid():
            try:
                # 1. Guardar Hoja de Ruta
                hoja_ruta = form_hoja.save(commit=False)
                hoja_ruta.conductor = request.user
                
                # Determinar si es camioneta
                es_camioneta = form_hoja.cleaned_data.get('es_camioneta', False)
                
                # Guardar hoja de ruta primero
                hoja_ruta.save()
                
                # 2. Crear Viaje según el tipo de vehículo
                if es_camioneta:
                    # Para camionetas: crear viaje con campos específicos
                    viaje = Viaje(
                        hora_salida=form_hoja.cleaned_data.get('hora_salida_viaje'),
                        hora_llegada=form_hoja.cleaned_data.get('hora_llegada_viaje'),
                        destino=form_hoja.cleaned_data.get('destino_camioneta'),
                        nombre_paciente=form_hoja.cleaned_data.get('persona_movilizada'),
                        tipo_servicio='Otros',  # Valor por defecto para camionetas
                        km_inicio_viaje=form_viaje.cleaned_data.get('km_inicio_viaje'),
                        km_fin_viaje=form_viaje.cleaned_data.get('km_fin_viaje'),
                        hoja_ruta=hoja_ruta
                    )
                else:
                    # Para ambulancias: usar el formulario ViajeForm normal
                    viaje = form_viaje.save(commit=False)
                    viaje.hoja_ruta = hoja_ruta
                
                # Guardar viaje
                viaje.save()
                
                # 3. Actualizar kilometraje del vehículo
                vehiculo = hoja_ruta.vehiculo
                if viaje.km_fin_viaje > vehiculo.kilometraje_actual:
                    vehiculo.kilometraje_actual = viaje.km_fin_viaje
                    vehiculo.save()
                
                # 4. Actualizar KM de la hoja de ruta
                hoja_ruta.km_inicio = viaje.km_inicio_viaje
                hoja_ruta.km_fin = viaje.km_fin_viaje
                hoja_ruta.save()
                
                messages.success(request, f'Salida registrada exitosamente (ID: {hoja_ruta.id})')
                return redirect('detalle_bitacora', id=hoja_ruta.id)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            # Mostrar errores detallados
            for field, errors in form_hoja.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            for field, errors in form_viaje.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form_hoja = HojaRutaForm()
        form_viaje = ViajeForm()
    
    return render(request, 'flota/registrar_bitacora_conductor.html', {
        'form': form_hoja,
        'form_viaje': form_viaje
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
            
            # Actualizar vehículo con el KM más alto registrado
            vehiculo = hoja_ruta.vehiculo
            if viaje.km_fin_viaje > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = viaje.km_fin_viaje
                vehiculo.save()
                
                # Verificar alertas de mantenimiento
                if vehiculo.kilometraje_para_mantencion <= 500:
                    messages.warning(request, 
                        f'⚠️ Al vehículo {vehiculo.patente} le quedan {vehiculo.kilometraje_para_mantencion} km para mantenimiento')
            
            primer_viaje = hoja_ruta.viajes.order_by('hora_salida', 'km_inicio_viaje').first()
            ultimo_viaje = hoja_ruta.viajes.order_by('hora_salida', 'km_inicio_viaje').last()
            
            if primer_viaje:
                hoja_ruta.km_inicio = primer_viaje.km_inicio_viaje
            
            if ultimo_viaje:
                hoja_ruta.km_fin = ultimo_viaje.km_fin_viaje
            
            hoja_ruta.save()

            messages.success(request, f'Viaje registrado: {viaje.km_recorridos_calculados} km recorridos')
            return redirect('agregar_viaje', id=hoja_ruta.id)
        else:
            # ESTE ES EL NUEVO BLOQUE DE ERROR QUE CAUSABA EL PROBLEMA DE INDENTACIÓN
            messages.error(request, 'No se pudo registrar el viaje. Verifique los errores arriba del formulario.')
            print("Errores formulario viaje:", form.errors)

    else:
        # Pre-llenado inteligente para el siguiente viaje
        initial_data = {}
        ultimo_viaje = hoja_ruta.viajes.last()
        
        # Si ya hay un viaje, el inicio del nuevo es el fin del anterior
        if ultimo_viaje:
            initial_data['km_inicio_viaje'] = ultimo_viaje.km_fin_viaje
        else:
            # Si es el PRIMER viaje, sugerimos el kilometraje actual del vehículo
            initial_data['km_inicio_viaje'] = hoja_ruta.vehiculo.kilometraje_actual
            
        form = ViajeForm(hoja_ruta=hoja_ruta)
    
    # Calcular resumen
    total_km_viajes = sum(v.km_recorridos_calculados for v in hoja_ruta.viajes.all())
    
    return render(request, 'flota/agregar_viaje.html', {
        'form': form,
        'hoja_ruta': hoja_ruta,
        'viajes_existentes': hoja_ruta.viajes.all(),
        'total_km_viajes': total_km_viajes
    })
    