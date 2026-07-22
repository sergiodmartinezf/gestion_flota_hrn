from django import forms

from ..models import DireccionDestino


class DireccionDestinoForm(forms.ModelForm):
    class Meta:
        model = DireccionDestino
        fields = ['texto']
        widgets = {
            'texto': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'texto': 'Dirección / detalle',
        }

    def clean_texto(self):
        texto = (self.cleaned_data.get('texto') or '').strip()
        if not texto:
            raise forms.ValidationError('La dirección es obligatoria.')
        return texto[:200]
