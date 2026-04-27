from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F
from decimal import Decimal
from ..models import Vehiculo, Mantenimiento, CargaCombustible, Alerta, Presupuesto, Arriendo

# RF_27: Visualizar panel de indicadores (Dashboard)
@login_required
def dashboard(request):
    # --- PROTECCIÓN: Si el usuario es Conductor, redirigir al registro de bitácora ---
    if request.user.rol == 'Conductor':
        return redirect('registrar_bitacora')
    # ---------------------------------------------------------------------------------

    # Estadísticas generales (Solo se ejecutan para Admin/Visualizador)
    total_vehiculos = Vehiculo.objects.count()
    vehiculos_disponibles = Vehiculo.objetos_operativos().filter(estado='Disponible').count()
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
            if m.fecha_salida:
                delta = (m.fecha_salida - m.fecha_ingreso).days
                dias_fuera += max(0, delta)
            
        vehiculos_con_disponibilidad.append({
            'vehiculo': vehiculo,
            'dias_fuera': dias_fuera,
        })
    
    # Próximos mantenimientos
    proximos_mantenimientos = Mantenimiento.objects.filter(
        estado='Programado'
    ).order_by('fecha_ingreso')[:5]
    
    # Alertas de mantenimiento activas (excluir pausadas: vehículo en taller con mantenimiento activo)
    ids_pausadas = set()
    for a in Alerta.objects.filter(vigente=True).select_related('vehiculo')[:50]:
        if a.vehiculo.estado == 'En mantenimiento' and Mantenimiento.objects.filter(
            vehiculo=a.vehiculo, estado__in=['En taller', 'Esperando repuestos'], fecha_salida__isnull=True
        ).exists():
            ids_pausadas.add(a.id)
    alertas_operativas = Alerta.objects.filter(vigente=True).exclude(
        id__in=ids_pausadas
    ).order_by('-generado_en')

    presupuestos_en_riesgo = [
        p for p in Presupuesto.objects.filter(activo=True).exclude(monto_asignado=0)
        if p.porcentaje_ejecutado >= 80
    ]

    # Unificar alertas activas en una sola colección (mantenimiento + presupuesto)
    alertas_activas = []
    for alerta in alertas_operativas:
        alertas_activas.append({
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

    # Conteo por tipo y total
    alertas_operativas_vigentes = alertas_operativas.count()
    presupuestos_alerta = len(presupuestos_en_riesgo)
    alertas_vigentes = alertas_operativas_vigentes + presupuestos_alerta
    
    # Vehículos arrendados (arriendos activos)
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
    })

