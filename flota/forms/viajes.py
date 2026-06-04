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

class HojaRutaForm(forms.ModelForm):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.queryset_para_hoja_ruta(),
        to_field_name='patente',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = HojaRuta
        fields = ['vehiculo', 'fecha', 'turno', 'km_inicio', 'km_fin',
                  'medico_derivador', 'tens', 
                  'enfermero', 'no_aplica_enfermero', 
                  'camillero', 'no_aplica_camillero']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'turno': forms.Select(attrs={'class': 'form-select'}),
            'km_inicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'km_fin': forms.NumberInput(attrs={'class': 'form-control'}),
            'medico_derivador': forms.TextInput(attrs={'class': 'form-control'}),
            'tens': forms.TextInput(attrs={'class': 'form-control'}),
            'enfermero': forms.TextInput(attrs={'class': 'form-control'}),
            'camillero': forms.TextInput(attrs={'class': 'form-control'}),
            'no_aplica_enfermero': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'no_aplica_camillero': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        incluir_pk = self.instance.vehiculo_id if self.instance.pk else None
        self.fields['vehiculo'].queryset = Vehiculo.queryset_para_hoja_ruta(incluir_pk=incluir_pk)

        if not self.data and not self.instance.pk:
            self.fields['fecha'].initial = datetime.now().date()
            self.fields['fecha'].widget.attrs['value'] = datetime.now().date().strftime('%Y-%m-%d')

        # --- Detectar si es camioneta (POST o instancia) ---
        es_camioneta = False
        if self.instance.pk and self.instance.vehiculo:
            es_camioneta = (self.instance.vehiculo.tipo_carroceria == 'Camioneta')
        elif self.data.get('vehiculo'):
            try:
                v = Vehiculo.objects.get(patente=self.data.get('vehiculo'))
                es_camioneta = (v.tipo_carroceria == 'Camioneta')
            except Vehiculo.DoesNotExist:
                pass

        # --- Ajustar required según tipo de vehículo ---
        if es_camioneta:
            self.fields['medico_derivador'].required = False
            self.fields['tens'].required = False
            self.fields['enfermero'].required = False
            self.fields['camillero'].required = False
            # Forzar "No aplica" y limpiar valores
            self.fields['no_aplica_enfermero'].initial = True
            self.fields['no_aplica_camillero'].initial = True
            self.fields['enfermero'].initial = ''
            self.fields['camillero'].initial = ''
        else:
            self.fields['medico_derivador'].required = True
            self.fields['tens'].required = True
            # Enfermero y camillero son condicionales, no se marcan required aquí
            self.fields['enfermero'].required = False
            self.fields['camillero'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        vehiculo = cleaned_data.get('vehiculo')
        turno = cleaned_data.get('turno')
        medico_derivador = cleaned_data.get('medico_derivador')
        tens = cleaned_data.get('tens')
        
        # Obtener valores de checkboxes y textos
        no_aplica_enfermero = cleaned_data.get('no_aplica_enfermero', False)
        enfermero = cleaned_data.get('enfermero')
        
        no_aplica_camillero = cleaned_data.get('no_aplica_camillero', False)
        camillero = cleaned_data.get('camillero')
        
        if not vehiculo:
            return cleaned_data
        
        es_camioneta = vehiculo.tipo_carroceria == 'Camioneta'
        
        if es_camioneta:
            if turno and turno != '08-17':
                self.add_error('turno', 'Las camionetas solo pueden operar en turno administrativo (08:00 a 17:00).')
            # Limpieza automática para camionetas
            cleaned_data['no_aplica_enfermero'] = True
            cleaned_data['no_aplica_camillero'] = True
            cleaned_data['enfermero'] = ''
            cleaned_data['camillero'] = ''
        
        else: # Es Ambulancia
            # 1. Validar Médico y TENS (Siempre obligatorios en ambulancia)
            if not medico_derivador:
                self.add_error('medico_derivador', 'El nombre del Médico es obligatorio.')
            
            if not tens:
                self.add_error('tens', 'El nombre del TENS es obligatorio.')
            
            # 2. Validar Enfermero
            if no_aplica_enfermero:
                # Si marca "No aplica", borramos cualquier texto que haya podido enviar
                cleaned_data['enfermero'] = ''
            else:
                # Si NO marca "No aplica", el texto es OBLIGATORIO
                if not enfermero:
                    self.add_error('enfermero', 'Debe ingresar el nombre del Enfermero/Matrón o marcar "No aplica".')
            
            # 3. Validar Camillero
            if no_aplica_camillero:
                cleaned_data['camillero'] = ''
            else:
                if not camillero:
                    self.add_error('camillero', 'Debe ingresar el nombre del Camillero o marcar "No aplica".')
        
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
        self.vehiculo_tipo = vehiculo_tipo  # Usado por la vista/plantilla (p. ej. camioneta)

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
        fields = ['hora_salida', 'hora_llegada', 'km_salida', 'km_llegada',
                  'hora_salida_hbo', 'hora_llegada_hbo', 'observaciones']
        widgets = {
            'hora_salida': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'km_salida': forms.NumberInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()

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
    extra=0,    # CERO formularios por defecto - el usuario agrega manualmente
    can_delete=True,
    min_num=0,  # Mínimo 0 pacientes
    validate_min=True
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


