from django.contrib import admin
from .models import WaterMeter, WaterReading, WaterUsage, CostPrediction


@admin.register(WaterMeter)
class WaterMeterAdmin(admin.ModelAdmin):
    list_display = ['name', 'meter_type', 'user', 'is_active', 'created_at']
    list_filter = ['meter_type', 'is_active', 'created_at']
    search_fields = ['name', 'user__username']


@admin.register(WaterReading)
class WaterReadingAdmin(admin.ModelAdmin):
    list_display = ['meter', 'timestamp', 'reading_value', 'processed']
    list_filter = ['processed', 'meter__meter_type', 'timestamp']
    search_fields = ['meter__name']
    readonly_fields = ['created_at']


@admin.register(WaterUsage)
class WaterUsageAdmin(admin.ModelAdmin):
    list_display = ['meter', 'date', 'usage_amount', 'calculated_cost']
    list_filter = ['meter__meter_type', 'date']
    search_fields = ['meter__name']


@admin.register(CostPrediction)
class CostPredictionAdmin(admin.ModelAdmin):
    list_display = ['meter', 'prediction_date', 'predicted_usage', 'predicted_cost', 'confidence_score']
    list_filter = ['meter__meter_type', 'prediction_date']
    search_fields = ['meter__name']
    readonly_fields = ['created_at']
