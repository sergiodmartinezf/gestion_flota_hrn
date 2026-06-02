from functools import wraps

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from ..services.presupuesto import (
    mensaje_presupuesto_disponible,
    validar_presupuesto_disponible,
)


def es_administrador(user):
    return user.is_authenticated and user.rol == 'Administrador'


def es_conductor(user):
    return user.is_authenticated and user.rol == 'Conductor'


def es_visualizador(user):
    return user.is_authenticated and user.rol == 'Visualizador'


def es_conductor_o_admin(user):
    return user.is_authenticated and user.rol in ('Administrador', 'Conductor')


def puede_escribir(user):
    """Administrador y Conductor pueden modificar datos; Visualizador solo lectura."""
    return user.is_authenticated and user.rol in ('Administrador', 'Conductor')


def verificar_presupuesto_cuenta(cuenta, anio, monto_requerido=0):
    """Verifica presupuesto disponible (compatibilidad con vistas y API)."""
    ok, mensaje, presupuesto = validar_presupuesto_disponible(cuenta, anio, monto_requerido)
    if not ok:
        return False, mensaje, presupuesto
    return True, mensaje_presupuesto_disponible(presupuesto), presupuesto


def rechazar_escritura_visualizador(view_func):
    """Bloquea POST/PUT/PATCH/DELETE para usuarios con rol Visualizador."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if (
            request.method not in ('GET', 'HEAD', 'OPTIONS')
            and es_visualizador(request.user)
        ):
            messages.error(request, 'Su rol no permite realizar modificaciones en el sistema.')
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return HttpResponseForbidden('Acceso de solo lectura.')
        return view_func(request, *args, **kwargs)
    return _wrapped
