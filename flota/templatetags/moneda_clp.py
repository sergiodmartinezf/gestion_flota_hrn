from django import template

register = template.Library()


@register.filter(name="clp")
def clp(value):
    """
    Formatea un monto en pesos chilenos como entero con separador de miles usando puntos (ej: 1234567 -> '1.234.567'). No agrega el símbolo $ para permitir flexibilidad en los templates.
    """
    if value is None:
        return ""

    try:
        numero = float(value)
    except (TypeError, ValueError):
        return ""

    entero = int(round(numero))
    return f"{entero:,}".replace(",", ".")

