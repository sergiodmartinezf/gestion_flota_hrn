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

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 4 caracteres y al menos un número'}),
        required=True,
        help_text='Requisitos: mínimo 4 caracteres y al menos un número (0-9)'
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
        if rut:
            es_valido, mensaje = validar_rut_chileno(rut)
            if not es_valido:
                raise forms.ValidationError(mensaje)
            rut_norm = normalizar_rut(rut)
            if rut_norm:
                return rut_norm
        return rut
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            if password.strip() == '':
                raise forms.ValidationError('La contraseña no puede estar compuesta solo por espacios.')
        
        # Solo validar si se proporcionó una contraseña (en creación o cambio)
        if password:
            # Validar longitud mínima
            if len(password) < 4:
                raise forms.ValidationError('La contraseña debe tener al menos 4 caracteres.')

            # Validar al menos un número
            if not re.search(r'[0-9]', password):
                raise forms.ValidationError('La contraseña debe contener al menos un número.')
        
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


