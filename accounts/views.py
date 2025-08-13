from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import UserSettings, CustomUser
from .decorators import viewer_required, admin_required


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


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class UserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


@viewer_required
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
    
    return render(request, 'accounts/user_settings.html', {
        'form': form,
        'settings': settings
    })


@admin_required
def user_management(request):
    users = CustomUser.objects.all().order_by('username')
    return render(request, 'accounts/user_management.html', {'users': users})


@admin_required
def add_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserSettings.get_or_create_for_user(user)  # Create default settings
            messages.success(request, f'User "{user.username}" created successfully!')
            return redirect('settings:user_management')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/add_user.html', {'form': form})


@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.username}" updated successfully!')
            return redirect('settings:user_management')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'accounts/edit_user.html', {'form': form, 'user': user})


@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent admin from deleting themselves
    if user == request.user:
        messages.error(request, "You cannot delete yourself!")
        return redirect('settings:user_management')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully!')
        return redirect('settings:user_management')
    
    return render(request, 'accounts/delete_user.html', {'user': user})
