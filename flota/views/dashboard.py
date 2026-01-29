from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F
from decimal import Decimal
from ..models import Vehiculo, Mantenimiento, CargaCombustible, AlertaMantencion, Presupuesto

# RF_27: Visualizar panel de indicadores (Dashboard)
@login_required
def dashboard(request):
    # --- PROTECCIÓN: Si el usuario es Conductor, redirigir al registro de bitácora ---
    if request.user.rol == 'Conductor':
        return redirect('registrar_bitacora')
    # ---------------------------------------------------------------------------------

    # Estadísticas generales (Solo se ejecutan para Admin/Visualizador)
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

    # Datos para gráficos de disponibilidad
    vehiculos = Vehiculo.objects.all()
    vehiculos_con_disponibilidad = []
    
    for vehiculo in vehiculos:
        mantenimientos_vehiculo = Mantenimiento.objects.filter(
            vehiculo=vehiculo,
            fecha_ingreso__month=mes_actual,
            fecha_ingreso__year=anio_actual
        )
        
        dias_fuera = 0
        for m in mantenimientos_vehiculo:
            if m.fecha_entrega:
                delta = (m.fecha_entrega - m.fecha_ingreso.date()).days
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
        'vehiculos_con_disponibilidad': vehiculos_con_disponibilidad,
        'proximos_mantenimientos': proximos_mantenimientos,
        'alertas_activas': alertas_activas,
    })

