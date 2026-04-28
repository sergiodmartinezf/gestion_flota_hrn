# flota/templatetags/flota_extras.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def km(value):
    """
    Formatea un número (kilómetros) con separador de miles como punto.
    Ejemplo: 12000 -> "12.000"
    """
    if value is None:
        return "0"
    try:
        # Convierte a entero, manejando Decimal o string
        num = int(Decimal(str(value)))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return str(value)
    # Formato chileno: puntos como separador de miles
    return f"{num:,}".replace(",", ".")
    