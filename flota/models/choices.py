TIPOS_SERVICIO = [
    ('Llamado', 'Llamado'),
    ('Rescate de Paciente', 'Rescate de Paciente'),
    ('A Urgencia HBO', 'A Urgencia HBO'),
    ('Exámenes', 'Exámenes'),
    ('Alta a Domicilio', 'Alta a Domicilio'),
    ('Interconsulta', 'Interconsulta'),
    ('Horas a especialista', 'Horas a especialista'),
    ('Imagen', 'Imagen'),
    ('Administrativo', 'Administrativo'), # Agregado para camionetas
    ('Otro', 'Otro'),
]

ROL_TRIPULACION = [
    ('MEDICO', 'Médico'),
    ('TENS', 'TENS'),
    ('ENFERMERO', 'Enfermero/Matrón'),
    ('CAMILLERO', 'Camillero'),
]

TURNOS = [
    ('08-20', 'Turno 08:00 a 20:00'),
    ('20-08', 'Turno 20:00 a 08:00'),
    ('09-20', 'Turno 09:00 a 20:00 (fin de semana/feriado)'),
    ('20-09', 'Turno 20:00 a 09:00 (fin de semana/feriado)'),
    ('08-17', 'Turno 08:00 a 17:00 (Horario Administrativo)'),
]

TIPO_TRASLADO_CATEGORIA = [
    ('PRIMARIO', 'Traslado Primario (Lugar del evento -> Urgencia)'),
    ('SECUNDARIO', 'Traslado Secundario (Urgencia -> Hospital Base/Red)'),
    ('OTROS', 'Otros Traslados (Rescates, Exámenes, Especialista)'),
    ('ALTA', 'Altas'),
    ('Administrativo', 'Administrativo'),
]

# Subcategorías para lógica de negocio
ORIGEN_ALTA = [
    ('URGENCIA', 'Desde Servicio de Urgencia'),
    ('HOSPITALIZADO', 'Desde Hospitalizado'),
    ('HBO', 'Desde Hospital Base Osorno'),
]

DESTINOS_RED_HOSPITAL = [
    ('HBO', 'Hospital Base Osorno'),
    ('HEPP_PURRANQUE', 'Hospital Dr. Juan Hepp Purranque'),
    ('H_PUERTO_OCTAY', 'Hospital Puerto Octay'),
    ('H_RIO_NEGRO', 'Hospital Río Negro'),
    ('H_FUTA', 'Hospital Futa Srüka Lawenche Kunko Mapu Mo'),
    ('H_PU_MULEN', 'Hospital Pu Mülen'),
]

DESTINOS_COMUNES = DESTINOS_RED_HOSPITAL + [
    ('DOMICILIO', 'Domicilio (Ingresar Dirección)'),
    ('CESFAM', 'CESFAM'),
    ('ACHS', 'ACHS/Mutual'),
    ('OTRO', 'Otro (Especificar)'),
]

CODIGOS_DESTINOS_RED = {codigo for codigo, _ in DESTINOS_RED_HOSPITAL}

# Estados de ordenes de compra
def normalizar_estado_oc(estado):
    """
    Normaliza cualquier variante de estado de orden de compra a los estados estándar.
    
    Mapea estados de Mercado Público y variantes a estados internos consistentes.
    """
    if not estado:
        return 'Emitida'
    
    estado = str(estado).strip().upper()
    
    # Mapeo de estados de Mercado Público a estados internos
    mapa_mercadopublico = {
        'RECEPCIÓN CONFORME': 'RECEPCIONADA',
        'RECEPCION CONFORME': 'RECEPCIONADA',
        'RECEPCIONADA PARCIALMENTE': 'RECEPCIONADA',
        'RECEPCION ACEPTADA PARCIALMENTE': 'RECEPCIONADA',
        'RECEPCION CONFORME INCOMPLETA': 'RECEPCIONADA',
        'PENDIENTE DE RECEPCIONAR': 'EMITIDA',
        'ENVIADA A PROVEEDOR': 'EMITIDA',
        'EN PROCESO': 'EMITIDA',
        'CANCELADA': 'ANULADA',
    }
    
    # Mapeo de variantes comunes
    mapa_variantes = {
        'RECEPCIONADA': 'RECEPCIONADA',
        'RECIBIDA': 'RECEPCIONADA',
        'ENTREGADA': 'RECEPCIONADA',
        'FINALIZADA': 'RECEPCIONADA',
        'CONCLUIDA': 'RECEPCIONADA',
        'ACEPTADA': 'ACEPTADA',
        'APROBADA': 'ACEPTADA',
        'VALIDADA': 'ACEPTADA',
        'EMITIDA': 'EMITIDA',
        'CREADA': 'EMITIDA',
        'GENERADA': 'EMITIDA',
        'PAGADA': 'PAGADA',
        'LIQUIDADA': 'PAGADA',
        'FACTURADA': 'PAGADA',
        'ANULADA': 'ANULADA',
        'CANCELADA': 'ANULADA',
        'ELIMINADA': 'ANULADA',
        'RECHAZADA': 'ANULADA',
    }
    
    # Primero buscar en el mapeo de Mercado Público
    if estado in mapa_mercadopublico:
        return mapa_mercadopublico[estado]
    
    # Luego buscar en el mapeo de variantes
    if estado in mapa_variantes:
        return mapa_variantes[estado]
    
    # Si no encuentra coincidencia, intentar coincidencia parcial
    for clave, valor in mapa_mercadopublico.items():
        if clave in estado or estado in clave:
            return valor
    
    for clave, valor in mapa_variantes.items():
        if clave in estado or estado in clave:
            return valor
    
    # Por defecto, devolver Emitida
    return 'EMITIDA'


def normalizar_estado_visual(estado_normalizado):
    """
    Convierte un estado normalizado a su forma legible para mostrar en interfaces.
    """
    estados_visuales = {
        'EMITIDA': 'Emitida',
        'ACEPTADA': 'Aceptada',
        'RECEPCIONADA': 'Recepcionada',
        'PAGADA': 'Pagada',
        'ANULADA': 'Anulada',
    }
    return estados_visuales.get(estado_normalizado, estado_normalizado)

