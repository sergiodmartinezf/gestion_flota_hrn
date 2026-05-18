"""Validación de RUT chileno (dígito verificador)."""


def _separar_rut(rut):
    if not rut:
        return None, None
    rut = str(rut).strip().upper().replace('.', '').replace(' ', '')
    if not rut:
        return None, None
    if '-' in rut:
        partes = rut.split('-')
        if len(partes) != 2:
            return None, None
        cuerpo, dv = partes[0], partes[1]
    else:
        if len(rut) < 2:
            return None, None
        cuerpo, dv = rut[:-1], rut[-1]
    if not cuerpo.isdigit():
        return None, None
    return cuerpo, dv


def calcular_dv_rut(cuerpo):
    secuencia = [2, 3, 4, 5, 6, 7]
    suma = 0
    for i, digito in enumerate(reversed(cuerpo)):
        suma += int(digito) * secuencia[i % 6]
    resto = suma % 11
    dv = 11 - resto
    if dv == 11:
        return '0'
    if dv == 10:
        return 'K'
    return str(dv)


def formatear_rut(cuerpo, dv):
    cuerpo = str(cuerpo)
    partes = []
    while len(cuerpo) > 3:
        partes.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    if cuerpo:
        partes.insert(0, cuerpo)
    return f"{'.'.join(partes)}-{dv}"


def validar_rut_chileno(rut):
    """
    Valida un RUT chileno según el algoritmo del dígito verificador.
    Retorna (es_valido, mensaje_error).
    """
    cuerpo, dv = _separar_rut(rut)
    if not cuerpo or not dv:
        return False, 'Ingrese un RUT válido (ej: 12.345.678-9).'
    if len(cuerpo) < 7:
        return False, 'El RUT debe tener al menos 7 dígitos.'
    dv_calculado = calcular_dv_rut(cuerpo)
    if dv.upper() != dv_calculado:
        return False, 'El dígito verificador del RUT no es correcto.'
    return True, None


def normalizar_rut(rut):
    """Devuelve RUT formateado (12.345.678-9) o None si es inválido."""
    cuerpo, dv = _separar_rut(rut)
    if not cuerpo or not dv:
        return None
    es_valido, _ = validar_rut_chileno(rut)
    if not es_valido:
        return None
    return formatear_rut(cuerpo, dv.upper())
