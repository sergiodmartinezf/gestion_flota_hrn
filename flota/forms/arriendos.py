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

class ArriendoForm(forms.ModelForm):
    vehiculo_reemplazado = forms.ModelChoiceField(
        queryset=Vehiculo.objects.filter(
            tipo_propiedad='Propio', 
            estado__in=['En mantenimiento', 'Fuera de servicio']
        ).order_by('patente'),
        required=False,
        label="Vehículo propio a reemplazar",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Arriendo
        fields = [
            'vehiculo_arrendado',
            'vehiculo_reemplazado',
            'proveedor',
            'fecha_inicio',
            'fecha_fin',
            'costo_diario',
            'motivo',
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vehiculo_arrendado': forms.Select(attrs={'class': 'form-select'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'costo_diario': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, modo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['motivo'].required = True
        self.fields['costo_diario'].required = True
        self.fields['vehiculo_arrendado'].queryset = Vehiculo.objects.filter(
            tipo_propiedad='Arrendado'
        ).order_by('patente')
        proveedor_qs = Proveedor.objects.filter(es_arrendador=True, activo=True)
        if self.instance.pk and self.instance.proveedor_id:
            proveedor_qs = (
                proveedor_qs | Proveedor.objects.filter(pk=self.instance.proveedor_id)
            ).distinct()
        self.fields['proveedor'].queryset = proveedor_qs.order_by('nombre_fantasia')

        reemplazado_qs = Vehiculo.objects.filter(
            tipo_propiedad='Propio',
            estado__in=['En mantenimiento', 'Fuera de servicio']
        )
        if self.instance.pk and self.instance.vehiculo_reemplazado_id:
            reemplazado_qs = (
                reemplazado_qs | Vehiculo.objects.filter(pk=self.instance.vehiculo_reemplazado_id)
            ).distinct()
        self.fields['vehiculo_reemplazado'].queryset = reemplazado_qs.order_by('patente')

        self.fields['fecha_inicio'].input_formats = ['%Y-%m-%d']
        self.fields['fecha_fin'].input_formats = ['%Y-%m-%d']

        # Formatear fechas para input type="date" (YYYY-MM-DD)
        if self.instance.pk:
            if self.instance.fecha_inicio:
                fecha_inicio_str = self.instance.fecha_inicio.strftime('%Y-%m-%d')
                self.fields['fecha_inicio'].initial = fecha_inicio_str
                self.fields['fecha_inicio'].widget.attrs['value'] = fecha_inicio_str
                self.fields['fecha_inicio'].widget.attrs['data-initial-value'] = fecha_inicio_str
            if self.instance.fecha_fin:
                fecha_fin_str = self.instance.fecha_fin.strftime('%Y-%m-%d')
                self.fields['fecha_fin'].initial = fecha_fin_str
                self.fields['fecha_fin'].widget.attrs['value'] = fecha_fin_str
                self.fields['fecha_fin'].widget.attrs['data-initial-value'] = fecha_fin_str

        if self.data:
            modo = self.data.get('modo_vehiculo_arriendo', modo)
        if modo != 'existente':
            self.fields['vehiculo_arrendado'].required = False

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error('fecha_fin', "La fecha de fin no puede ser anterior a la fecha de inicio.")
        return cleaned_data

    def clean_costo_diario(self):
        costo = self.cleaned_data.get('costo_diario')
        if costo is not None and costo <= 0:
            raise forms.ValidationError('El costo diario debe ser mayor a cero.')
        return costo

    def clean_vehiculo_reemplazado(self):
        vehiculo = self.cleaned_data.get('vehiculo_reemplazado')
        if not vehiculo:
            raise forms.ValidationError('Debe seleccionar un vehículo propio a reemplazar.')
        return vehiculo

    def clean_motivo(self):
        motivo = self.cleaned_data.get('motivo')
        if motivo is None or motivo.strip() == '':
            raise forms.ValidationError('El motivo es obligatorio y no puede estar vacío.')
        return motivo.strip()


class ArriendoFechaFinForm(forms.Form):
    fecha_fin = forms.DateField(
        required=False,
        label='Fecha fin',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )

    def __init__(self, *args, arriendo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.arriendo = arriendo
        if arriendo and arriendo.fecha_fin:
            self.fields['fecha_fin'].widget.attrs['value'] = arriendo.fecha_fin.strftime('%Y-%m-%d')

    def clean_fecha_fin(self):
        fecha_fin = self.cleaned_data.get('fecha_fin')
        if fecha_fin and self.arriendo and self.arriendo.fecha_inicio and fecha_fin < self.arriendo.fecha_inicio:
            raise forms.ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')
        return fecha_fin

