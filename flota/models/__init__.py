"""Modelos de dominio (reexportación compatible con `from flota.models import ...`)."""

from .choices import *
from .usuario import Usuario, UsuarioManager
from .proveedor import Proveedor, CuentaPresupuestaria
from .presupuesto import Presupuesto
from .vehiculo import Vehiculo
from .orden_trabajo import OrdenTrabajo
from .orden_compra import OrdenCompra
from .mantenimiento import Mantenimiento
from .arriendo import Arriendo
from .operativa import (
    HojaRuta,
    Viaje,
    PersonaTripulacion,
    TripulacionViaje,
    PacienteViaje,
    PacienteTraslado,
    CargaCombustible,
    FallaReportada,
    Alerta,
)

__all__ = [
    "TIPOS_SERVICIO",
    "TURNOS",
    "TIPO_TRASLADO_CATEGORIA",
    "ORIGEN_ALTA",
    "DESTINOS_RED_HOSPITAL",
    "DESTINOS_COMUNES",
    "CODIGOS_DESTINOS_RED",
    "normalizar_estado_oc",
    "normalizar_estado_visual",
    "Usuario",
    "UsuarioManager",
    "Proveedor",
    "CuentaPresupuestaria",
    "Presupuesto",
    "Vehiculo",
    "OrdenTrabajo",
    "OrdenCompra",
    "Mantenimiento",
    "Arriendo",
    "HojaRuta",
    "Viaje",
    "PersonaTripulacion",
    "TripulacionViaje",
    "PacienteViaje",
    "PacienteTraslado",
    "CargaCombustible",
    "FallaReportada",
    "Alerta",
]
