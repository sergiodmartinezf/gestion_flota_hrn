from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from ..models import Vehiculo, AlertaMantencion, CuentaPresupuestaria, Mantenimiento, Presupuesto
from .utilidades import verificar_presupuesto_cuenta

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
    cuenta_id = request.GET.get('cuenta')
    anio = request.GET.get('anio')
    monto = request.GET.get('monto', 0)
    
    if not cuenta_id or not anio:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)
    
    try:
        cuenta = CuentaPresupuestaria.objects.get(id=cuenta_id)
        anio = int(anio)
        monto = float(monto)
    except (ValueError, CuentaPresupuestaria.DoesNotExist):
        return JsonResponse({'error': 'Parámetros inválidos'}, status=400)
    
    presupuesto = Presupuesto.objects.filter(cuenta=cuenta, anio=anio, activo=True).first()
    
    if not presupuesto:
        return JsonResponse({
            'tiene_presupuesto': False,
            'mensaje': f'No hay presupuesto para {cuenta.codigo} en {anio}.'
        })
    
    tiene_saldo = presupuesto.disponible >= monto
    porcentaje = (presupuesto.monto_ejecutado / presupuesto.monto_asignado * 100) if presupuesto.monto_asignado else 0
    
    return JsonResponse({
        'tiene_presupuesto': True,
        'tiene_saldo': tiene_saldo,
        'disponible': float(presupuesto.disponible),
        'porcentaje_ejecutado': porcentaje,
        'mensaje': f'Presupuesto disponible: ${presupuesto.disponible:.0f}'
    })
