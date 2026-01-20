from ..models import Presupuesto

def es_administrador(user):
    return user.is_authenticated and user.rol == 'Administrador'


def es_conductor_o_admin(user):
    return user.is_authenticated and (user.rol == 'Administrador' or user.rol == 'Conductor')


# Función helper para verificar presupuesto
def verificar_presupuesto_vehiculo(vehiculo, cuenta_presupuestaria, anio, monto_requerido=0):
    """
    Verifica si un vehículo tiene presupuesto asignado.
    Retorna (tiene_presupuesto, mensaje, presupuesto_obj)
    """
    # Buscar presupuesto específico del vehículo
    presupuesto = Presupuesto.objects.filter(
        cuenta=cuenta_presupuestaria,
        vehiculo=vehiculo,
        anio=anio,
        activo=True
    ).first()
    
    # Si no hay específico, buscar global
    if not presupuesto:
        presupuesto = Presupuesto.objects.filter(
            cuenta=cuenta_presupuestaria,
            vehiculo__isnull=True,
            anio=anio,
            activo=True
        ).first()
    
    if not presupuesto:
        return False, f"No hay presupuesto asignado para la cuenta {cuenta_presupuestaria.codigo} en el año {anio}.", None
    
    if monto_requerido > 0 and presupuesto.disponible < monto_requerido:
        return False, f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, Requerido: ${monto_requerido:.0f}", presupuesto
    
    return True, f"Presupuesto disponible: ${presupuesto.disponible:.0f}", presupuesto


