from django import forms
from django.contrib.auth.forms import UserCreationForm
from datetime import datetime
from .models import (
    Usuario, Vehiculo, Proveedor, OrdenCompra, OrdenTrabajo,
    Presupuesto, Arriendo, HojaRuta, Viaje, CargaCombustible,
    Mantenimiento, FallaReportada, CuentaPresupuestaria
)


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
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
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
        # Si es una edición (instance existe), hacer password no obligatorio y RUT readonly
        if self.instance.pk:
            self.fields['password'].required = False
            self.fields['password_confirm'].required = False
            # El RUT es la primary key, no debe ser editable (usar readonly en lugar de disabled para que se envíe en POST)
            self.fields['rut'].widget.attrs['readonly'] = True
        else:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        # Solo validar contraseñas si estamos creando o cambiando contraseña
        if self.instance.pk:
            # Edición: si se ingresó contraseña, validar
            if password or password_confirm:
                if password != password_confirm:
                    raise forms.ValidationError('Las contraseñas no coinciden.')
        else:
            # Creación: contraseñas son obligatorias
            if not password:
                raise forms.ValidationError('Debe ingresar una contraseña.')
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
            'es_backup', 'estado', 'tipo_propiedad'
        ]
        widgets = {
            'patente': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'vin': forms.TextInput(attrs={'class': 'form-control'}),
            'nro_motor': forms.TextInput(attrs={'class': 'form-control'}),
            'anio_adquisicion': forms.NumberInput(attrs={'class': 'form-control'}),
            'vida_util': forms.NumberInput(attrs={'class': 'form-control'}),
            'kilometraje_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'umbral_mantencion': forms.NumberInput(attrs={'class': 'form-control'}),
            'tipo_carroceria': forms.Select(attrs={'class': 'form-control'}),
            'clase_ambulancia': forms.Select(attrs={'class': 'form-control'}),
            'es_samu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'establecimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'criticidad': forms.Select(attrs={'class': 'form-control'}),
            'es_backup': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'tipo_propiedad': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es una edición, hacer patente readonly (es la primary key)
        if self.instance.pk:
            self.fields['patente'].widget.attrs['readonly'] = True


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            'rut_empresa', 'nombre_fantasia', 'giro', 'telefono', 
            'email_contacto', 'es_taller', 'es_arrendador', 'activo'
        ]
        widgets = {
            'rut_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'giro': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email_contacto': forms.EmailInput(attrs={'class': 'form-control'}),
            'es_taller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_arrendador': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class HojaRutaForm(forms.ModelForm):
    class Meta:
        model = HojaRuta
        fields = ['fecha', 'turno', 'vehiculo', 'km_inicio', 'km_fin', 
                  'litros_inicio', 'litros_fin', 'observaciones']
        
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'turno': forms.Select(attrs={'class': 'form-control'}),
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'km_inicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'km_fin': forms.NumberInput(attrs={'class': 'form-control'}),
            'litros_inicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'litros_fin': forms.NumberInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.fecha:
            self.fields['fecha'].widget.attrs['value'] = self.instance.fecha.strftime('%Y-%m-%d')

class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = [
            'hora_salida', 'hora_llegada', 'destino', 'rut_paciente', 
            'nombre_paciente', 'tipo_servicio', 'km_recorridos_viaje'
        ]
        widgets = {
            'hora_salida': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_llegada': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'rut_paciente': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_paciente': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_servicio': forms.Select(attrs={'class': 'form-control'}),
            'km_recorridos_viaje': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CargaCombustibleForm(forms.ModelForm):
    class Meta:
        model = CargaCombustible
        fields = [
            'fecha', 'patente_vehiculo', 'kilometraje_al_cargar', 
            'litros', 'precio_unitario', 'costo_total', 'nro_boleta', 
            'proveedor', 'conductor', 'cuenta_presupuestaria'
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'patente_vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'kilometraje_al_cargar': forms.NumberInput(attrs={'class': 'form-control'}),
            'litros': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'nro_boleta': forms.TextInput(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'conductor': forms.Select(attrs={'class': 'form-control'}),
            'cuenta_presupuestaria': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.fecha:
            self.fields['fecha'].widget.attrs['value'] = self.instance.fecha.strftime('%Y-%m-%d')


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
        # Formatear fecha_salida para input type="date"
        if self.instance.pk and self.instance.fecha_salida:
            self.fields['fecha_salida'].widget.attrs['value'] = self.instance.fecha_salida.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        mano_obra = cleaned_data.get('costo_mano_obra') or 0
        repuestos = cleaned_data.get('costo_repuestos') or 0
        
        if mano_obra + repuestos <= 0:
            raise forms.ValidationError("Debe ingresar los costos reales para finalizar el mantenimiento.")
        
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
        # Establecer valor por defecto para nivel_urgencia si no existe
        if not self.instance.pk:
            self.fields['nivel_urgencia'].initial = 'Media'
        if self.instance.pk and self.instance.fecha_reporte:
            self.fields['fecha_reporte'].widget.attrs['value'] = self.instance.fecha_reporte.strftime('%Y-%m-%d')


class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['vehiculo', 'anio', 'cuenta', 'monto_asignado', 'activo']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'monto_asignado': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'vehiculo': 'Vehículo (opcional)',
            'anio': 'Año Presupuestario',
            'cuenta': 'Cuenta SIGFE',
            'monto_asignado': 'Monto Asignado',
        }
        help_texts = {
            'vehiculo': 'Dejar en blanco para presupuesto general de flota',
            'anio': 'Ej: 2024',
            'monto_asignado': 'Monto en pesos chilenos',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar vehículos por patente
        self.fields['vehiculo'].queryset = Vehiculo.objects.all().order_by('patente')
        # Ordenar cuentas por código
        self.fields['cuenta'].queryset = CuentaPresupuestaria.objects.all().order_by('codigo')
        # Hacer vehículo opcional
        self.fields['vehiculo'].required = False
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
        vehiculo = cleaned_data.get('vehiculo')
        
        # Validar combinación única
        if anio and cuenta:
            existing = Presupuesto.objects.filter(
                anio=anio,
                cuenta=cuenta,
                vehiculo=vehiculo
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
    class Meta:
        model = Arriendo
        fields = [
            'vehiculo_reemplazado', 'proveedor', 
            'patente_arrendada', 'marca_modelo_arrendado',
            'fecha_inicio', 'fecha_fin', 'costo_diario',
            'motivo', 'nro_orden_compra'
        ]
        widgets = {
            'vehiculo_reemplazado': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'patente_arrendada': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: ABC-123'}),
            'marca_modelo_arrendado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Mercedes Sprinter'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'costo_diario': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'nro_orden_compra': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if self.instance.fecha_inicio:
                self.fields['fecha_inicio'].widget.attrs['value'] = self.instance.fecha_inicio.strftime('%Y-%m-%d')
            if self.instance.fecha_fin:
                self.fields['fecha_fin'].widget.attrs['value'] = self.instance.fecha_fin.strftime('%Y-%m-%d')


class OrdenCompraForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = [
            'nro_oc', 'fecha_emision', 'proveedor', 
            'monto_neto', 'impuesto', 'monto_total',
            'id_licitacion', 'folio_sigfe', 'estado',
            'archivo_adjunto', 'cuenta_presupuestaria'
        ]
        widgets = {
            'nro_oc': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'monto_neto': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'id_licitacion': forms.TextInput(attrs={'class': 'form-control'}),
            'folio_sigfe': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'cuenta_presupuestaria': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.fecha_emision:
            self.fields['fecha_emision'].widget.attrs['value'] = self.instance.fecha_emision.strftime('%Y-%m-%d')

class OrdenTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo
        fields = [
            'nro_ot', 'descripcion', 'fecha_solicitud', 'vehiculo',
            'proveedor', 'orden_compra'
        ]
        widgets = {
            'nro_ot': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'fecha_solicitud': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'orden_compra': forms.Select(attrs={'class': 'form-control'}),
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
