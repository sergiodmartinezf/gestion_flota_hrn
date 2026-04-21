import re
from django import forms
from django.forms import formset_factory, inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from datetime import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import (
    Usuario, Vehiculo, Proveedor, OrdenCompra, OrdenTrabajo,
    Presupuesto, Arriendo, HojaRuta, Viaje, PacienteTraslado, CargaCombustible,
    Mantenimiento, FallaReportada, CuentaPresupuestaria, TIPOS_SERVICIO
)
from .constants import MANTENIMIENTO_CUENTAS_MAP

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


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 8 caracteres, mayúscula, minúscula, número y símbolo'}),
        required=True,
        help_text='Requisitos: 8+ caracteres, al menos 1 mayúscula, 1 minúscula, 1 número y 1 símbolo especial'
    )
    password_confirm = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = Usuario
        fields = ['rut', 'nombre', 'apellido', 'email', 'rol', 'activo']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12345678-9'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es una edición (instance existe), hacer password no obligatorio
        if self.instance.pk:
            self.fields['password'].required = False
            self.fields['password_confirm'].required = False
            self.fields['password'].help_text = 'Dejar en blanco para mantener la contraseña actual'
            # El RUT NO es readonly porque ya no es PK, pero lo mantenemos readonly visualmente
            # El valor se preservará mediante initial y clean_rut()
            self.fields['rut'].widget.attrs['readonly'] = True
            # Establecer el valor inicial para que se envíe en POST
            self.fields['rut'].initial = self.instance.rut
        else:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True
    
    def clean_rut(self):
        """Asegurar que el RUT no cambie en ediciones"""
        rut = self.cleaned_data.get('rut')
        # Si el campo está readonly, puede venir vacío en POST, usar el valor de la instancia
        if not rut and self.instance.pk:
            rut = self.instance.rut
        # Si se intenta cambiar el RUT en una edición, mantener el original
        if self.instance.pk and rut and self.instance.rut != rut:
            return self.instance.rut
        return rut
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            if password.strip() == '':
                raise forms.ValidationError('La contraseña no puede estar compuesta solo por espacios.')
        
        # Solo validar si se proporcionó una contraseña (en creación o cambio)
        if password:
            # Validar longitud mínima
            if len(password) < 8:
                raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
            
            # Validar al menos una mayúscula
            if not re.search(r'[A-Z]', password):
                raise forms.ValidationError('La contraseña debe contener al menos una letra mayúscula.')
            
            # Validar al menos una minúscula
            if not re.search(r'[a-z]', password):
                raise forms.ValidationError('La contraseña debe contener al menos una letra minúscula.')
            
            # Validar al menos un número
            if not re.search(r'[0-9]', password):
                raise forms.ValidationError('La contraseña debe contener al menos un número.')
            
            # Validar al menos un símbolo especial
            if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
                raise forms.ValidationError('La contraseña debe contener al menos un símbolo especial.')
        
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        # Solo validar si estamos creando usuario Y no hay error previo en password
        if not self.instance.pk:
            # Si el campo password tiene errores, no lanzamos el mensaje global
            if self.errors.get('password'):
                return cleaned_data
            if not password:
                raise forms.ValidationError('Debe ingresar una contraseña.')
            if password != password_confirm:
                raise forms.ValidationError('Las contraseñas no coinciden.')
        else:
            # Edición: solo validar si se ingresó alguna contraseña
            if password or password_confirm:
                if password != password_confirm:
                    raise forms.ValidationError('Las contraseñas no coinciden.')
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        # Si se proporcionó una nueva contraseña, establecerla
        if password:
            user.set_password(password)
        elif not user.pk:
            # Si es nuevo usuario sin contraseña, usar rut como contraseña temporal
            user.set_password(self.cleaned_data['rut'])
        
        if commit:
            user.save()
        return user


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


