from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Vehiculo, HojaRuta, AlertaMantencion


@receiver(post_save, sender=HojaRuta)
def verificar_umbral_mantencion(sender, instance, **kwargs):
    """
    Crea una alerta automática cuando el kilometraje del vehículo
    se acerca o alcanza el umbral de mantenimiento.
    """
    vehiculo = instance.vehiculo
    
    # Verificar si el kilometraje actual está cerca del umbral
    km_restantes = vehiculo.umbral_mantencion - (vehiculo.kilometraje_actual % vehiculo.umbral_mantencion)
    
    # Crear alerta si faltan menos de 1000 km para el mantenimiento
    if km_restantes <= 1000 and km_restantes > 0:
        # Verificar si ya existe una alerta vigente para este vehículo
        alerta_existente = AlertaMantencion.objects.filter(
            vehiculo=vehiculo,
            vigente=True,
            valor_umbral__gte=vehiculo.kilometraje_actual - 1000
        ).first()
        
        if not alerta_existente:
            AlertaMantencion.objects.create(
                vehiculo=vehiculo,
                descripcion=f'El vehículo {vehiculo.patente} requiere mantenimiento preventivo. Faltan aproximadamente {km_restantes} km.',
                valor_umbral=vehiculo.kilometraje_actual,
            )
    
    # Crear alerta si ya se pasó el umbral
    elif vehiculo.kilometraje_actual >= vehiculo.umbral_mantencion:
        alerta_existente = AlertaMantencion.objects.filter(
            vehiculo=vehiculo,
            vigente=True,
            valor_umbral__gte=vehiculo.umbral_mantencion
        ).first()
        
        if not alerta_existente:
            AlertaMantencion.objects.create(
                vehiculo=vehiculo,
                descripcion=f'El vehículo {vehiculo.patente} ha superado el umbral de mantenimiento ({vehiculo.umbral_mantencion} km). Se requiere mantenimiento urgente.',
                valor_umbral=vehiculo.kilometraje_actual,
            )

