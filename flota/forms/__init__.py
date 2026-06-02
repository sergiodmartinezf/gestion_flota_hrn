"""Formularios del sistema (reexportación compatible con `from flota.forms import ...`)."""

from .auth import LoginForm
from .usuarios import UsuarioForm
from .vehiculos import VehiculoForm
from .proveedores import ProveedorForm
from .viajes import (
    HojaRutaForm,
    ViajeForm,
    PacienteTrasladoForm,
    CargaCombustibleForm,
    PacienteFormSet,
)
from .mantenimiento import (
    MantenimientoForm,
    ProgramarMantenimientoForm,
    FinalizarMantenimientoForm,
)
from .incidentes import FallaReportadaForm
from .presupuesto import PresupuestoForm
from .arriendos import ArriendoForm
from .ordenes import OrdenCompraForm, OrdenTrabajoForm

__all__ = [
    "LoginForm",
    "UsuarioForm",
    "VehiculoForm",
    "ProveedorForm",
    "HojaRutaForm",
    "ViajeForm",
    "PacienteTrasladoForm",
    "CargaCombustibleForm",
    "PacienteFormSet",
    "MantenimientoForm",
    "ProgramarMantenimientoForm",
    "FinalizarMantenimientoForm",
    "FallaReportadaForm",
    "PresupuestoForm",
    "ArriendoForm",
    "OrdenCompraForm",
    "OrdenTrabajoForm",
]
