from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Sum, Avg, Count, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.views.decorators.http import require_POST
from .utils import consultar_oc_mercado_publico, exportar_reporte_excel, exportar_planilla_mantenimientos_excel

from .models import (
    Usuario, Vehiculo, Proveedor, OrdenCompra, OrdenTrabajo, Presupuesto, Arriendo, 
    HojaRuta, Viaje, CargaCombustible, Mantenimiento, AlertaMantencion, FallaReportada
)
from .forms import (
    LoginForm, UsuarioForm, VehiculoForm, ProveedorForm, HojaRutaForm, 
    ViajeForm, CargaCombustibleForm, MantenimientoForm, ProgramarMantenimientoForm, 
    FinalizarMantenimientoForm, FallaReportadaForm, PresupuestoForm, ArriendoForm, 
    OrdenCompraForm, OrdenTrabajoForm
)


def es_administrador(user):
    return user.is_authenticated and user.rol == 'Administrador'


def es_conductor_o_admin(user):
    return user.is_authenticated and (user.rol == 'Administrador' or user.rol == 'Conductor')


# RF_01: Iniciar sesión
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            rut = form.cleaned_data['rut']
            password = form.cleaned_data['password']
            user = authenticate(request, username=rut, password=password)
            if user is not None and user.activo:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'RUT o contraseña incorrectos, o usuario deshabilitado.')
    else:
        form = LoginForm()
    
    return render(request, 'flota/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')


# RF_02: Registrar usuario
@login_required
@user_passes_test(es_administrador)
def registrar_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            try:
                usuario = form.save()
                messages.success(request, f'Usuario {usuario.nombre_completo} registrado exitosamente. Contraseña establecida.')
                return redirect('listar_usuarios')
            except Exception as e:
                messages.error(request, f'Error al registrar usuario: {str(e)}')
        else:
            # Mostrar errores específicos
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UsuarioForm()
    
    return render(request, 'flota/registrar_usuario.html', {'form': form})


# RF_03: Listar usuarios
@login_required
@user_passes_test(es_administrador)
def listar_usuarios(request):
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'
    
    if mostrar_deshabilitados:
        usuarios = Usuario.objects.all().order_by('apellido', 'nombre')
    else:
        usuarios = Usuario.objects.filter(activo=True).order_by('apellido', 'nombre')
    
    return render(request, 'flota/listar_usuarios.html', {
        'usuarios': usuarios,
        'mostrar_deshabilitados': mostrar_deshabilitados,
    })


# RF_04: Modificar usuario
@login_required
@user_passes_test(es_administrador)
def modificar_usuario(request, rut):
    usuario = get_object_or_404(Usuario, rut=rut)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            try:
                usuario = form.save()
                messages.success(request, f'Usuario {usuario.nombre_completo} modificado exitosamente.')
                return redirect('listar_usuarios')
            except Exception as e:
                messages.error(request, f'Error al modificar usuario: {str(e)}')
        else:
            # Mostrar errores específicos
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UsuarioForm(instance=usuario)
    
    return render(request, 'flota/modificar_usuario.html', {'form': form, 'usuario': usuario})


# RF_05: Deshabilitar usuario
@login_required
@user_passes_test(es_administrador)
def deshabilitar_usuario(request, rut):
    usuario = get_object_or_404(Usuario, rut=rut)
    
    # Prevenir que un administrador se deshabilite a sí mismo
    if request.user.rut == usuario.rut:
        messages.error(request, 'No puedes deshabilitarte a ti mismo. Otro administrador debe hacerlo.')
        return redirect('listar_usuarios')
    
    if request.method == 'POST':
        usuario.activo = False
        usuario.save()
        messages.success(request, f'Usuario {usuario.nombre_completo} deshabilitado exitosamente.')
        return redirect('listar_usuarios')
    
    return render(request, 'flota/deshabilitar_usuario.html', {'usuario': usuario})


# RF_06: Registrar vehículo
@login_required
@user_passes_test(es_administrador)
def registrar_vehiculo(request):
    if request.method == 'POST':
        form = VehiculoForm(request.POST)
        if form.is_valid():
            vehiculo = form.save()
            messages.success(request, f'Vehículo {vehiculo.patente} registrado exitosamente.')
            return redirect('listar_flota')
    else:
        form = VehiculoForm()
    
    return render(request, 'flota/registrar_vehiculo.html', {'form': form})


# RF_07: Listar flota
@login_required
def listar_flota(request):
    vehiculos = Vehiculo.objects.all().order_by('patente')
    
    # Filtros
    estado_filter = request.GET.get('estado')
    tipo_filter = request.GET.get('tipo_carroceria')
    
    if estado_filter:
        vehiculos = vehiculos.filter(estado=estado_filter)
    if tipo_filter:
        vehiculos = vehiculos.filter(tipo_carroceria=tipo_filter)
    
    return render(request, 'flota/listar_flota.html', {
        'vehiculos': vehiculos,
        'estado_filter': estado_filter,
        'tipo_filter': tipo_filter,
    })


# RF_08: Visualizar ficha de unidad
@login_required
def ficha_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo).order_by('-fecha_ingreso')[:10]
    alertas = AlertaMantencion.objects.filter(vehiculo=vehiculo, vigente=True)
    presupuestos = Presupuesto.objects.filter(vehiculo=vehiculo).order_by('-anio')
    
    # Calcular costo por kilómetro
    total_mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo).aggregate(
        total=Sum('costo_total_real')
    )['total'] or Decimal('0')
    
    total_combustible = CargaCombustible.objects.filter(patente_vehiculo=vehiculo).aggregate(
        total=Sum('costo_total')
    )['total'] or Decimal('0')
    
    costo_total = total_mantenimientos + total_combustible
    costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
    
    return render(request, 'flota/ficha_vehiculo.html', {
        'vehiculo': vehiculo,
        'mantenimientos': mantenimientos,
        'alertas': alertas,
        'presupuestos': presupuestos,
        'costo_total': costo_total,
        'costo_por_km': costo_por_km,
    })


