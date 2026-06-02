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

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            'rut_empresa', 'nombre_fantasia', 'telefono', 
            'email_contacto', 'es_taller', 'es_arrendador', 'activo'
        ]
        widgets = {
            'rut_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email_contacto': forms.EmailInput(attrs={'class': 'form-control'}),
            'es_taller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_arrendador': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_rut_empresa(self):
        rut = self.cleaned_data.get('rut_empresa')
        if rut:
            es_valido, mensaje = validar_rut_chileno(rut)
            if not es_valido:
                raise forms.ValidationError(mensaje)
            rut_norm = normalizar_rut(rut)
            if rut_norm:
                return rut_norm
        return rut


