from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Usuario, Vehiculo, Proveedor, OrdenCompra, OrdenTrabajo,
    Presupuesto, Arriendo, HojaRuta, Viaje, CargaCombustible,
    Mantenimiento, FallaReportada
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
        required=False
    )
    password_confirm = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = Usuario
        fields = ['rut', 'nombre', 'apellido', 'email', 'rol', 'activo']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password != password_confirm:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = [
            'patente', 'marca', 'modelo', 'vin', 'nro_motor', 'anio_adquisicion',
            'vida_util', 'kilometraje_actual', 'umbral_mantencion', 'tipo_carroceria',
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
            'clase_ambulancia': forms.TextInput(attrs={'class': 'form-control'}),
            'es_samu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'establecimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'criticidad': forms.Select(attrs={'class': 'form-control'}),
            'es_backup': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'tipo_propiedad': forms.Select(attrs={'class': 'form-control'}),
        }


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['rut_empresa', 'nombre_fantasia', 'giro', 'telefono', 'email_contacto']
        widgets = {
            'rut_empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'giro': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email_contacto': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class HojaRutaForm(forms.ModelForm):
    class Meta:
        model = HojaRuta
        fields = ['fecha', 'turno', 'vehiculo', 'km_inicio', 'km_fin', 'litros_inicio', 'litros_fin', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'turno': forms.Select(attrs={'class': 'form-control'}),
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'km_inicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'km_fin': forms.NumberInput(attrs={'class': 'form-control'}),
            'litros_inicio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'litros_fin': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['hora_salida', 'hora_llegada', 'destino', 'rut_paciente', 'tipo_servicio', 'km_recorridos']
        widgets = {
            'hora_salida': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_llegada': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'rut_paciente': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_servicio': forms.Select(attrs={'class': 'form-control'}),
            'km_recorridos': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CargaCombustibleForm(forms.ModelForm):
    class Meta:
        model = CargaCombustible
        fields = ['fecha', 'patente_vehiculo', 'kilometraje_al_cargar', 'litros', 'costo_total', 'nro_boleta', 'proveedor']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'patente_vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'kilometraje_al_cargar': forms.NumberInput(attrs={'class': 'form-control'}),
            'litros': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'nro_boleta': forms.TextInput(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
        }


class MantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = [
            'vehiculo', 'tipo_mantencion', 'fecha_ingreso', 'fecha_salida',
            'km_al_ingreso', 'proveedor', 'orden_trabajo', 'orden_compra',
            'costo_total', 'descripcion', 'estado'
        ]
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'tipo_mantencion': forms.Select(attrs={'class': 'form-control'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_salida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'km_al_ingreso': forms.NumberInput(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'orden_trabajo': forms.Select(attrs={'class': 'form-control'}),
            'orden_compra': forms.Select(attrs={'class': 'form-control'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }


class FallaReportadaForm(forms.ModelForm):
    class Meta:
        model = FallaReportada
        fields = ['vehiculo', 'fecha_reporte', 'descripcion']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'fecha_reporte': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['vehiculo', 'anio', 'categoria', 'subasignacion_sigfe', 'monto_asignado']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'subasignacion_sigfe': forms.TextInput(attrs={'class': 'form-control'}),
            'monto_asignado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class ArriendoForm(forms.ModelForm):
    class Meta:
        model = Arriendo
        fields = ['vehiculo', 'proveedor', 'fecha_inicio', 'fecha_fin', 'costo_diario', 'costo_total', 'nro_orden_compra', 'estado']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'costo_diario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'nro_orden_compra': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }

