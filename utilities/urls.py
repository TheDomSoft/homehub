from django.urls import path
from . import views

app_name = 'utilities'

urlpatterns = [
    path('upload/', views.upload_reading, name='upload_reading'),
    path('readings/', views.readings_list, name='readings_list'),
    path('readings/<int:reading_id>/edit/', views.edit_reading, name='edit_reading'),
    path('readings/<int:reading_id>/delete/', views.delete_reading, name='delete_reading'),
    path('meters/', views.meter_management, name='meter_management'),
    path('meters/<int:meter_id>/edit/', views.edit_meter, name='edit_meter'),
    path('meters/<int:meter_id>/delete/', views.delete_meter, name='delete_meter'),
    path('analytics/', views.usage_analytics, name='usage_analytics'),
    path('api/usage-data/', views.api_usage_data, name='api_usage_data'),
]