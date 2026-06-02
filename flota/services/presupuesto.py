"""Validación y consulta de presupuesto (fuente única para forms, API, señales y vistas)."""

from decimal import Decimal


def obtener_presupuesto_activo(cuenta, anio):
    from ..models import Presupuesto

    return Presupuesto.objects.filter(
        cuenta=cuenta,
        anio=anio,
        activo=True,
    ).first()


def validar_presupuesto_disponible(cuenta, anio, monto_requerido=0):
    """
    Verifica existencia de presupuesto y saldo.

    Returns:
        (ok: bool, mensaje: str | None, presupuesto)
    """
    presupuesto = obtener_presupuesto_activo(cuenta, anio)
    if not presupuesto:
        return (
            False,
            f"No hay presupuesto asignado para la cuenta {cuenta.codigo} en el año {anio}.",
            None,
        )

    monto = Decimal(str(monto_requerido or 0))
    if monto > 0 and presupuesto.disponible < monto:
        return (
            False,
            (
                f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                f"Requerido: ${monto:.0f}"
            ),
            presupuesto,
        )

    return True, None, presupuesto


def mensaje_presupuesto_disponible(presupuesto):
    return f"Presupuesto disponible: ${presupuesto.disponible:.0f}"
