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

class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['anio', 'cuenta', 'monto_asignado', 'activo']
        widgets = {
            'anio': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'monto_asignado': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'anio': 'Año Presupuestario',
            'cuenta': 'Cuenta SIGFE',
            'monto_asignado': 'Monto Asignado',
        }
        help_texts = {
            'anio': 'Ej: 2024',
            'monto_asignado': 'Monto en pesos chilenos',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar cuentas por código
        self.fields['cuenta'].queryset = CuentaPresupuestaria.objects.all().order_by('codigo')
        if self.instance.pk and self.instance.monto_ejecutado > 0:
            self.fields['anio'].disabled = True
        # Año actual por defecto
        if not self.instance.pk:  # Solo para creación, no edición
            self.fields['anio'].initial = datetime.now().year
            # Ocultar campo activo en creación (será True por defecto)
            if 'activo' in self.fields:
                del self.fields['activo']
    
    def clean(self):
        cleaned_data = super().clean()
        anio = cleaned_data.get('anio')
        cuenta = cleaned_data.get('cuenta')
        
        # Validar combinación única
        if anio and cuenta:
            existing = Presupuesto.objects.filter(
                anio=anio,
                cuenta=cuenta
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError(
                    f'Ya existe un presupuesto para el año {anio} y la cuenta {cuenta}.'
                )
        
        # Validar año razonable
        if anio:
            current_year = datetime.now().year
            if anio < 2000 or anio > current_year + 10:
                raise forms.ValidationError('Por favor ingrese un año válido (2000-2030).')
        
        return cleaned_data

    def clean_anio(self):
        anio = self.cleaned_data.get('anio')
        if self.instance.pk and self.instance.monto_ejecutado > 0:
            return self.instance.anio
        return anio


