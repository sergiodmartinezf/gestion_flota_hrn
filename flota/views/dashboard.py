from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from ..models import Vehiculo, Mantenimiento, CargaCombustible, Arriendo
from ..services.alertas import alertas_mantenimiento_vigentes, presupuestos_con_alerta
from .utilidades import puede_escribir

@login_required
def dashboard(request):
    if request.user.rol == 'Conductor':
        return redirect('registrar_bitacora')

    total_vehiculos = Vehiculo.objects.count()
    vehiculos_disponibles = Vehiculo.objetos_operativos().filter(estado='Disponible').count()
    vehiculos_mantenimiento = Vehiculo.objects.filter(estado='En mantenimiento').count()

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
            if m.fecha_salida:
                delta = (m.fecha_salida - m.fecha_ingreso).days
                dias_fuera += max(0, delta)
            
        vehiculos_con_disponibilidad.append({
            'vehiculo': vehiculo,
            'dias_fuera': dias_fuera,
        })

    proximos_mantenimientos = Mantenimiento.objects.filter(
        estado='Programado'
    ).order_by('fecha_ingreso')[:5]

    alertas_operativas = alertas_mantenimiento_vigentes()
    presupuestos_en_riesgo = presupuestos_con_alerta()

    alertas_activas = []
    for alerta in alertas_operativas:
        alertas_activas.append({
            'id': alerta.id,
            'tipo_alerta': 'mantenimiento',
            'tipo': 'Mantenimiento',
            'fecha': alerta.generado_en,
            'titulo': alerta.vehiculo.patente,
            'descripcion': alerta.descripcion,
            'detalle': f"Umbral: {alerta.valor_umbral} km",
            'clase_item': 'list-group-item-warning',
            'icono': 'bi-car-front',
        })

    ahora = timezone.now()
    for presupuesto in presupuestos_en_riesgo:
        alertas_activas.append({
            'id': presupuesto.id,
            'tipo_alerta': 'presupuesto',
            'tipo': 'Presupuesto',
            'fecha': ahora,
            'titulo': f"{presupuesto.cuenta.codigo} ({presupuesto.anio})",
            'descripcion': (
                f"Ejecución en riesgo: {presupuesto.porcentaje_ejecutado:.1f}% del monto asignado."
            ),
            'detalle': f"Disponible: ${presupuesto.disponible:,.0f}",
            'clase_item': 'list-group-item-danger',
            'icono': 'bi-cash-stack',
        })

    alertas_activas = sorted(alertas_activas, key=lambda a: a['fecha'], reverse=True)[:5]

    alertas_operativas_vigentes = alertas_operativas.count()
    presupuestos_alerta = len(presupuestos_en_riesgo)
    alertas_vigentes = alertas_operativas_vigentes + presupuestos_alerta

    arriendos_activos = Arriendo.objects.filter(estado='Activo').select_related(
        'vehiculo_arrendado', 'vehiculo_reemplazado', 'proveedor'
    ).order_by('-fecha_inicio')
    
    return render(request, 'flota/dashboard.html', {
        'total_vehiculos': total_vehiculos,
        'vehiculos_disponibles': vehiculos_disponibles,
        'vehiculos_mantenimiento': vehiculos_mantenimiento,
        'costo_mensual_total': costo_mensual_total,
        'vehiculos_con_disponibilidad': vehiculos_con_disponibilidad,
        'proximos_mantenimientos': proximos_mantenimientos,
        'alertas_activas': alertas_activas,
        'alertas_vigentes': alertas_vigentes,
        'alertas_operativas_vigentes': alertas_operativas_vigentes,
        'presupuestos_alerta': presupuestos_alerta,
        'arriendos_activos': arriendos_activos,
        'puede_eliminar_alertas': puede_escribir(request.user),
    })
