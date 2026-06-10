"""
Constantes de dominio y helpers de cuentas presupuestarias (códigos SIGFE).
"""

# Cuentas de mantenimiento (datos/cuenta_presupuestaria.csv)
CUENTA_PREVENTIVO_CRITICO = '22.06.002.001'
CUENTA_CORRECTIVO_CRITICO = '22.06.002.002'
CUENTA_PREVENTIVO_NO_CRITICO = '22.06.002.003'
CUENTA_CORRECTIVO_NO_CRITICO = '22.06.002.004'

PREVENTIVE_ACCOUNT_CODES = [CUENTA_PREVENTIVO_CRITICO, CUENTA_PREVENTIVO_NO_CRITICO]
CORRECTIVE_ACCOUNT_CODES = [CUENTA_CORRECTIVO_CRITICO, CUENTA_CORRECTIVO_NO_CRITICO]
ALL_MAINTENANCE_ACCOUNT_CODES = PREVENTIVE_ACCOUNT_CODES + CORRECTIVE_ACCOUNT_CODES

# (tipo_mantencion, criticidad del vehículo) -> códigos SIGFE permitidos
MANTENIMIENTO_CUENTAS_CODIGOS = {
    ('Preventivo', 'Crítico'): [CUENTA_PREVENTIVO_CRITICO],
    ('Correctivo', 'Crítico'): [CUENTA_CORRECTIVO_CRITICO],
    ('Preventivo', 'No crítico'): [CUENTA_PREVENTIVO_NO_CRITICO],
    ('Correctivo', 'No crítico'): [CUENTA_CORRECTIVO_NO_CRITICO],
}


def _cuentas_model():
    from .models import CuentaPresupuestaria
    return CuentaPresupuestaria


def ids_cuentas_por_codigos(codigos):
    CuentaPresupuestaria = _cuentas_model()
    return list(
        CuentaPresupuestaria.objects.filter(codigo__in=codigos).values_list('id', flat=True)
    )


def mapa_mantenimiento_cuenta_ids():
    """
    Equivalente al antiguo MANTENIMIENTO_CUENTAS_MAP, con IDs resueltos desde BD.
    """
    return {
        clave: ids_cuentas_por_codigos(codigos)
        for clave, codigos in MANTENIMIENTO_CUENTAS_CODIGOS.items()
    }


def ids_cuentas_por_tipo_mantencion(tipo_mantencion):
    """
    IDs de cuentas asociadas a un tipo de mantención (o todas si tipo vacío).
    """
    if not tipo_mantencion:
        return ids_cuentas_por_codigos(ALL_MAINTENANCE_ACCOUNT_CODES)

    codigos = set()
    for (tipo, _), lista in MANTENIMIENTO_CUENTAS_CODIGOS.items():
        if tipo == tipo_mantencion:
            codigos.update(lista)
    return ids_cuentas_por_codigos(codigos)


def cuenta_valida_para_mantenimiento(cuenta, tipo_mantencion, criticidad_vehiculo):
    codigos = MANTENIMIENTO_CUENTAS_CODIGOS.get((tipo_mantencion, criticidad_vehiculo), [])
    return cuenta.codigo in codigos
