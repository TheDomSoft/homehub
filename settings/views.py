from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from .models import UserSettings


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['currency']
        widgets = {
            'currency': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].label = "Preferred Currency"


@login_required
def user_settings(request):
    settings = UserSettings.get_or_create_for_user(request.user)
    
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings:user_settings')
    else:
        form = UserSettingsForm(instance=settings)
    
    return render(request, 'settings/user_settings.html', {
        'form': form,
        'settings': settings
    })
