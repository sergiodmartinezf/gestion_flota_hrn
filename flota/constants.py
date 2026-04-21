# Mapeo de (tipo_mantencion, criticidad) -> lista de IDs de CuentaPresupuestaria
MANTENIMIENTO_CUENTAS_MAP = {
    ('Preventivo', 'Crítico'): [1],      # ID de cuenta preventivo-crítico
    ('Correctivo', 'Crítico'): [2],      # ID de cuenta correctivo-crítico
    ('Preventivo', 'No crítico'): [3],   # ID de cuenta preventivo-no crítico
    ('Correctivo', 'No crítico'): [4],   # ID de cuenta correctivo-no crítico
}
