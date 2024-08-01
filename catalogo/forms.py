from django import forms
from .models import Productor

class ProductorForm(forms.ModelForm):
    class Meta:
        model = Productor
        fields = '__all__'
