from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from ..models import Vehiculo, AlertaMantencion, CuentaPresupuestaria, Mantenimiento, Presupuesto
from .utilidades import verificar_presupuesto_vehiculo

# API para obtener el kilometraje de los vehículos
@login_required
def api_vehiculos_kilometraje(request):
    vehiculos = Vehiculo.objects.all()
    data = {}
    for vehiculo in vehiculos:
        data[str(vehiculo.patente)] = vehiculo.kilometraje_actual
    return JsonResponse(data)


@login_required
def api_alertas_count(request):
    """API para obtener el conteo de alertas activas (mantenimiento no pausadas + presupuesto >= 80%)."""
    # Alertas de mantenimiento vigentes, excluyendo pausadas (vehículo en taller con mantenimiento activo)
    ids_pausadas = set()
    for a in AlertaMantencion.objects.filter(vigente=True).select_related('vehiculo'):
        if a.vehiculo.estado == 'En mantenimiento' and Mantenimiento.objects.filter(
            vehiculo=a.vehiculo, estado__in=['En taller', 'Esperando repuestos'], fecha_salida__isnull=True
        ).exists():
            ids_pausadas.add(a.id)
    count_mant = AlertaMantencion.objects.filter(vigente=True).exclude(id__in=ids_pausadas).count()
    # Alertas de presupuesto (porcentaje ejecutado >= 80%)
    presupuestos_alerta = Presupuesto.objects.filter(activo=True).exclude(monto_asignado=0)
    count_presupuesto = sum(1 for p in presupuestos_alerta if p.porcentaje_ejecutado >= 80)
    total = count_mant + count_presupuesto
    return JsonResponse({'count': total, 'mantenimiento': count_mant, 'presupuesto': count_presupuesto})


# API para verificar presupuesto desde JavaScript
@login_required
def api_verificar_presupuesto(request):
    """API para verificar presupuesto desde el frontend"""
    vehiculo_id = request.GET.get('vehiculo')
    cuenta_id = request.GET.get('cuenta')
    anio = request.GET.get('anio', timezone.now().year)
    monto = request.GET.get('monto', 0)
    
    try:
        monto = Decimal(monto)
        vehiculo = Vehiculo.objects.get(patente=vehiculo_id)
        cuenta = CuentaPresupuestaria.objects.get(id=cuenta_id)
        
        tiene_presupuesto, mensaje, presupuesto = verificar_presupuesto_vehiculo(
            vehiculo, cuenta, int(anio), monto
        )
        
        return JsonResponse({
            'tiene_presupuesto': tiene_presupuesto,
            'mensaje': mensaje,
            'disponible': float(presupuesto.disponible) if presupuesto else 0,
            'porcentaje_ejecutado': float(presupuesto.porcentaje_ejecutado) if presupuesto else 0
        })
    except Exception as e:
        return JsonResponse({
            'tiene_presupuesto': False,
            'mensaje': f'Error: {str(e)}',
            'disponible': 0,
            'porcentaje_ejecutado': 0
        })

        