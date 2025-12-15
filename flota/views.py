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

from .models import (
    Usuario, Vehiculo, Proveedor, OrdenCompra, OrdenTrabajo,
    Presupuesto, Arriendo, HojaRuta,
    Viaje, CargaCombustible, Mantenimiento, AlertaMantencion,
    FallaReportada
)
from .forms import (
    LoginForm, UsuarioForm, VehiculoForm, ProveedorForm,
    HojaRutaForm, ViajeForm, CargaCombustibleForm, MantenimientoForm,
    FallaReportadaForm, PresupuestoForm, ArriendoForm, OrdenCompraForm
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
            usuario = form.save()
            messages.success(request, f'Usuario {usuario.nombre_completo} registrado exitosamente.')
            return redirect('listar_usuarios')
    else:
        form = UsuarioForm()
    
    return render(request, 'flota/registrar_usuario.html', {'form': form})


# RF_03: Listar usuarios
@login_required
@user_passes_test(es_administrador)
def listar_usuarios(request):
    usuarios = Usuario.objects.all().order_by('apellido', 'nombre')
    return render(request, 'flota/listar_usuarios.html', {'usuarios': usuarios})


# RF_04: Modificar usuario
@login_required
@user_passes_test(es_administrador)
def modificar_usuario(request, rut):
    usuario = get_object_or_404(Usuario, rut=rut)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario {usuario.nombre_completo} modificado exitosamente.')
            return redirect('listar_usuarios')
    else:
        form = UsuarioForm(instance=usuario)
    
    return render(request, 'flota/modificar_usuario.html', {'form': form, 'usuario': usuario})


# RF_05: Deshabilitar usuario
@login_required
@user_passes_test(es_administrador)
def deshabilitar_usuario(request, rut):
    usuario = get_object_or_404(Usuario, rut=rut)
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
            
            messages.success(request, 'Bitácora registrada exitosamente.')
            return redirect('listar_bitacoras')
    else:
        form = HojaRutaForm()
    
    return render(request, 'flota/registrar_bitacora.html', {'form': form})


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
            carga = form.save(commit=False)
            if request.user.rol == 'Conductor':
                carga.conductor = request.user
            carga.save()
            messages.success(request, 'Carga de combustible registrada exitosamente.')
            return redirect('listar_cargas_combustible')
    else:
        form = CargaCombustibleForm()
    
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
            falla = form.save(commit=False)
            falla.conductor = request.user
            falla.save()
            
            # Crear alerta si es necesario
            vehiculo = falla.vehiculo
            if vehiculo.kilometraje_actual >= vehiculo.umbral_mantencion:
                AlertaMantencion.objects.create(
                    vehiculo=vehiculo,
                    descripcion=f'Falla reportada: {falla.descripcion}',
                    valor_umbral=vehiculo.kilometraje_actual,
                )
            
            messages.success(request, 'Incidente registrado exitosamente.')
            return redirect('listar_incidentes')
    else:
        form = FallaReportadaForm()
    
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
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            mantenimiento = form.save(commit=False)
            mantenimiento.tipo_mantencion = 'Preventivo'
            mantenimiento.estado = 'Programado'
            mantenimiento.save()
            
            # Actualizar estado del vehículo
            vehiculo = mantenimiento.vehiculo
            vehiculo.estado = 'En mantenimiento'
            vehiculo.save()
            
            messages.success(request, 'Mantenimiento preventivo programado exitosamente.')
            return redirect('listar_mantenimientos')
    else:
        form = MantenimientoForm(initial={'tipo_mantencion': 'Preventivo', 'estado': 'Programado'})
    
    return render(request, 'flota/programar_mantenimiento_preventivo.html', {'form': form})


# RF_19: Registrar mantenimiento ejecutado
@login_required
@user_passes_test(es_administrador)
def registrar_mantenimiento_ejecutado(request):
    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            mantenimiento = form.save()
            
            # Actualizar presupuesto si existe
            if mantenimiento.cuenta_presupuestaria:
                presupuestos = Presupuesto.objects.filter(
                    vehiculo=mantenimiento.vehiculo,
                    anio=mantenimiento.fecha_ingreso.year,
                    cuenta=mantenimiento.cuenta_presupuestaria
                )
                for presupuesto in presupuestos:
                    presupuesto.monto_ejecutado += mantenimiento.costo_total_real
                    presupuesto.save()
            
            # Actualizar estado del vehículo
            vehiculo = mantenimiento.vehiculo
            if mantenimiento.fecha_salida:
                vehiculo.estado = 'Disponible'
                vehiculo.save()
            
            messages.success(request, 'Mantenimiento ejecutado registrado exitosamente.')
            return redirect('listar_mantenimientos')
    else:
        form = MantenimientoForm()
    
    return render(request, 'flota/registrar_mantenimiento_ejecutado.html', {'form': form})


# RF_20: Listar mantenimientos
@login_required
def listar_mantenimientos(request):
    patente = request.GET.get('patente')
    mantenimientos = Mantenimiento.objects.all()
    
    if patente:
        mantenimientos = mantenimientos.filter(vehiculo__patente=patente)
    
    mantenimientos = mantenimientos.order_by('-fecha_ingreso')
    
    return render(request, 'flota/listar_mantenimientos.html', {
        'mantenimientos': mantenimientos,
        'patente_filter': patente,
    })


# RF_21: Registrar presupuesto anual por convenio
@login_required
@user_passes_test(es_administrador)
def registrar_presupuesto(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST)
        if form.is_valid():
            presupuesto = form.save()
            messages.success(request, 'Presupuesto registrado exitosamente.')
            return redirect('listar_presupuestos')
    else:
        form = PresupuestoForm()
    
    return render(request, 'flota/registrar_presupuesto.html', {'form': form})


@login_required
def listar_presupuestos(request):
    presupuestos = Presupuesto.objects.all().order_by('-anio', 'vehiculo')
    return render(request, 'flota/listar_presupuestos.html', {'presupuestos': presupuestos})


# RF_22: Visualizar alertas de presupuesto
@login_required
def alertas_presupuesto(request):
    presupuestos = Presupuesto.objects.all()
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


# RF_23: Visualizar calendario de mantenciones
@login_required
def calendario_mantenciones(request):
    mantenimientos = Mantenimiento.objects.filter(estado__in=['Programado', 'En taller']).order_by('fecha_ingreso')
    return render(request, 'flota/calendario_mantenciones.html', {'mantenimientos': mantenimientos})


# RF_24: Generar reporte de costos
@login_required
def reporte_costos(request):
    vehiculos = Vehiculo.objects.all()
    reporte = []
    
    for vehiculo in vehiculos:
        mantenimientos = Mantenimiento.objects.filter(vehiculo=vehiculo)
        costo_mantenimientos = mantenimientos.aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
        
        cargas = CargaCombustible.objects.filter(patente_vehiculo=vehiculo)
        costo_combustible = cargas.aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
        
        arriendos = Arriendo.objects.filter(vehiculo=vehiculo)
        costo_arriendos = arriendos.aggregate(total=Sum('costo_total_real'))['total'] or Decimal('0')
        
        costo_total = costo_mantenimientos + costo_combustible + costo_arriendos
        costo_por_km = costo_total / vehiculo.kilometraje_actual if vehiculo.kilometraje_actual > 0 else Decimal('0')
        
        presupuesto = Presupuesto.objects.filter(vehiculo=vehiculo).aggregate(
            total=Sum('monto_asignado')
        )['total'] or Decimal('0')
        
        reporte.append({
            'vehiculo': vehiculo,
            'costo_mantenimientos': costo_mantenimientos,
            'costo_combustible': costo_combustible,
            'costo_arriendos': costo_arriendos,
            'costo_total': costo_total,
            'costo_por_km': costo_por_km,
            'presupuesto': presupuesto,
        })
    
    return render(request, 'flota/reporte_costos.html', {'reporte': reporte})


# RF_25: Generar reporte de disponibilidad
# En flota/views.py

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
            'vehiculo': vehiculo,
            'dias_fuera_servicio': total_dias_fuera,
            'incidentes': incidentes,
            'estado': vehiculo.estado,
        })
    
    return render(request, 'flota/reporte_disponibilidad.html', {'reporte': reporte})


# RF_26: Registrar arriendo
@login_required
@user_passes_test(es_administrador)
def registrar_arriendo(request):
    if request.method == 'POST':
        form = ArriendoForm(request.POST)
        if form.is_valid():
            arriendo = form.save()
            # Actualizar estado del vehículo
            if arriendo.vehiculo_reemplazado:
                vehiculo = arriendo.vehiculo_reemplazado
                vehiculo.tipo_propiedad = 'Arrendado'
                vehiculo.save()

            vehiculo.tipo_propiedad = 'Arrendado'
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
    proveedores = Proveedor.objects.all().order_by('nombre_fantasia')
    return render(request, 'flota/listar_proveedores.html', {'proveedores': proveedores})

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

# Eliminar proveedores
@login_required
@user_passes_test(es_administrador)
def eliminar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    if request.method == 'POST':
        nombre_fantasia = proveedor.nombre_fantasia
        proveedor.delete()
        messages.success(request, f'Proveedor {nombre_fantasia} eliminado exitosamente.')
        return redirect('listar_proveedores')
    
    return render(request, 'flota/eliminar_proveedor.html', {'proveedor': proveedor})


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
