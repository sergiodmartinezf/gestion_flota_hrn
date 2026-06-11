import re
from django import forms
from django.forms import formset_factory, inlineformset_factory
from datetime import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import (
    Usuario, Vehiculo, Proveedor, OrdenCompra, OrdenTrabajo,
    Presupuesto, Arriendo, HojaRuta, Viaje, TripulacionViaje, PacienteTraslado,
    CargaCombustible, Mantenimiento, FallaReportada, CuentaPresupuestaria,
    TIPOS_SERVICIO, ROL_TRIPULACION,
)
from ..constants import cuenta_valida_para_mantenimiento
from ..services.presupuesto import validar_presupuesto_disponible
from ..validators import validar_rut_chileno, normalizar_rut

class HojaRutaForm(forms.ModelForm):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.queryset_para_hoja_ruta(),
        to_field_name='patente',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = HojaRuta
        fields = ['vehiculo', 'fecha', 'turno', 'km_inicio', 'km_fin']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'turno': forms.Select(attrs={'class': 'form-select'}),
            'km_inicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'km_fin': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        incluir_pk = self.instance.vehiculo_id if self.instance.pk else None
        self.fields['vehiculo'].queryset = Vehiculo.queryset_para_hoja_ruta(incluir_pk=incluir_pk)

        self.fields['fecha'].input_formats = ['%Y-%m-%d']
        self.fields['fecha'].widget.format = '%Y-%m-%d'

        if not self.data:
            if self.instance.pk:
                if self.instance.fecha:
                    fecha_str = self.instance.fecha.strftime('%Y-%m-%d')
                    self.fields['fecha'].widget.attrs['value'] = fecha_str
                if self.instance.vehiculo_id:
                    # to_field_name='patente': el valor del select es la patente, no el pk
                    self.initial['vehiculo'] = self.instance.vehiculo.patente
            else:
                self.fields['fecha'].initial = datetime.now().date()
                self.fields['fecha'].widget.attrs['value'] = datetime.now().date().strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()

        vehiculo = cleaned_data.get('vehiculo')
        turno = cleaned_data.get('turno')

        if vehiculo and vehiculo.tipo_carroceria == 'Camioneta':
            if turno and turno != '08-17':
                self.add_error('turno', 'Las camionetas solo pueden operar en turno administrativo (08:00 a 17:00).')

        return cleaned_data

    def clean_km_inicio(self):
        km = self.cleaned_data.get('km_inicio')
        if km is None:
            raise ValidationError('Debe ingresar el kilometraje inicial.')
        if km < 0:
            raise ValidationError('El kilometraje inicial no puede ser negativo.')
        return km


class ViajeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        vehiculo_tipo = kwargs.pop('vehiculo_tipo', None)
        super().__init__(*args, **kwargs)
        self.vehiculo_tipo = vehiculo_tipo
        for name in ('hora_salida_hbo', 'hora_llegada_hbo', 'no_aplica_enfermero', 'no_aplica_camillero'):
            self.fields[name].required = False
            self.fields[name].widget.attrs.pop('required', None)
        self.fields['no_aplica_enfermero'].widget = forms.HiddenInput()
        self.fields['no_aplica_camillero'].widget = forms.HiddenInput()
        if not self.instance.pk and not self.data:
            self.initial['no_aplica_enfermero'] = True
            self.initial['no_aplica_camillero'] = True

    hora_llegada = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        required=True,
        label="Hora de Llegada"
    )
    km_llegada = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        required=False,
        label="KM Llegada"
    )
    hora_salida_hbo = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        required=False,
        label="Hora Salida HBO"
    )
    hora_llegada_hbo = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        required=False,
        label="Hora Llegada HBO"
    )

    class Meta:
        model = Viaje
        fields = [
            'hora_salida', 'hora_llegada', 'km_salida', 'km_llegada',
            'hora_salida_hbo', 'hora_llegada_hbo',
            'no_aplica_enfermero', 'no_aplica_camillero',
            'observaciones',
        ]
        widgets = {
            'hora_salida': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'km_salida': forms.NumberInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'no_aplica_enfermero': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'no_aplica_camillero': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        if self.data:
            lleva_enfermero = self.data.get('lleva_enfermero') == 'on'
            lleva_camillero = self.data.get('lleva_camillero') == 'on'
            cleaned_data['no_aplica_enfermero'] = not lleva_enfermero
            cleaned_data['no_aplica_camillero'] = not lleva_camillero
        elif not self.instance.pk:
            cleaned_data['no_aplica_enfermero'] = True
            cleaned_data['no_aplica_camillero'] = True

        km_salida = cleaned_data.get('km_salida')
        km_llegada = cleaned_data.get('km_llegada')

        if km_llegada is not None and km_salida is not None:
            if km_llegada < km_salida:
                self.add_error('km_llegada', 'El KM de llegada no puede ser menor que el KM de salida.')

        return cleaned_data


class PacienteTrasladoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.vehiculo_tipo = kwargs.pop('vehiculo_tipo', None)
        super().__init__(*args, **kwargs)
        if self.vehiculo_tipo == 'Camioneta':
            self.fields['categoria_traslado'].choices = [('Administrativo', 'Administrativo')]
            self.fields['categoria_traslado'].initial = 'Administrativo'
            self.fields['categoria_traslado'].disabled = True
            self.fields['categoria_traslado'].required = False
            self.fields['detalle_origen_alta'].widget = forms.HiddenInput()
            self.fields['detalle_origen_alta'].required = False
            self.fields['sentido'].widget = forms.HiddenInput()
            self.fields['sentido'].required = False

    class Meta:
        model = PacienteTraslado
        fields = [
            'rut', 'destino_tipo', 'direccion_especifica',
            'categoria_traslado', 'sentido', 'detalle_origen_alta',
        ]
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control paciente-rut', 'placeholder': 'RUT'}),
            'destino_tipo': forms.Select(attrs={'class': 'form-select destino-selector'}),
            'direccion_especifica': forms.TextInput(attrs={'class': 'form-control direccion-input', 'placeholder': 'Especifique dirección'}),
            'categoria_traslado': forms.Select(attrs={'class': 'form-select categoria-traslado-select'}),
            'sentido': forms.Select(attrs={'class': 'form-select sentido-select'}),
            'detalle_origen_alta': forms.Select(attrs={'class': 'form-select detalle-origen-alta-select'}),
        }

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if rut and rut.strip():
            es_valido, mensaje = validar_rut_chileno(rut)
            if not es_valido:
                raise forms.ValidationError(mensaje)
            rut_norm = normalizar_rut(rut)
            if rut_norm:
                return rut_norm
        return rut

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('DELETE'):
            return cleaned_data

        rut = (cleaned_data.get('rut') or '').strip()
        destino = cleaned_data.get('destino_tipo')
        direccion = (cleaned_data.get('direccion_especifica') or '').strip()

        if not rut and not destino and not direccion:
            return cleaned_data

        if self.vehiculo_tipo == 'Camioneta':
            cleaned_data['categoria_traslado'] = 'Administrativo'
            cleaned_data['sentido'] = 'IDA'
            cleaned_data['detalle_origen_alta'] = None
        else:
            categoria = cleaned_data.get('categoria_traslado')
            if categoria == 'ALTA':
                if not cleaned_data.get('detalle_origen_alta'):
                    self.add_error('detalle_origen_alta', 'Debe indicar el origen del alta.')
            else:
                cleaned_data['detalle_origen_alta'] = None

        if not rut:
            self.add_error('rut', 'El RUT es obligatorio.')
        if not destino:
            self.add_error('destino_tipo', 'Debe seleccionar un destino.')

        return cleaned_data

