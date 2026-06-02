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

class MantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = [
            'vehiculo', 'tipo_mantencion', 'fecha_ingreso', 'fecha_salida',
            'km_al_ingreso', 'descripcion_trabajo', 'estado',
            'costo_estimado', 'costo_mano_obra', 'costo_repuestos',
            'proveedor', 'orden_trabajo', 'cuenta_presupuestaria'
        ]
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'tipo_mantencion': forms.Select(attrs={'class': 'form-control'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_salida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'km_al_ingreso': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion_trabajo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'costo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'costo_mano_obra': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'costo_repuestos': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'orden_trabajo': forms.Select(attrs={'class': 'form-control'}),
            'cuenta_presupuestaria': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si es un nuevo mantenimiento, verificar presupuesto
        if not self.instance.pk:
            # Mostrar advertencia si no hay presupuesto
            self.fields['vehiculo'].widget.attrs['onchange'] = 'verificarPresupuesto(this.value)'
            self.fields['cuenta_presupuestaria'].widget.attrs['onchange'] = 'verificarPresupuesto()'

        # Formatear fechas para input type="date" (YYYY-MM-DD)
        if self.instance.pk:
            if self.instance.fecha_ingreso:
                fecha_ingreso_str = self.instance.fecha_ingreso.strftime('%Y-%m-%d')
                self.fields['fecha_ingreso'].initial = fecha_ingreso_str
                self.fields['fecha_ingreso'].widget.attrs['value'] = fecha_ingreso_str
                self.fields['fecha_ingreso'].widget.attrs['data-initial-value'] = fecha_ingreso_str
            if self.instance.fecha_salida:
                fecha_salida_str = self.instance.fecha_salida.strftime('%Y-%m-%d')
                self.fields['fecha_salida'].initial = fecha_salida_str
                self.fields['fecha_salida'].widget.attrs['value'] = fecha_salida_str
                self.fields['fecha_salida'].widget.attrs['data-initial-value'] = fecha_salida_str
            
            # Filtrar órdenes de trabajo por vehículo (si ya tiene vehículo asignado)
            if self.instance.vehiculo:
                self.fields['orden_trabajo'].queryset = OrdenTrabajo.objects.filter(
                    vehiculo=self.instance.vehiculo
                )
        
        # Configurar el queryset para orden_trabajo en general
        if 'vehiculo' in self.fields:
            # Si se cambia el vehículo en el formulario, actualizar dinámicamente
            self.fields['orden_trabajo'].queryset = OrdenTrabajo.objects.none()
            
            # Agregar validación personalizada
            if 'vehiculo' in self.data:
                try:
                    vehiculo_id = self.data.get('vehiculo')
                    if vehiculo_id:
                        self.fields['orden_trabajo'].queryset = OrdenTrabajo.objects.filter(
                            vehiculo_id=vehiculo_id
                        )
                except (ValueError, TypeError):
                    pass

    def clean(self):
        cleaned_data = super().clean()
        vehiculo = cleaned_data.get('vehiculo')
        cuenta_presupuestaria = cleaned_data.get('cuenta_presupuestaria')
        fecha_ingreso = cleaned_data.get('fecha_ingreso')
        costo_estimado = cleaned_data.get('costo_estimado', 0)
        costo_total_real = cleaned_data.get('costo_total_real', 0)
        
        # Validar que o bien se seleccione un vehículo arrendado existente, o se proporcione uno nuevo
        vehiculo = cleaned_data.get('vehiculo')
        orden_trabajo = cleaned_data.get('orden_trabajo')
        
        if orden_trabajo and vehiculo and orden_trabajo.vehiculo != vehiculo:
            raise forms.ValidationError(
                f'La Orden de Trabajo {orden_trabajo.nro_ot} corresponde al vehículo '
                f'{orden_trabajo.vehiculo.patente}, no a {vehiculo.patente}.'
            )
        
        if not self.instance.pk and vehiculo and cuenta_presupuestaria and fecha_ingreso:
            monto_a_validar = costo_total_real if costo_total_real > 0 else costo_estimado
            ok, mensaje, _ = validar_presupuesto_disponible(
                cuenta_presupuestaria, fecha_ingreso.year, monto_a_validar
            )
            if not ok:
                raise forms.ValidationError(mensaje)
        
        return cleaned_data


class ProgramarMantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = [
            'vehiculo', 'fecha_ingreso', 'fecha_programada', 'km_al_ingreso', 
            'proveedor', 'orden_trabajo', 'descripcion_trabajo', 
            'costo_estimado', 'cuenta_presupuestaria'
        ]
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_programada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'km_al_ingreso': forms.NumberInput(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'orden_trabajo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion_trabajo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'costo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'cuenta_presupuestaria': forms.Select(attrs={'class': 'form-control'}),
        }

    # Costo estimado y fecha_programada son opcionales
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['costo_estimado'].required = False
        self.fields['fecha_programada'].required = False
        self.fields['fecha_programada'].help_text = "Fecha en que se programó realizar el mantenimiento (para alertas por tiempo)"
        # Formatear fechas para input type="date"
        if self.instance.pk:
            if self.instance.fecha_ingreso:
                self.fields['fecha_ingreso'].widget.attrs['value'] = self.instance.fecha_ingreso.strftime('%Y-%m-%d')
            if self.instance.fecha_programada:
                self.fields['fecha_programada'].widget.attrs['value'] = self.instance.fecha_programada.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_mantencion')
        vehiculo = cleaned_data.get('vehiculo')
        cuenta_presupuestaria = cleaned_data.get('cuenta_presupuestaria')
        fecha_ingreso = cleaned_data.get('fecha_ingreso')
        costo_estimado = cleaned_data.get('costo_estimado', 0)

        # Para filtro dinámico de opciones de cuentas
        if tipo and vehiculo and cuenta_presupuestaria:
            criticidad = vehiculo.criticidad   # 'Crítico' o 'No crítico'
            if not cuenta_valida_para_mantenimiento(cuenta_presupuestaria, tipo, criticidad):
                raise forms.ValidationError(
                    f"La cuenta {cuenta_presupuestaria.codigo} no corresponde a un mantenimiento {tipo} "
                    f"para un vehículo {criticidad.lower()}."
                )

        if vehiculo and cuenta_presupuestaria and fecha_ingreso:
            ok, mensaje, _ = validar_presupuesto_disponible(
                cuenta_presupuestaria, fecha_ingreso.year, costo_estimado
            )
            if not ok:
                raise forms.ValidationError(mensaje)

        return cleaned_data

    def clean_costo_estimado(self):
        costo = self.cleaned_data.get('costo_estimado')
        if costo is not None and costo < 0:
            raise forms.ValidationError('El costo estimado no puede ser negativo.')
        return costo

class FinalizarMantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = [
            'fecha_salida', 
            'descripcion_trabajo',
            'costo_mano_obra', 
            'costo_repuestos',
            'orden_compra', # Si se generó durante el proceso
            'nro_factura',
            'archivo_adjunto' # Si quieres subir la factura escaneada
        ]
        widgets = {
            'fecha_salida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion_trabajo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'costo_mano_obra': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'costo_repuestos': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'orden_compra': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Orden de Compra obligatoria para cierre administrativo (normativa hospitalaria)
        self.fields['orden_compra'].required = True
        self.fields['orden_compra'].help_text = 'Obligatorio para cerrar el mantenimiento.'
        # Formatear fecha_salida para input type="date"
        if self.instance.pk and self.instance.fecha_salida:
            self.fields['fecha_salida'].widget.attrs['value'] = self.instance.fecha_salida.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        mano_obra = cleaned_data.get('costo_mano_obra') or 0
        repuestos = cleaned_data.get('costo_repuestos') or 0
        orden_compra = cleaned_data.get('orden_compra') or self.instance.orden_compra_id
        
        if mano_obra + repuestos <= 0:
            raise forms.ValidationError("Debe ingresar los costos reales para finalizar el mantenimiento.")
        if not orden_compra:
            raise forms.ValidationError(
                "No se puede finalizar el mantenimiento sin Orden de Compra asociada. "
                "Seleccione la OC correspondiente."
            )
        return cleaned_data


