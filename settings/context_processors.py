from .models import UserSettings


def user_settings(request):
    """
    Context processor to make user settings available in all templates
    """
    if request.user.is_authenticated:
        try:
            settings = UserSettings.objects.get(user=request.user)
            return {
                'user_settings': settings,
                'currency_symbol': settings.get_currency_symbol(),
            }
        except UserSettings.DoesNotExist:
            # Create default settings if they don't exist
            settings = UserSettings.objects.create(user=request.user)
            return {
                'user_settings': settings,
                'currency_symbol': settings.get_currency_symbol(),
            }
    return {
        'user_settings': None,
        'currency_symbol': '$',  # Default for anonymous users
    }