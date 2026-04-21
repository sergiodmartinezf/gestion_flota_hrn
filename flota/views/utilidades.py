from ..models import Presupuesto

def es_administrador(user):
    return user.is_authenticated and user.rol == 'Administrador'


def es_conductor_o_admin(user):
    return user.is_authenticated and (user.rol == 'Administrador' or user.rol == 'Conductor')


# Función helper para verificar presupuesto
def verificar_presupuesto_cuenta(cuenta, anio, monto_requerido=0):
    """Verifica presupuesto disponible para una cuenta en un año"""
    presupuesto = Presupuesto.objects.filter(
        cuenta=cuenta,
        anio=anio,
        activo=True
    ).first()
    
    if not presupuesto:
        return False, f"No hay presupuesto para {cuenta.codigo} en {anio}.", None
    
    if monto_requerido > 0 and presupuesto.disponible < monto_requerido:
        return False, f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, Requerido: ${monto_requerido:.0f}", presupuesto
    
    return True, f"Presupuesto disponible: ${presupuesto.disponible:.0f}", presupuesto

