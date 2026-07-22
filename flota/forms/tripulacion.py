from django import forms

from ..models import PersonaTripulacion


class PersonaTripulacionForm(forms.ModelForm):
    class Meta:
        model = PersonaTripulacion
        fields = ['nombre', 'rol']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            raise forms.ValidationError('El nombre es obligatorio.')
        return nombre
