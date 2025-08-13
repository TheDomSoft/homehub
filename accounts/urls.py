from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.user_settings, name='user_settings'),
    path('users/', views.user_management, name='user_management'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
]