PacienteFormSet = inlineformset_factory(
    Viaje,
    PacienteTraslado,
    form=PacienteTrasladoForm,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=True,
)


class TripulacionViajeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.vehiculo_tipo = kwargs.pop('vehiculo_tipo', None)
        super().__init__(*args, **kwargs)
        self.fields['rol'].widget = forms.HiddenInput()
        self.fields['nombre'].widget.attrs.update({
            'class': 'form-control tripulacion-nombre',
            'placeholder': 'Nombre',
            'maxlength': '100',
        })

    class Meta:
        model = TripulacionViaje
        fields = ['nombre', 'rol']
        widgets = {
            'rol': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('DELETE'):
            return cleaned_data
        nombre = (cleaned_data.get('nombre') or '').strip()
        if not nombre and self.instance.pk:
            nombre = (self.instance.nombre or '').strip()
        cleaned_data['nombre'] = nombre
        return cleaned_data


def _nombre_efectivo_tripulacion(form):
    if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
        return ''
    if form.cleaned_data.get('DELETE'):
        return ''
    return (form.cleaned_data.get('nombre') or '').strip()


class BaseTripulacionFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, vehiculo_tipo=None, no_aplica_enfermero=False,
                 no_aplica_camillero=False, **kwargs):
        self.vehiculo_tipo = vehiculo_tipo
        self.no_aplica_enfermero = no_aplica_enfermero
        self.no_aplica_camillero = no_aplica_camillero
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.vehiculo_tipo == 'Camioneta':
            return

        conteo = {rol[0]: 0 for rol in ROL_TRIPULACION}
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            nombre = _nombre_efectivo_tripulacion(form)
            if not nombre:
                continue
            rol = form.cleaned_data.get('rol')
            if rol in conteo:
                conteo[rol] += 1

        if conteo['MEDICO'] < 1:
            raise ValidationError('Debe ingresar al menos un médico.')
        if conteo['TENS'] < 1:
            raise ValidationError('Debe ingresar al menos un TENS.')
        if not self.no_aplica_enfermero and conteo['ENFERMERO'] < 1:
            raise ValidationError('Debe ingresar al menos un enfermero/matrón si el viaje lo incluye.')
        if not self.no_aplica_camillero and conteo['CAMILLERO'] < 1:
            raise ValidationError('Debe ingresar al menos un camillero si el viaje lo incluye.')


TripulacionFormSet = inlineformset_factory(
    Viaje,
    TripulacionViaje,
    form=TripulacionViajeForm,
    formset=BaseTripulacionFormSet,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=True,
)


class CargaCombustibleForm(forms.ModelForm):
    class Meta:
        model = CargaCombustible
        fields = [
            'fecha', 'patente_vehiculo', 'kilometraje_al_cargar',
            'litros', 'precio_unitario', 'costo_total', 'nro_boleta',
            'conductor', 'cuenta_presupuestaria'
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'patente_vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'kilometraje_al_cargar': forms.NumberInput(attrs={'class': 'form-control'}),
            'litros': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1'}),
            'nro_boleta': forms.TextInput(attrs={'class': 'form-control'}),
            'conductor': forms.Select(attrs={'class': 'form-control'}),
            'cuenta_presupuestaria': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.fecha:
            self.fields['fecha'].widget.attrs['value'] = self.instance.fecha.strftime('%Y-%m-%d')

        self.fields['patente_vehiculo'].queryset = Vehiculo.objetos_operativos().order_by('patente')

        # Auto-seleccionar conductor actual
        if not self.instance.pk:
            self.fields['conductor'].initial = self.initial.get('conductor')