# RF_09: Modificar datos de unidad
@login_required
@user_passes_test(es_administrador)
def modificar_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    if request.method == 'POST':
        form = VehiculoForm(request.POST, instance=vehiculo)
        if form.is_valid():
            vehiculo = form.save()
            messages.success(request, f'Vehículo {vehiculo.patente} modificado exitosamente.')
            return redirect('ficha_vehiculo', patente=vehiculo.patente)
    else:
        form = VehiculoForm(instance=vehiculo)
    
    return render(request, 'flota/modificar_vehiculo.html', {'form': form, 'vehiculo': vehiculo})


# RF_10: Actualizar estado de unidad
@login_required
@user_passes_test(es_administrador)
def actualizar_estado_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Vehiculo.ESTADOS):
            vehiculo.estado = nuevo_estado
            vehiculo.save()
            messages.success(request, f'Estado del vehículo {vehiculo.patente} actualizado a {nuevo_estado}.')
            return redirect('ficha_vehiculo', patente=vehiculo.patente)
    
    return render(request, 'flota/actualizar_estado_vehiculo.html', {'vehiculo': vehiculo})


# RF_11: Visualizar disponibilidad de flota
@login_required
def disponibilidad_flota(request):
    vehiculos = Vehiculo.objects.all()
    estados_count = {}
    for estado, nombre in Vehiculo.ESTADOS:
        estados_count[estado] = vehiculos.filter(estado=estado).count()
    
    return render(request, 'flota/disponibilidad_flota.html', {
        'vehiculos': vehiculos,
        'estados_count': estados_count,
    })


# RF_12: Visualizar costo por kilometro
@login_required
def costo_por_kilometro(request):
    vehiculos = Vehiculo.objects.all()
    costos = []
    
    for vehiculo in vehiculos:
        total_mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo).aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        
        total_combustible = CargaCombustible.objects.filter(patente_vehiculo=vehiculo).aggregate(
            total=Sum('costo_total')
        )['total'] or Decimal('0')
        
        costo_total = total_mantenimientos + total_combustible
        costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
        
        costos.append({
            'vehiculo': vehiculo,
            'costo_total': costo_total,
            'costo_por_km': costo_por_km,
        })
    
    costo_promedio = sum(c['costo_por_km'] for c in costos) / len(costos) if costos else Decimal('0')
    
    return render(request, 'flota/costo_por_kilometro.html', {
        'costos': costos,
        'costo_promedio': costo_promedio,
    })


# RF_13: Visualizar gastos de mantenimientos
@login_required
def gastos_mantenimientos(request):
    vehiculos = Vehiculo.objects.all()
    gastos = []
    
    for vehiculo in vehiculos:
        presupuestos = Presupuesto.objects.filter(vehiculo=vehiculo)
        gasto_acumulado = Mantenimiento.objects.filter(vehiculo=vehiculo).aggregate(
            total=Sum('costo_total_real')
        )['total'] or Decimal('0')
        
        presupuesto_total = presupuestos.aggregate(
            total=Sum('monto_asignado')
        )['total'] or Decimal('0')
        
        gastos.append({
            'vehiculo': vehiculo,
            'gasto_acumulado': gasto_acumulado,
            'presupuesto_total': presupuesto_total,
            'diferencia': gasto_acumulado - presupuesto_total,
        })
    
    return render(request, 'flota/gastos_mantenimientos.html', {'gastos': gastos})


# RF_14: Visualizar alertas de mantenimiento
@login_required
def alertas_mantenimiento(request):
    alertas = AlertaMantencion.objects.filter(vigente=True).order_by('-generado_en')
    return render(request, 'flota/alertas_mantenimiento.html', {'alertas': alertas})


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
            
            # Actualizar kilometraje del vehículo
            vehiculo = hoja_ruta.vehiculo
            if vehiculo.kilometraje_actual < hoja_ruta.km_fin:
                vehiculo.kilometraje_actual = hoja_ruta.km_fin
                vehiculo.save()
            elif hoja_ruta.km_fin < vehiculo.kilometraje_actual:
                # Validar que el kilometraje no retroceda
                messages.warning(request, f'El kilometraje final ({hoja_ruta.km_fin} km) es menor al actual ({vehiculo.kilometraje_actual} km). Verifique los datos.')
                return render(request, 'flota/registrar_bitacora.html', {'form': form})
            
            messages.success(request, 'Bitácora registrada exitosamente.')
            return redirect('listar_bitacoras')
    else:
        form = HojaRutaForm()
        form.fields['vehiculo'].queryset = Vehiculo.objects.filter(
            estado__in=['Disponible', 'En uso']
        ).order_by('patente')
    
    return render(request, 'flota/registrar_bitacora.html', {'form': form})

# API para obtener el kilometraje de los vehículos
@login_required
def api_vehiculos_kilometraje(request):
    vehiculos = Vehiculo.objects.all()
    data = {}
    for vehiculo in vehiculos:
        data[str(vehiculo.patente)] = vehiculo.kilometraje_actual
    return JsonResponse(data)


@login_required
def listar_bitacoras(request):
    if request.user.rol == 'Conductor':
        bitacoras = HojaRuta.objects.filter(conductor=request.user).order_by('-fecha', '-creado_en')
    else:
        bitacoras = HojaRuta.objects.all().order_by('-fecha', '-creado_en')
    
    return render(request, 'flota/listar_bitacoras.html', {'bitacoras': bitacoras})


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
        # Filtrar proveedores activos
        form.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True).order_by('nombre_fantasia')
    
    return render(request, 'flota/registrar_carga_combustible.html', {'form': form})


@login_required
def listar_cargas_combustible(request):
    if request.user.rol == 'Conductor':
        cargas = CargaCombustible.objects.filter(conductor=request.user).order_by('-fecha')
    else:
        cargas = CargaCombustible.objects.all().order_by('-fecha')
    
    return render(request, 'flota/listar_cargas_combustible.html', {'cargas': cargas})


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
    if request.user.rol == 'Conductor':
        incidentes = FallaReportada.objects.filter(conductor=request.user).order_by('-fecha_reporte')
    else:
        incidentes = FallaReportada.objects.all().order_by('-fecha_reporte')
    
    return render(request, 'flota/listar_incidentes.html', {'incidentes': incidentes})


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
                
                mantenimiento.save()
                
                # Actualizar estado del vehículo
                vehiculo = mantenimiento.vehiculo
                vehiculo.estado = 'En mantenimiento'
                vehiculo.save()
                
                # El signal actualizará el presupuesto automáticamente si es necesario
                # (aunque el signal solo actualiza para preventivos, los correctivos no deberían descontar del presupuesto preventivo)
                
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


