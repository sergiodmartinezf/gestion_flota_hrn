from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F
from decimal import Decimal
from ..models import Vehiculo, Mantenimiento, CargaCombustible, AlertaMantencion, Presupuesto

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
    
    # Crear alerta de prueba si no hay ninguna (DEBUG)
    if not AlertaMantencion.objects.filter(vigente=True).exists():
        vehiculo_prueba = Vehiculo.objects.first()
        if vehiculo_prueba:
            AlertaMantencion.objects.create(
                vehiculo=vehiculo_prueba,
                descripcion="Alerta de prueba: Mantenimiento requerido próximamente.",
                valor_umbral=10000,
                vigente=True
            )

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

