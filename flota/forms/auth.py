import re
from django import forms
from django.forms import formset_factory, inlineformset_factory
from datetime import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import (
    Usuario, Vehiculo, Proveedor, OrdenCompra, OrdenTrabajo,
    Presupuesto, Arriendo, HojaRuta, Viaje, PacienteTraslado, CargaCombustible,
    Mantenimiento, FallaReportada, CuentaPresupuestaria, TIPOS_SERVICIO,
)
from ..constants import cuenta_valida_para_mantenimiento
from ..services.presupuesto import validar_presupuesto_disponible
from ..validators import validar_rut_chileno, normalizar_rut

class LoginForm(forms.Form):
    rut = forms.CharField(
        label='RUT',
        max_length=12,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su RUT'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su contraseña'})
    )

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        es_valido, mensaje = validar_rut_chileno(rut)
        if not es_valido:
            raise forms.ValidationError(mensaje)
        rut_norm = normalizar_rut(rut)
        return rut_norm or rut


