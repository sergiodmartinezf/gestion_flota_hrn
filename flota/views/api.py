from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from ..models import Vehiculo, CuentaPresupuestaria
from ..services.alertas import contar_alertas_vigentes
from ..services.presupuesto import validar_presupuesto_disponible

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
    """
    API para obtener el conteo de alertas activas (mantenimiento no pausadas + presupuesto >= 80%).
    """
    return JsonResponse(contar_alertas_vigentes())


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
    
    ok, mensaje, presupuesto = validar_presupuesto_disponible(cuenta, anio, monto)

    if not presupuesto:
        return JsonResponse({
            'tiene_presupuesto': False,
            'mensaje': mensaje,
        })

    tiene_saldo = ok
    porcentaje = (
        presupuesto.monto_ejecutado / presupuesto.monto_asignado * 100
    ) if presupuesto.monto_asignado else 0

    return JsonResponse({
        'tiene_presupuesto': True,
        'tiene_saldo': tiene_saldo,
        'disponible': float(presupuesto.disponible),
        'porcentaje_ejecutado': porcentaje,
        'mensaje': mensaje if not ok else f'Presupuesto disponible: ${presupuesto.disponible:.0f}',
    })
