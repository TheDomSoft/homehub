from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json

from utilities.models import WaterMeter, WaterReading, WaterUsage


@login_required
def dashboard_home(request):
    user_meters = WaterMeter.objects.filter(user=request.user, is_active=True)
    
    # Summary statistics
    total_readings = WaterReading.objects.filter(meter__user=request.user).count()
    processed_readings = WaterReading.objects.filter(
        meter__user=request.user, 
        processed=True
    ).count()
    
    # Recent readings
    recent_readings = WaterReading.objects.filter(
        meter__user=request.user
    ).order_by('-timestamp')[:5]
    
    # Monthly usage summary
    current_month = timezone.now().replace(day=1)
    monthly_data = {}
    
    for meter in user_meters:
        readings = WaterReading.objects.filter(
            meter=meter,
            processed=True,
            timestamp__gte=current_month
        ).order_by('timestamp')
        
        if readings.count() >= 2:
            first_reading = readings.first()
            last_reading = readings.last()
            usage = float(last_reading.reading_value - first_reading.reading_value)
            
            monthly_data[meter.name] = {
                'usage': usage,
                'cost': usage * float(meter.cost_per_unit),
                'readings_count': readings.count()
            }
    
    context = {
        'user_meters': user_meters,
        'total_readings': total_readings,
        'processed_readings': processed_readings,
        'recent_readings': recent_readings,
        'monthly_data': monthly_data,
        'processing_rate': (processed_readings / total_readings * 100) if total_readings > 0 else 0
    }
    
    return render(request, 'dashboard/home.html', context)
