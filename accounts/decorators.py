from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import render


def role_required(role):
    """
    Decorator to require a specific role or higher.
    Role hierarchy: admin > reader > viewer
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user_role = request.user.role
            
            # Define role hierarchy
            role_hierarchy = {
                'viewer': 1,
                'reader': 2, 
                'admin': 3
            }
            
            required_level = role_hierarchy.get(role, 0)
            user_level = role_hierarchy.get(user_role, 0)
            
            if user_level >= required_level:
                return view_func(request, *args, **kwargs)
            else:
                return render(request, 'errors/403.html', {
                    'message': f'You need {role} role or higher to access this page.'
                }, status=403)
        
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator to require admin role"""
    return role_required('admin')(view_func)


def reader_required(view_func):
    """Decorator to require reader role or higher (admin, reader)"""
    return role_required('reader')(view_func)


def viewer_required(view_func):
    """Decorator to require viewer role or higher (admin, reader, viewer)"""
    return role_required('viewer')(view_func)