from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from ..models import Vehiculo, AlertaMantencion, CuentaPresupuestaria
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
    """API para obtener el conteo de alertas activas"""
    count = AlertaMantencion.objects.filter(vigente=True).count()
    return JsonResponse({'count': count})


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

        