from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.conf import settings


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')  # Force admin role for superusers
        return super().create_superuser(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('reader', 'Reader (Can Upload)'),
        ('viewer', 'Viewer (Read Only)'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='viewer')
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = CustomUserManager()
    
    def save(self, *args, **kwargs):
        # Automatically set admin role for superusers
        if self.is_superuser and self.role == 'viewer':
            self.role = 'admin'
        super().save(*args, **kwargs)
    
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    def can_upload(self):
        return self.role in ['admin', 'reader'] or self.is_superuser
    
    def can_only_view(self):
        return self.role == 'viewer' and not self.is_superuser


class UserSettings(models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('PLN', 'Polish Złoty (zł)'),
        ('GBP', 'British Pound (£)'),
        ('JPY', 'Japanese Yen (¥)'),
        ('CAD', 'Canadian Dollar (C$)'),
        ('AUD', 'Australian Dollar (A$)'),
        ('CHF', 'Swiss Franc (CHF)'),
        ('SEK', 'Swedish Krona (kr)'),
        ('NOK', 'Norwegian Krone (kr)'),
        ('CZK', 'Czech Koruna (Kč)'),
        ('HUF', 'Hungarian Forint (Ft)'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='settings')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"
    
    def __str__(self):
        return f"{self.user.username} Settings"
    
    def get_currency_symbol(self):
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'PLN': 'zł',
            'GBP': '£',
            'JPY': '¥',
            'CAD': 'C$',
            'AUD': 'A$',
            'CHF': 'CHF',
            'SEK': 'kr',
            'NOK': 'kr',
            'CZK': 'Kč',
            'HUF': 'Ft',
        }
        return currency_symbols.get(self.currency, self.currency)
    
    @classmethod
    def get_or_create_for_user(cls, user):
        settings, created = cls.objects.get_or_create(user=user)
        return settings
