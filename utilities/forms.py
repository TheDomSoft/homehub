from django import forms
from .models import WaterReading, WaterMeter
from django.utils import timezone


class WaterReadingUploadForm(forms.ModelForm):
    reading_value_manual = forms.DecimalField(
        max_digits=10, 
        decimal_places=3,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '0.001', 
            'min': '0',
            'placeholder': 'Enter reading manually if AI extraction is incorrect'
        }),
        label='Manual Reading Value',
        help_text='Leave empty to use AI extraction. Enter value to override AI reading.'
    )
    
    class Meta:
        model = WaterReading
        # On create, we do not allow setting timestamp; it's derived from image EXIF
        fields = ['meter', 'image', 'notes', 'reading_value_manual']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'meter': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional notes about this reading'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['meter'].queryset = WaterMeter.objects.filter(user=user, is_active=True)
        
        # If editing existing reading, populate manual field with current value
        if self.instance.pk and self.instance.reading_value:
            self.fields['reading_value_manual'].initial = self.instance.reading_value


class WaterReadingEditForm(forms.ModelForm):
    reading_value_manual = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'min': '0',
            'placeholder': 'Enter reading manually if AI extraction is incorrect'
        }),
        label='Manual Reading Value',
        help_text='Leave empty to use AI extraction. Enter value to override AI reading.'
    )

    class Meta:
        model = WaterReading
        # On edit, allow timestamp modification
        fields = ['meter', 'image', 'timestamp', 'notes', 'reading_value_manual']
        widgets = {
            'timestamp': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'meter': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional notes about this reading'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['meter'].queryset = WaterMeter.objects.filter(user=user, is_active=True)
        if self.instance.pk and self.instance.reading_value:
            self.fields['reading_value_manual'].initial = self.instance.reading_value


class WaterMeterForm(forms.ModelForm):
    class Meta:
        model = WaterMeter
        fields = ['name', 'meter_type', 'cost_per_unit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kitchen Hot Water'}),
            'meter_type': forms.Select(attrs={'class': 'form-select'}),
            'cost_per_unit': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.0001', 
                'min': '0',
                'placeholder': '0.0050'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cost_per_unit'].label = "Cost per Liter"
        self.fields['cost_per_unit'].help_text = "Cost in your local currency per liter"