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

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = [
            'patente', 'marca', 'modelo', 'vin', 'nro_motor', 
            'anio_adquisicion', 'vida_util',
            'kilometraje_actual', 'umbral_mantencion', 'tipo_carroceria',
            'clase_ambulancia', 'es_samu', 'establecimiento', 'criticidad',
            'es_backup', 'estado'
        ]
        widgets = {
            'patente': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'vin': forms.TextInput(attrs={'class': 'form-control'}),
            'nro_motor': forms.TextInput(attrs={'class': 'form-control'}),
            'anio_adquisicion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1900, 'max': 2100}),
            'vida_util': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'umbral_mantencion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'kilometraje_actual': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'tipo_carroceria': forms.Select(attrs={'class': 'form-control'}),
            'clase_ambulancia': forms.Select(attrs={'class': 'form-control'}),
            'es_samu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'establecimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'criticidad': forms.Select(attrs={'class': 'form-control'}),
            'es_backup': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['patente'].widget.attrs['readonly'] = True  # Mantener readonly visual
            # Establecer el valor inicial para que se envíe en POST
            self.fields['patente'].initial = self.instance.patente
        required_fields = [
            'patente', 
            'marca', 
            'modelo', 
            'anio_adquisicion', 
            'kilometraje_actual', 
            'umbral_mantencion', 
            'tipo_carroceria', 
            'establecimiento', 
            'criticidad', 
            'estado'
        ]
        for field_name in required_fields:
            self.fields[field_name].required = True
        self.fields['es_samu'].required = False
        self.fields['es_backup'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_carroceria = cleaned_data.get('tipo_carroceria')
        clase_ambulancia = cleaned_data.get('clase_ambulancia')

        # Solo permitir clase de ambulancia cuando el tipo de carrocería es Ambulancia
        if tipo_carroceria != 'Ambulancia':
            cleaned_data['clase_ambulancia'] = None

        return cleaned_data

    def clean_anio_adquisicion(self):
        value = self.cleaned_data.get('anio_adquisicion')
        if value is not None:
            if value <= 0:
                raise forms.ValidationError('El año de adquisición debe ser un número positivo.')
            current_year = timezone.now().year
            if value < 1900 or value > current_year + 1:
                raise forms.ValidationError(f'Ingrese un año válido (1900-{current_year+1}).')
        return value

    def clean_vida_util(self):
        value = self.cleaned_data.get('vida_util')
        if value is not None and value <= 0:
            raise forms.ValidationError('La vida útil debe ser mayor a cero.')
        return value

    def clean_umbral_mantencion(self):
        value = self.cleaned_data.get('umbral_mantencion')
        if value is not None and value <= 0:
            raise forms.ValidationError('El umbral de mantención debe ser mayor a cero.')
        return value

    def clean_kilometraje_actual(self):
        value = self.cleaned_data.get('kilometraje_actual')
        if value is not None and value < 0:
            raise forms.ValidationError('El kilometraje actual no puede ser negativo.')
        return value

    def clean_patente(self):
        patente = self.cleaned_data.get('patente')
        if not patente or patente.strip() == '':
            raise forms.ValidationError('La patente es obligatoria.')
        # Normalizar: mayúsculas y sin espacios
        return patente.strip().upper()

    def clean_marca(self):
        marca = self.cleaned_data.get('marca')
        if not marca or marca.strip() == '':
            raise forms.ValidationError('La marca es obligatoria.')
        return marca.strip()

    def clean_modelo(self):
        modelo = self.cleaned_data.get('modelo')
        if not modelo or modelo.strip() == '':
            raise forms.ValidationError('El modelo es obligatorio.')
        return modelo.strip()

    def clean_establecimiento(self):
        establecimiento = self.cleaned_data.get('establecimiento')
        if not establecimiento or establecimiento.strip() == '':
            raise forms.ValidationError('El establecimiento es obligatorio.')
        return establecimiento.strip()