class HojaRutaForm(forms.ModelForm):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objetos_operativos(),  # ← Cambio aquí
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

        # --- Fecha por defecto (SIEMPRE) ---
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
        if vehiculo_tipo == 'Camioneta':
            # Limitar categorías de traslado
            self.fields['categoria_traslado'].choices = [('Administrativo', 'Administrativo')]
            self.fields['categoria_traslado'].initial = 'Administrativo'
            self.fields['categoria_traslado'].disabled = True
            # Ocultar el campo detalle_origen_alta (no aplica)
            self.fields['detalle_origen_alta'].widget = forms.HiddenInput()
            self.fields['detalle_origen_alta'].required = False
            
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
                  'categoria_traslado', 'detalle_origen_alta', 
                  'hora_salida_hbo', 'hora_llegada_hbo', 'observaciones']
        widgets = {
            'hora_salida': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'km_salida': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria_traslado': forms.Select(attrs={'class': 'form-select'}),
            'detalle_origen_alta': forms.Select(attrs={'class': 'form-select'}), # Se muestra/oculta con JS
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
    class Meta:
        model = PacienteTraslado
        fields = ['nombre', 'rut', 'destino_tipo', 'direccion_especifica', 'prevision']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Paciente/Pasajero'}),
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RUT'}),
            'destino_tipo': forms.Select(attrs={'class': 'form-select destino-selector'}), # Clase para JS
            'direccion_especifica': forms.TextInput(attrs={'class': 'form-control direccion-input', 'placeholder': 'Especifique dirección'}),
            'prevision': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tipo Servicio/Prev.'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        destino = cleaned_data.get('destino_tipo')
        # Si el formulario no está marcado para eliminar, el nombre es obligatorio
        if not self.cleaned_data.get('DELETE', False):
            if not nombre or not nombre.strip():
                self.add_error('nombre', 'El nombre del paciente/pasajero es obligatorio.')
            if not destino:
                self.add_error('destino_tipo', 'Debe seleccionar un destino.')
        return cleaned_data

# Factory para gestionar multiples pacientes dentro del mismo formulario de Viaje
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

        # REQ: Filtrar vehículos que no esten en mantenimiento ni de baja
        self.fields['patente_vehiculo'].queryset = Vehiculo.objetos_operativos().order_by('patente')

        # Auto-seleccionar conductor actual
        if not self.instance.pk:
            self.fields['conductor'].initial = self.initial.get('conductor')


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
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_salida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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
        
        # Validar presupuesto si se está creando un nuevo mantenimiento
        if not self.instance.pk and vehiculo and cuenta_presupuestaria and fecha_ingreso:
            anio = fecha_ingreso.year
            
            # Buscar presupuesto específico del vehículo
            presupuesto = Presupuesto.objects.filter(
                cuenta=cuenta_presupuestaria,
                anio=anio,
                activo=True
            ).first()
            
            # Si no hay específico, buscar global
            if not presupuesto:
                presupuesto = Presupuesto.objects.filter(
                    cuenta=cuenta_presupuestaria,
                    anio=anio,
                    activo=True
                ).first()
            
            if not presupuesto:
                raise forms.ValidationError(
                    f"No hay presupuesto asignado para la cuenta {cuenta_presupuestaria.codigo} "
                    f"en el año {anio}. Debe crear un presupuesto antes de registrar mantenimientos."
                )
            
            # Verificar costo estimado contra presupuesto disponible
            monto_a_validar = costo_total_real if costo_total_real > 0 else costo_estimado
            
            if monto_a_validar > 0 and presupuesto.disponible < monto_a_validar:
                raise forms.ValidationError(
                    f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                    f"Requerido: ${monto_a_validar:.0f}"
                )
        
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
            cuentas_permitidas = MANTENIMIENTO_CUENTAS_MAP.get((tipo, criticidad), [])
            if cuenta_presupuestaria.id not in cuentas_permitidas:
                raise forms.ValidationError(
                    f"La cuenta {cuenta_presupuestaria.codigo} no corresponde a un mantenimiento {tipo} "
                    f"para un vehículo {criticidad.lower()}."
                )
        return cleaned_data
        
        # Validar presupuesto
        if vehiculo and cuenta_presupuestaria and fecha_ingreso:
            anio = fecha_ingreso.year
            
            # Buscar presupuesto
            presupuesto = Presupuesto.objects.filter(
                cuenta=cuenta_presupuestaria,
                anio=anio,
                activo=True
            ).first()
            
            if not presupuesto:
                presupuesto = Presupuesto.objects.filter(
                    cuenta=cuenta_presupuestaria,
                    anio=anio,
                    activo=True
                ).first()
            
            if not presupuesto:
                raise forms.ValidationError(
                    f"No hay presupuesto asignado para la cuenta {cuenta_presupuestaria.codigo} "
                    f"en el año {anio}. Debe crear un presupuesto antes de programar mantenimientos."
                )
            
            # Verificar costo estimado contra presupuesto disponible
            if costo_estimado > 0 and presupuesto.disponible < costo_estimado:
                raise forms.ValidationError(
                    f"Presupuesto insuficiente. Disponible: ${presupuesto.disponible:.0f}, "
                    f"Requerido: ${costo_estimado:.0f}"
                )
        
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


class FallaReportadaForm(forms.ModelForm):
    class Meta:
        model = FallaReportada
        fields = ['vehiculo', 'fecha_reporte', 'descripcion', 'nivel_urgencia']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'fecha_reporte': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'nivel_urgencia': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['nivel_urgencia'].initial = 'Media'
        if self.instance.pk and self.instance.fecha_reporte:
            self.fields['fecha_reporte'].widget.attrs['value'] = self.instance.fecha_reporte.strftime('%Y-%m-%d')

        # REQ: Filtrar vehículos activos para reportar fallas nuevas
        if not self.instance.pk:
            self.fields['vehiculo'].queryset = Vehiculo.objetos_operativos().order_by('patente')


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
                tipo = f"para {vehiculo.patente}" if vehiculo else "global"
                raise forms.ValidationError(
                    f'Ya existe un presupuesto para el año {anio}, cuenta {cuenta} {tipo}.'
                )
        
        # Validar año razonable
        if anio:
            current_year = datetime.now().year
            if anio < 2000 or anio > current_year + 10:
                raise forms.ValidationError('Por favor ingrese un año válido (2000-2030).')
        
        return cleaned_data


class ArriendoForm(forms.ModelForm):
    # Definir explícitamente vehiculo_reemplazado como ModelChoiceField
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
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vehiculo_arrendado': forms.Select(attrs={'class': 'form-select'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'costo_diario': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['motivo'].required = True
        self.fields['costo_diario'].required = True
        self.fields['vehiculo_arrendado'].queryset = Vehiculo.objects.filter(
            tipo_propiedad='Arrendado'
        ).order_by('patente')
        self.fields['proveedor'].queryset = Proveedor.objects.filter(
            es_arrendador=True, activo=True
        ).order_by('nombre_fantasia')
        # Nota: vehiculo_reemplazado ya tiene queryset fijo, no se modifica aquí

        # Formatear fechas si es edición
        if self.instance.pk:
            if self.instance.fecha_inicio:
                self.fields['fecha_inicio'].widget.attrs['value'] = self.instance.fecha_inicio.strftime('%Y-%m-%d')
            if self.instance.fecha_fin:
                self.fields['fecha_fin'].widget.attrs['value'] = self.instance.fecha_fin.strftime('%Y-%m-%d')

        # Hacer vehiculo_arrendado opcional si es modo nuevo
        modo = self.data.get('modo_vehiculo_arriendo') if self.data else None
        if modo == 'nuevo':
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
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),  # Nuevo
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'monto_neto': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'id_licitacion': forms.TextInput(attrs={'class': 'form-control'}),
            'folio_sigfe': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),  # Ahora sí en widgets
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo_adquisicion': forms.Select(attrs={'class': 'form-control'}),  # Nuevo
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
