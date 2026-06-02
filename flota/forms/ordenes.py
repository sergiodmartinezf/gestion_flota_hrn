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

class OrdenCompraForm(forms.ModelForm):
    estado = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Estado exacto de Mercado Público"
    )
    
    class Meta:
        model = OrdenCompra
        fields = [
            'nro_oc', 'descripcion', 'fecha_emision', 'proveedor',
            'monto_neto', 'impuesto', 'monto_total',
            'id_licitacion', 'folio_sigfe', 'estado',
            'archivo_adjunto', 'tipo_adquisicion',
            'cuenta_presupuestaria', 'orden_trabajo', 'vehiculo'
        ]
        widgets = {
            'nro_oc': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'monto_neto': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'id_licitacion': forms.TextInput(attrs={'class': 'form-control'}),
            'folio_sigfe': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo_adquisicion': forms.Select(attrs={'class': 'form-control'}),
            'cuenta_presupuestaria': forms.Select(attrs={'class': 'form-control'}),
            'orden_trabajo': forms.Select(attrs={'class': 'form-control'}),
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'estado': 'Estado exacto de Mercado Público. Se normalizará automáticamente.',
            'vehiculo': 'Vehículo asociado a esta orden de compra (opcional)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Formatear fecha
        if self.instance.pk and self.instance.fecha_emision:
            self.fields['fecha_emision'].widget.attrs['value'] = self.instance.fecha_emision.strftime('%Y-%m-%d')
        
        # Si hay una orden de trabajo seleccionada, auto-completar vehículo y proveedor
        if 'orden_trabajo' in self.data and self.data['orden_trabajo']:
            try:
                ot = OrdenTrabajo.objects.get(pk=self.data['orden_trabajo'])
                self.fields['vehiculo'].initial = ot.vehiculo
                self.fields['proveedor'].initial = ot.proveedor
            except (OrdenTrabajo.DoesNotExist, ValueError):
                pass
        
        # Si no se proporciona estado, establecer uno por defecto
        if not self.instance.pk:
            self.fields['estado'].initial = 'EMITIDA'
    
    def clean_estado(self):
        """Normalizar el estado usando la función del modelo"""
        estado = self.cleaned_data.get('estado')
        from .models import normalizar_estado_oc
        return normalizar_estado_oc(estado)

    def save(self, commit=True):
        orden = super().save(commit=False)
        if commit:
            orden.save()
        return orden
        

class OrdenTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo
        fields = [
            'nro_ot', 'descripcion', 'fecha_solicitud', 'vehiculo',
            'proveedor'
        ]
        widgets = {
            'nro_ot': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'fecha_solicitud': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'nro_ot': 'Número de Orden de Trabajo',
            'descripcion': 'Descripción del trabajo solicitado',
            'fecha_solicitud': 'Fecha de Solicitud',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.fecha_solicitud:
            self.fields['fecha_solicitud'].widget.attrs['value'] = self.instance.fecha_solicitud.strftime('%Y-%m-%d')
        
        # Filtrar proveedores que son talleres
        self.fields['proveedor'].queryset = Proveedor.objects.filter(es_taller=True, activo=True).order_by('nombre_fantasia')
        
        # Filtrar proveedores que son talleres
        self.fields['proveedor'].queryset = Proveedor.objects.filter(es_taller=True, activo=True).order_by('nombre_fantasia')
