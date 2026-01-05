from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Vehiculo, HojaRuta, AlertaMantencion, Mantenimiento, Presupuesto


@receiver(post_save, sender=HojaRuta)
def verificar_umbral_mantencion(sender, instance, **kwargs):
    """
    Crea una alerta automática cuando el kilometraje del vehículo
    se acerca o alcanza el umbral de mantenimiento.
    """
    vehiculo = instance.vehiculo
    
    # Calcular cuántos km faltan para el PRÓXIMO umbral de mantenimiento
    # Ejemplo: si umbral=10000 y km_actual=15000, próximo_umbral=20000, km_restantes=5000
    if vehiculo.umbral_mantencion > 0:
        proximo_umbral = ((vehiculo.kilometraje_actual // vehiculo.umbral_mantencion) + 1) * vehiculo.umbral_mantencion
        km_restantes = proximo_umbral - vehiculo.kilometraje_actual
    else:
        km_restantes = 0
    
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


@receiver(post_save, sender=Mantenimiento)
def verificar_alertas_fecha_mantenimiento(sender, instance, **kwargs):
    """
    Crea alertas automáticas cuando un mantenimiento programado se acerca a su fecha programada.
    """
    if instance.fecha_programada and instance.estado in ['Programado']:
        hoy = timezone.now().date()
        dias_restantes = (instance.fecha_programada - hoy).days
        
        # Crear alerta si faltan 7 días o menos para la fecha programada
        if 0 <= dias_restantes <= 7:
            alerta_existente = AlertaMantencion.objects.filter(
                vehiculo=instance.vehiculo,
                vigente=True,
                descripcion__icontains=f"Fecha programada: {instance.fecha_programada}"
            ).first()
            
            if not alerta_existente:
                AlertaMantencion.objects.create(
                    vehiculo=instance.vehiculo,
                    descripcion=f'Mantenimiento {instance.get_tipo_mantencion_display()} programado para {instance.fecha_programada.strftime("%d/%m/%Y")}. Faltan {dias_restantes} día(s).',
                    valor_umbral=0,  # Para alertas por fecha, no usamos kilometraje
                )
        
        # Crear alerta si ya pasó la fecha programada
        elif dias_restantes < 0:
            alerta_existente = AlertaMantencion.objects.filter(
                vehiculo=instance.vehiculo,
                vigente=True,
                descripcion__icontains=f"Fecha programada vencida: {instance.fecha_programada}"
            ).first()
            
            if not alerta_existente:
                AlertaMantencion.objects.create(
                    vehiculo=instance.vehiculo,
                    descripcion=f'Mantenimiento {instance.get_tipo_mantencion_display()} programado para {instance.fecha_programada.strftime("%d/%m/%Y")} está VENCIDO. Se requiere atención urgente.',
                    valor_umbral=0,
                )


@receiver(post_save, sender=Mantenimiento)
def actualizar_ejecucion_presupuesto(sender, instance, created, **kwargs):
    if instance.cuenta_presupuestaria:
        # Buscar y actualizar presupuesto
        presupuesto = Presupuesto.objects.filter(
            cuenta=instance.cuenta_presupuestaria,
            vehiculo=instance.vehiculo,
            anio=instance.fecha_ingreso.year
        ).first()
        
        if presupuesto:
            # Recalcular monto ejecutado sumando SOLO mantenimientos preventivos
            # según requisito: "presupuesto anual para lo preventivo"
            total_ejecutado = Mantenimiento.objects.filter(
                cuenta_presupuestaria=instance.cuenta_presupuestaria,
                vehiculo=instance.vehiculo,
                fecha_ingreso__year=instance.fecha_ingreso.year,
                tipo_mantencion='Preventivo'  # Solo mantenimientos preventivos
            ).aggregate(total=models.Sum('costo_total_real'))['total'] or 0
            
            presupuesto.monto_ejecutado = total_ejecutado
            presupuesto.save()