# RF_21: Registrar presupuesto anual por convenio
@login_required
@user_passes_test(es_administrador)
def registrar_presupuesto(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST)
        if form.is_valid():
            try:
                presupuesto = form.save()
                messages.success(request, 'Presupuesto registrado exitosamente.')
                return redirect('listar_presupuestos')
            except Exception as e:
                messages.error(request, f'Error al registrar presupuesto: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PresupuestoForm()
    
    return render(request, 'flota/registrar_presupuesto.html', {'form': form})


@login_required
@user_passes_test(es_administrador)
def modificar_presupuesto(request, id):
    presupuesto = get_object_or_404(Presupuesto, id=id)
    if request.method == 'POST':
        form = PresupuestoForm(request.POST, instance=presupuesto)
        if form.is_valid():
            try:
                presupuesto = form.save()
                messages.success(request, 'Presupuesto modificado exitosamente.')
                return redirect('listar_presupuestos')
            except Exception as e:
                messages.error(request, f'Error al modificar presupuesto: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PresupuestoForm(instance=presupuesto)
    
    return render(request, 'flota/modificar_presupuesto.html', {'form': form, 'presupuesto': presupuesto})


@login_required
@user_passes_test(es_administrador)
def deshabilitar_presupuesto(request, id):
    presupuesto = get_object_or_404(Presupuesto, id=id)
    if request.method == 'POST':
        presupuesto.activo = False
        presupuesto.save()
        messages.success(request, 'Presupuesto deshabilitado exitosamente.')
        return redirect('listar_presupuestos')
    
    return render(request, 'flota/deshabilitar_presupuesto.html', {'presupuesto': presupuesto})


@login_required
def listar_presupuestos(request):
    presupuestos = Presupuesto.objects.filter(activo=True).order_by('-anio', 'vehiculo')
    
    # Filtros
    anio_filter = request.GET.get('anio')
    vehiculo_filter = request.GET.get('vehiculo')
    
    if anio_filter:
        presupuestos = presupuestos.filter(anio=anio_filter)
    if vehiculo_filter:
        presupuestos = presupuestos.filter(vehiculo__patente=vehiculo_filter)
    
    # Calcular totales
    total_asignado = presupuestos.aggregate(
        total=Sum('monto_asignado')
    )['total'] or Decimal('0')
    
    total_ejecutado = presupuestos.aggregate(
        total=Sum('monto_ejecutado')
    )['total'] or Decimal('0')
    
    total_disponible = total_asignado - total_ejecutado
    
    vehiculos = Vehiculo.objects.all().order_by('patente')
    
    return render(request, 'flota/listar_presupuestos.html', {
        'presupuestos': presupuestos,
        'vehiculos': vehiculos,
        'anio_filter': anio_filter,
        'vehiculo_filter': vehiculo_filter,
        'total_asignado': total_asignado,
        'total_ejecutado': total_ejecutado,
        'total_disponible': total_disponible,
    })


# RF_22: Visualizar alertas de presupuesto
@login_required
def alertas_presupuesto(request):
    presupuestos = Presupuesto.objects.filter(activo=True)
    alertas = []
    
    for presupuesto in presupuestos:
        porcentaje = presupuesto.porcentaje_ejecutado
        if porcentaje >= 80:  # Alerta cuando se ha gastado el 80% o más
            alertas.append({
                'presupuesto': presupuesto,
                'porcentaje': porcentaje,
                'monto_restante': presupuesto.monto_asignado - presupuesto.monto_ejecutado,
            })
    
    return render(request, 'flota/alertas_presupuesto.html', {'alertas': alertas})


# Reporte de Variación Presupuestaria (ahora parte de reporte_costos, pero se mantiene para exportación)
@login_required
def reporte_variacion_presupuestaria(request):
    """
    Reporte que compara presupuesto planificado vs ejecutado.
    Alerta cuando la variación es mayor al 10% (requisito crítico).
    """
    anio = request.GET.get('anio', timezone.now().year)
    try:
        anio = int(anio)
    except (ValueError, TypeError):
        anio = timezone.now().year
    
    # Obtener presupuestos del año seleccionado (solo activos)
    # NOTA: Según requisito, este reporte es para "presupuesto anual para lo preventivo"
    # El monto_ejecutado ya está calculado solo con mantenimientos preventivos en signals.py
    presupuestos = Presupuesto.objects.filter(anio=anio, activo=True).select_related('vehiculo', 'cuenta')
    
    reporte = []
    alertas_variacion = []
    
    for presupuesto in presupuestos:
        # Recalcular monto ejecutado solo con mantenimientos preventivos para este reporte
        # (por si acaso el signal no se ejecutó correctamente)
        monto_ejecutado_preventivo = Mantenimiento.objects.filter(
            cuenta_presupuestaria=presupuesto.cuenta,
            vehiculo=presupuesto.vehiculo,
            fecha_ingreso__year=anio,
            tipo_mantencion='Preventivo'
        ).aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
        
        # Calcular variación usando el monto ejecutado de preventivos
        diferencia = monto_ejecutado_preventivo - presupuesto.monto_asignado
        porcentaje_variacion = (diferencia / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
        
        # Determinar si hay alerta (solo cuando se sobrepasa el presupuesto en más del 10%)
        # No alertar si hay mucho presupuesto sin usar, solo cuando se excede
        tiene_alerta = porcentaje_variacion > 10
        
        porcentaje_ejecutado = (monto_ejecutado_preventivo / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
        
        item_reporte = {
            'vehiculo': presupuesto.vehiculo.patente if presupuesto.vehiculo else 'Flota General',
            'marca_modelo': f"{presupuesto.vehiculo.marca} {presupuesto.vehiculo.modelo}" if presupuesto.vehiculo else 'N/A',
            'cuenta_sigfe': presupuesto.cuenta.codigo,
            'nombre_cuenta': presupuesto.cuenta.nombre,
            'monto_asignado': presupuesto.monto_asignado,
            'monto_ejecutado': monto_ejecutado_preventivo,  # Solo preventivos
            'diferencia': diferencia,
            'porcentaje_variacion': porcentaje_variacion,
            'porcentaje_ejecutado': porcentaje_ejecutado,
            'tiene_alerta': tiene_alerta,
            'presupuesto': presupuesto,  # Para el template
        }
        
        reporte.append(item_reporte)
        
        if tiene_alerta:
            alertas_variacion.append(item_reporte)
    
    # Exportar a Excel si se solicita
    if request.GET.get('exportar') == 'excel':
        columnas = [
            ('Vehículo', 'vehiculo', 'texto'),
            ('Marca/Modelo', 'marca_modelo', 'texto'),
            ('Cuenta SIGFE', 'cuenta_sigfe', 'texto'),
            ('Nombre Cuenta', 'nombre_cuenta', 'texto'),
            ('Monto Asignado', 'monto_asignado', 'moneda'),
            ('Monto Ejecutado', 'monto_ejecutado', 'moneda'),
            ('Diferencia', 'diferencia', 'moneda'),
            ('% Variación', 'porcentaje_variacion', 'decimal'),
            ('% Ejecutado', 'porcentaje_ejecutado', 'decimal'),
        ]
        return exportar_reporte_excel(
            f'Análisis de Variación Presupuestaria - Año {anio}',
            reporte,
            columnas,
            f'variacion_presupuestaria_{anio}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    
    # Obtener años disponibles: desde el año actual hacia atrás hasta 5 años
    anio_actual = timezone.now().year
    anios_disponibles = list(range(anio_actual, anio_actual - 6, -1))
    # Agregar años que tienen presupuestos registrados
    anios_con_presupuestos = list(Presupuesto.objects.values_list('anio', flat=True).distinct())
    anios_disponibles = sorted(set(anios_disponibles + anios_con_presupuestos), reverse=True)
    
    return render(request, 'flota/reporte_variacion_presupuestaria.html', {
        'reporte': reporte,
        'alertas_variacion': alertas_variacion,
        'anio': anio,
        'anios_disponibles': anios_disponibles,
    })


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

# flota/views.py

@login_required
@user_passes_test(es_administrador)
def finalizar_mantenimiento(request, id):
    mantenimiento = get_object_or_404(Mantenimiento, id=id)
    
    if request.method == 'POST':
        form = FinalizarMantenimientoForm(request.POST, request.FILES, instance=mantenimiento)
        if form.is_valid():
            mant = form.save(commit=False)
            
            # Calcular costo total real
            mant.costo_total_real = (mant.costo_mano_obra or 0) + (mant.costo_repuestos or 0)
            
            # Cambiar estado a finalizado
            mant.estado = 'Finalizado'

            mant.save()
            
            # Liberar el Vehículo
            vehiculo = mant.vehiculo
            vehiculo.estado = 'Disponible'
            
            # Actualizar kilometraje si el mantenimiento tiene un kilometraje mayor
            if mant.km_al_ingreso > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = mant.km_al_ingreso
            
            vehiculo.save()
            
            # El signal actualizará el presupuesto automáticamente si es preventivo
            # Los mantenimientos correctivos NO deben descontar del presupuesto preventivo
            # (según requisito: "presupuesto anual para lo preventivo")

            messages.success(request, f'Mantenimiento de {vehiculo.patente} finalizado correctamente.')
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


# RF_24: Generar reporte de costos (ahora incluye variación presupuestaria)
@login_required
def reporte_costos(request):
    # Si se solicita exportar variación presupuestaria
    if request.GET.get('exportar') == 'excel' and request.GET.get('tipo') == 'variacion':
        return reporte_variacion_presupuestaria(request)
    
    # Si se solicita exportar costos
    if request.GET.get('exportar') == 'excel' and not request.GET.get('tipo'):
        vehiculos = Vehiculo.objects.all()
        reporte = []
        
        for vehiculo in vehiculos:
            mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
            costo_mantenimientos = mantenimientos.aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
            
            cargas = CargaCombustible.objects.filter(patente_vehiculo=vehiculo)
            costo_combustible = cargas.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
            
            arriendos = Arriendo.objects.filter(vehiculo_reemplazado=vehiculo)
            costo_arriendos = arriendos.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
            
            costo_total = costo_mantenimientos + costo_combustible + costo_arriendos
            costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
            
            presupuesto = Presupuesto.objects.filter(vehiculo=vehiculo).aggregate(
                total=Sum('monto_asignado')
            )['total'] or Decimal('0')
            
            reporte.append({
                'patente': vehiculo.patente,
                'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
                'costo_mantenimientos': costo_mantenimientos,
                'costo_combustible': costo_combustible,
                'costo_arriendos': costo_arriendos,
                'costo_total': costo_total,
                'costo_por_km': costo_por_km,
                'presupuesto': presupuesto,
                'vehiculo': vehiculo,
            })
        
        columnas = [
            ('Vehículo', 'patente', 'texto'),
            ('Marca/Modelo', 'marca_modelo', 'texto'),
            ('Costo Mantenimientos', 'costo_mantenimientos', 'moneda'),
            ('Costo Combustible', 'costo_combustible', 'moneda'),
            ('Costo Arriendos', 'costo_arriendos', 'moneda'),
            ('Costo Total', 'costo_total', 'moneda'),
            ('Costo por Km', 'costo_por_km', 'decimal'),
            ('Presupuesto', 'presupuesto', 'moneda'),
        ]
        return exportar_reporte_excel(
            'Reporte de Costos por Vehículo',
            reporte,
            columnas,
            f'reporte_costos_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    
    # Obtener datos de costos
    vehiculos = Vehiculo.objects.all()
    reporte_costos_data = []
    
    for vehiculo in vehiculos:
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        costo_mantenimientos = mantenimientos.aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
        
        cargas = CargaCombustible.objects.filter(patente_vehiculo=vehiculo)
        costo_combustible = cargas.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        arriendos = Arriendo.objects.filter(vehiculo_reemplazado=vehiculo)
        costo_arriendos = arriendos.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        costo_total = costo_mantenimientos + costo_combustible + costo_arriendos
        costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
        
        presupuesto = Presupuesto.objects.filter(vehiculo=vehiculo).aggregate(
            total=Sum('monto_asignado')
        )['total'] or Decimal('0')
        
        reporte_costos_data.append({
            'patente': vehiculo.patente,
            'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
            'costo_mantenimientos': costo_mantenimientos,
            'costo_combustible': costo_combustible,
            'costo_arriendos': costo_arriendos,
            'costo_total': costo_total,
            'costo_por_km': costo_por_km,
            'presupuesto': presupuesto,
            'vehiculo': vehiculo,
        })
    
    # Obtener datos de variación presupuestaria
    anio = request.GET.get('anio', timezone.now().year)
    try:
        anio = int(anio)
    except (ValueError, TypeError):
        anio = timezone.now().year
    
    presupuestos = Presupuesto.objects.filter(anio=anio, activo=True).select_related('vehiculo', 'cuenta')
    
    reporte_variacion = []
    alertas_variacion = []
    
    for presupuesto in presupuestos:
        monto_ejecutado_preventivo = Mantenimiento.objects.filter(
            cuenta_presupuestaria=presupuesto.cuenta,
            vehiculo=presupuesto.vehiculo,
            fecha_ingreso__year=anio,
            tipo_mantencion='Preventivo'
        ).aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
        
        diferencia = monto_ejecutado_preventivo - presupuesto.monto_asignado
        porcentaje_variacion = (diferencia / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
        
        tiene_alerta = porcentaje_variacion > 10
        
        porcentaje_ejecutado = (monto_ejecutado_preventivo / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado > 0 else 0
        
        item_reporte = {
            'vehiculo': presupuesto.vehiculo.patente if presupuesto.vehiculo else 'Flota General',
            'marca_modelo': f"{presupuesto.vehiculo.marca} {presupuesto.vehiculo.modelo}" if presupuesto.vehiculo else 'N/A',
            'cuenta_sigfe': presupuesto.cuenta.codigo,
            'nombre_cuenta': presupuesto.cuenta.nombre,
            'monto_asignado': presupuesto.monto_asignado,
            'monto_ejecutado': monto_ejecutado_preventivo,
            'diferencia': diferencia,
            'porcentaje_variacion': porcentaje_variacion,
            'porcentaje_ejecutado': porcentaje_ejecutado,
            'tiene_alerta': tiene_alerta,
            'presupuesto': presupuesto,
        }
        
        reporte_variacion.append(item_reporte)
        
        if tiene_alerta:
            alertas_variacion.append(item_reporte)
    
    # Obtener años disponibles
    anio_actual = timezone.now().year
    anios_disponibles = list(range(anio_actual, anio_actual - 6, -1))
    anios_con_presupuestos = list(Presupuesto.objects.values_list('anio', flat=True).distinct())
    anios_disponibles = sorted(set(anios_disponibles + anios_con_presupuestos), reverse=True)
    
    return render(request, 'flota/reporte_costos.html', {
        'reporte': reporte_costos_data,
        'reporte_variacion': reporte_variacion,
        'alertas_variacion': alertas_variacion,
        'anio': anio,
        'anios_disponibles': anios_disponibles,
    })


# RF_25: Generar reporte de disponibilidad (ahora parte de reporte_costos)
@login_required
def reporte_disponibilidad(request):
    vehiculos = Vehiculo.objects.all()
    reporte = []
    
    for vehiculo in vehiculos:
        # Calcular días fuera de servicio sumando duración de mantenimientos
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        total_dias_fuera = 0
        
        for mant in mantenimientos:
            if mant.fecha_salida:
                dias = (mant.fecha_salida - mant.fecha_ingreso).days
                total_dias_fuera += max(0, dias)
        
        incidentes = FallaReportada.objects.filter(vehiculo=vehiculo).count()
        
        reporte.append({
            'patente': vehiculo.patente,
            'marca_modelo': f"{vehiculo.marca} {vehiculo.modelo}",
            'dias_fuera_servicio': total_dias_fuera,
            'incidentes': incidentes,
            'estado': vehiculo.get_estado_display(),
            'vehiculo': vehiculo,  # Para el template
        })
    
    # Exportar a Excel si se solicita
    if request.GET.get('exportar') == 'excel':
        columnas = [
            ('Vehículo', 'patente', 'texto'),
            ('Marca/Modelo', 'marca_modelo', 'texto'),
            ('Días Fuera de Servicio', 'dias_fuera_servicio', 'entero'),
            ('Número de Incidentes', 'incidentes', 'entero'),
            ('Estado Actual', 'estado', 'texto'),
        ]
        return exportar_reporte_excel(
            'Reporte de Disponibilidad de Flota',
            reporte,
            columnas,
            f'reporte_disponibilidad_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    
    return render(request, 'flota/reporte_disponibilidad.html', {'reporte': reporte})


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


# RF_27: Visualizar panel de indicadores (Dashboard)
@login_required
def dashboard(request):
    # Estadísticas generales
    total_vehiculos = Vehiculo.objects.count()
    vehiculos_disponibles = Vehiculo.objects.filter(estado='Disponible').count()
    vehiculos_mantenimiento = Vehiculo.objects.filter(estado='En mantenimiento').count()
    
    # Costo mensual total
    mes_actual = timezone.now().month
    anio_actual = timezone.now().year
    
    mantenimientos_mes = Mantenimiento.objects.filter(
        fecha_ingreso__month=mes_actual,
        fecha_ingreso__year=anio_actual
    )
    costo_mantenimientos_mes = mantenimientos_mes.aggregate(
        total=Sum('costo_total_real')
    )['total'] or Decimal('0')
    
    cargas_mes = CargaCombustible.objects.filter(
        fecha__month=mes_actual,
        fecha__year=anio_actual
    )
    costo_combustible_mes = cargas_mes.aggregate(
        total=Sum('costo_total')
    )['total'] or Decimal('0')
    
    costo_mensual_total = costo_mantenimientos_mes + costo_combustible_mes
    
    # Mantenimientos por vencer
    alertas_vigentes = AlertaMantencion.objects.filter(vigente=True).count()
    
    # Presupuestos por vencer (80% o más ejecutado)
    presupuestos_alerta = Presupuesto.objects.filter(
        monto_ejecutado__gte=F('monto_asignado') * Decimal('0.8')
    ).count()
    
    # Disponibilidad histórica
    vehiculos_con_disponibilidad = []
    for vehiculo in Vehiculo.objects.all()[:10]:
        # Sumar días de mantenimientos pasados
        dias_fuera = 0
        mants = Mantenimiento.objects.filter(vehiculo=vehiculo)
        for mant in mants:
            fin = mant.fecha_salida if mant.fecha_salida else timezone.now().date()
            delta = (fin - mant.fecha_ingreso).days
            dias_fuera += max(0, delta)
            
        vehiculos_con_disponibilidad.append({
            'vehiculo': vehiculo,
            'dias_fuera': dias_fuera,
        })
    
    # Próximos mantenimientos
    proximos_mantenimientos = Mantenimiento.objects.filter(
        estado='Programado'
    ).order_by('fecha_ingreso')[:5]
    
    # Alertas activas
    alertas_activas = AlertaMantencion.objects.filter(vigente=True).order_by('-generado_en')[:5]
    
    return render(request, 'flota/dashboard.html', {
        'total_vehiculos': total_vehiculos,
        'vehiculos_disponibles': vehiculos_disponibles,
        'vehiculos_mantenimiento': vehiculos_mantenimiento,
        'costo_mensual_total': costo_mensual_total,
        'alertas_vigentes': alertas_vigentes,
        'presupuestos_alerta': presupuestos_alerta,
        'vehiculos_con_disponibilidad': vehiculos_con_disponibilidad,
        'proximos_mantenimientos': proximos_mantenimientos,
        'alertas_activas': alertas_activas,
    })


# RF_28: Generar reporte de historial por unidad
@login_required
def reporte_historial_unidad(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Filtrar por fechas si se proporcionan
    filtros = {'vehiculo': vehiculo}
    filtros_combustible = {'patente_vehiculo': vehiculo}
    filtros_hoja = {'vehiculo': vehiculo}
    
    if fecha_inicio:
        filtros['fecha_ingreso__gte'] = fecha_inicio
        filtros_combustible['fecha__gte'] = fecha_inicio
        filtros_hoja['fecha__gte'] = fecha_inicio
    
    if fecha_fin:
        filtros['fecha_ingreso__lte'] = fecha_fin
        filtros_combustible['fecha__lte'] = fecha_fin
        filtros_hoja['fecha__lte'] = fecha_fin
    
    mantenimientos = Mantenimiento.objects.filter(**filtros).order_by('-fecha_ingreso')
    cargas_combustible = CargaCombustible.objects.filter(**filtros_combustible).order_by('-fecha')
    hojas_ruta = HojaRuta.objects.filter(**filtros_hoja).order_by('-fecha')
    incidentes = FallaReportada.objects.filter(vehiculo=vehiculo).order_by('-fecha_reporte')
    
    return render(request, 'flota/reporte_historial_unidad.html', {
        'vehiculo': vehiculo,
        'mantenimientos': mantenimientos,
        'cargas_combustible': cargas_combustible,
        'hojas_ruta': hojas_ruta,
        'incidentes': incidentes,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })

# Listar proveedores
@login_required
@user_passes_test(es_administrador)
def listar_proveedores(request):
    mostrar_deshabilitados = request.GET.get('mostrar_deshabilitados', 'false') == 'true'
    
    if mostrar_deshabilitados:
        proveedores = Proveedor.objects.all().order_by('nombre_fantasia')
    else:
        proveedores = Proveedor.objects.filter(activo=True).order_by('nombre_fantasia')
    
    return render(request, 'flota/listar_proveedores.html', {
        'proveedores': proveedores,
        'mostrar_deshabilitados': mostrar_deshabilitados,
    })

# Registrar proveedores
@login_required
@user_passes_test(es_administrador)
def registrar_proveedor(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f'Proveedor {proveedor.nombre_fantasia} registrado exitosamente.')
            return redirect('listar_proveedores')
    else:
        form = ProveedorForm()
    
    return render(request, 'flota/registrar_proveedor.html', {'form': form, 'titulo': 'Registrar Proveedor'})

# Modificar proveedores
@login_required
@user_passes_test(es_administrador)
def modificar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f'Proveedor {proveedor.nombre_fantasia} modificado exitosamente.')
            return redirect('listar_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)

    return render(request, 'flota/registrar_proveedor.html', {'form': form, 'titulo': 'Modificar Proveedor'})

# Habilitar proveedor
@login_required
@user_passes_test(es_administrador)
def habilitar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    
    if request.method == 'POST':
        proveedor.activo = True
        proveedor.save()
        messages.success(request, f'Proveedor {proveedor.nombre_fantasia} habilitado exitosamente.')
        return redirect('listar_proveedores')
    
    return render(request, 'flota/habilitar_proveedor.html', {'proveedor': proveedor})

# Deshabilitar proveedores
@login_required
@user_passes_test(es_administrador)
def deshabilitar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    if request.method == 'POST':
        proveedor.activo = False
        proveedor.save()
        messages.success(request, f'Proveedor {proveedor.nombre_fantasia} deshabilitado exitosamente.')
        return redirect('listar_proveedores')
    
    return render(request, 'flota/deshabilitar_proveedor.html', {'proveedor': proveedor})


def importar_orden_compra(request):
    if request.method == 'POST':
        codigo_oc = request.POST.get('codigo_oc', '').strip().upper()
        
        if not codigo_oc:
            messages.error(request, "Debe ingresar un código de Orden de Compra.")
            return redirect('importar_oc')

        # 1. Consultar API
        datos = consultar_oc_mercado_publico(codigo_oc)

        if 'error' in datos:
            messages.error(request, datos['error'])
        else:
            try:
                # 2. Gestionar Proveedor (Crear si no existe)
                proveedor, created_prov = Proveedor.objects.get_or_create(
                    rut_empresa=datos['proveedor_rut'],
                    defaults={
                        'nombre_fantasia': datos['proveedor_nombre'],
                        'giro': 'Importado desde Mercado Público',  # Valor por defecto
                        'telefono': '',
                        'email_contacto': '',  # La API no proporciona email
                        'es_taller': True,     # Asumir que es taller si es proveedor de mantenimiento
                        'es_arrendador': False,
                        'activo': True
                    }
                )
                
                if created_prov:
                    messages.info(request, f"Se ha creado el proveedor {proveedor.nombre_fantasia} automáticamente.")

                # 3. Crear Orden de Compra
                oc, created_oc = OrdenCompra.objects.get_or_create(
                    nro_oc=datos['codigo'],
                    defaults={
                        'descripcion': datos['descripcion'],
                        'fecha_emision': datos['fecha_emision'],
                        'monto_neto': datos.get('monto_neto', 0),
                        'monto_total': datos.get('monto_total', 0),
                        'impuesto': datos.get('impuestos', 0),
                        'id_licitacion': datos.get('id_licitacion', ''),
                        'estado': datos['estado'],
                        'proveedor': proveedor,
                        'tipo_adquisicion': 'Licitación Pública',  # Valor por defecto
                    }
                )

                if created_oc:
                    messages.success(request, f"Orden de Compra {oc.nro_oc} importada exitosamente.")
                    return redirect('detalle_orden_compra', id=oc.id)
                else:
                    messages.warning(request, f"La Orden de Compra {oc.nro_oc} ya existía en el sistema.")
                    return redirect('detalle_orden_compra', id=oc.id)

            except Exception as e:
                messages.error(request, f"Error al guardar en base de datos: {str(e)}")

        return redirect('importar_oc')

    return render(request, 'flota/importar_oc.html')


# RF_29: Registrar orden de compra
@login_required
@user_passes_test(es_administrador)
def registrar_orden_compra(request):
    if request.method == 'POST':
        form = OrdenCompraForm(request.POST, request.FILES)
        if form.is_valid():
            orden_compra = form.save()
            messages.success(request, f'Orden de Compra {orden_compra.nro_oc} registrada exitosamente.')
            return redirect('listar_ordenes_compra')
    else:
        form = OrdenCompraForm()
    
    return render(request, 'flota/registrar_orden_compra.html', {'form': form})


# RF_30: Listar órdenes de compra
@login_required
def listar_ordenes_compra(request):
    ordenes = OrdenCompra.objects.all().order_by('-fecha_emision', 'nro_oc')
    
    # Filtros
    estado_filter = request.GET.get('estado')
    proveedor_filter = request.GET.get('proveedor')
    
    if estado_filter:
        ordenes = ordenes.filter(estado=estado_filter)
    if proveedor_filter:
        ordenes = ordenes.filter(proveedor__id=proveedor_filter)
    
    proveedores = Proveedor.objects.all()
    
    return render(request, 'flota/listar_ordenes_compra.html', {
        'ordenes': ordenes,
        'proveedores': proveedores,
        'estado_filter': estado_filter,
        'proveedor_filter': proveedor_filter,
    })


# RF_31: Modificar orden de compra
@login_required
@user_passes_test(es_administrador)
def modificar_orden_compra(request, id):
    orden = get_object_or_404(OrdenCompra, id=id)
    if request.method == 'POST':
        form = OrdenCompraForm(request.POST, request.FILES, instance=orden)
        if form.is_valid():
            orden = form.save()
            messages.success(request, f'Orden de Compra {orden.nro_oc} modificada exitosamente.')
            return redirect('listar_ordenes_compra')
    else:
        form = OrdenCompraForm(instance=orden)
    
    return render(request, 'flota/modificar_orden_compra.html', {'form': form, 'orden': orden})


# RF_32: Eliminar orden de compra
@login_required
@user_passes_test(es_administrador)
def eliminar_orden_compra(request, id):
    orden = get_object_or_404(OrdenCompra, id=id)
    if request.method == 'POST':
        nro_oc = orden.nro_oc
        orden.delete()
        messages.success(request, f'Orden de Compra {nro_oc} eliminada exitosamente.')
        return redirect('listar_ordenes_compra')
    
    return render(request, 'flota/eliminar_orden_compra.html', {'orden': orden})


# RF_33: Detalle de orden de compra
@login_required
def detalle_orden_compra(request, id):
    orden = get_object_or_404(OrdenCompra, id=id)
    return render(request, 'flota/detalle_orden_compra.html', {'orden': orden})


# Registrar Orden de Trabajo
@login_required
@user_passes_test(es_administrador)
def registrar_orden_trabajo(request):
    if request.method == 'POST':
        form = OrdenTrabajoForm(request.POST)
        if form.is_valid():
            orden_trabajo = form.save()
            messages.success(request, f'Orden de Trabajo {orden_trabajo.nro_ot} registrada exitosamente.')
            return redirect('listar_ordenes_trabajo')
    else:
        form = OrdenTrabajoForm()
    
    return render(request, 'flota/registrar_orden_trabajo.html', {'form': form})


# Listar Órdenes de Trabajo
@login_required
def listar_ordenes_trabajo(request):
    ordenes = OrdenTrabajo.objects.all().order_by('-fecha_solicitud', 'nro_ot')
    
    # Filtros
    vehiculo_filter = request.GET.get('vehiculo')
    proveedor_filter = request.GET.get('proveedor')
    
    if vehiculo_filter:
        ordenes = ordenes.filter(vehiculo__patente=vehiculo_filter)
    if proveedor_filter:
        ordenes = ordenes.filter(proveedor__id=proveedor_filter)
    
    # Datos para filtros
    vehiculos = Vehiculo.objects.all().order_by('patente')
    proveedores = Proveedor.objects.filter(es_taller=True, activo=True).order_by('nombre_fantasia')
    
    return render(request, 'flota/listar_ordenes_trabajo.html', {
        'ordenes': ordenes,
        'vehiculos': vehiculos,
        'proveedores': proveedores,
        'vehiculo_filter': vehiculo_filter,
        'proveedor_filter': proveedor_filter,
    })


# Detalle de Orden de Trabajo
@login_required
def detalle_orden_trabajo(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    mantenimientos = Mantenimiento.objects.filter(orden_trabajo=orden)
    
    return render(request, 'flota/detalle_orden_trabajo.html', {
        'orden': orden,
        'mantenimientos': mantenimientos,
    })


# Modificar Orden de Trabajo
@login_required
@user_passes_test(es_administrador)
def modificar_orden_trabajo(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    if request.method == 'POST':
        form = OrdenTrabajoForm(request.POST, instance=orden)
        if form.is_valid():
            orden = form.save()
            messages.success(request, f'Orden de Trabajo {orden.nro_ot} modificada exitosamente.')
            return redirect('listar_ordenes_trabajo')
    else:
        form = OrdenTrabajoForm(instance=orden)
    
    return render(request, 'flota/modificar_orden_trabajo.html', {'form': form, 'orden': orden})


# Eliminar Orden de Trabajo
@login_required
@user_passes_test(es_administrador)
def eliminar_orden_trabajo(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    if request.method == 'POST':
        nro_ot = orden.nro_ot
        orden.delete()
        messages.success(request, f'Orden de Trabajo {nro_ot} eliminada exitosamente.')
        return redirect('listar_ordenes_trabajo')
    
    return render(request, 'flota/eliminar_orden_trabajo.html', {'orden': orden})
