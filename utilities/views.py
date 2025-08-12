from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Avg
from datetime import datetime, timedelta
import json

from .models import WaterMeter, WaterReading, WaterUsage, CostPrediction
from .forms import WaterReadingUploadForm, WaterMeterForm
from .services import GeminiWaterMeterReader, ImageMetadataExtractor, WaterUsageCalculator
import logging

logger = logging.getLogger(__name__)

@login_required
def upload_reading(request):
    if request.method == 'POST':
        form = WaterReadingUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            reading = form.save(commit=False)
            
            # Use original timestamp if provided from frontend, otherwise extract from image
            original_timestamp = request.POST.get('original_timestamp')
            original_tz_offset = request.POST.get('original_tz_offset')
            original_last_modified_ms = request.POST.get('original_last_modified_ms')
            logger.info(f"Original timestamp: {original_timestamp}")
            logger.info(f"Original tz offset: {original_tz_offset}")
            if original_timestamp and not reading.timestamp:
                try:
                    # Normalize to ISO with 'T' separator
                    ts = original_timestamp.strip().replace(' ', 'T')
                    # If no explicit tz in timestamp, apply provided offset
                    has_tz = ('+' in ts[10:] or '-' in ts[10:] or ts.endswith('Z'))
                    if not has_tz and original_tz_offset:
                        ts = f"{ts}{original_tz_offset}"
                    # Parse ISO string
                    parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if timezone.is_naive(parsed):
                        # As a last resort, assume server local timezone (not ideal)
                        reading.timestamp = timezone.make_aware(parsed, timezone.get_current_timezone())
                    else:
                        reading.timestamp = parsed
                except (ValueError, TypeError):
                    reading.timestamp = None
            
            # If still not set, try client lastModified with client tz offset
            if not reading.timestamp and original_last_modified_ms:
                try:
                    ms = int(original_last_modified_ms)
                    dt_local = datetime.fromtimestamp(ms / 1000.0)
                    if original_tz_offset:
                        parsed = datetime.fromisoformat(dt_local.strftime('%Y-%m-%dT%H:%M:%S') + original_tz_offset)
                        reading.timestamp = parsed if not timezone.is_naive(parsed) else timezone.make_aware(parsed)
                except Exception:
                    reading.timestamp = None

            # Absolute last resort: current time
            if not reading.timestamp:
                reading.timestamp = timezone.now()
            
            # Check if manual reading value is provided
            manual_value = form.cleaned_data.get('reading_value_manual')
            if manual_value is not None:
                # User provided manual value, use it directly
                reading.reading_value = manual_value
                reading.processed = True
                reading.save()
                messages.success(request, f'Reading saved successfully with manual value: {manual_value}')
            else:
                # No manual value, proceed with AI processing
                reading.save()
                
                try:
                    gemini_reader = GeminiWaterMeterReader()
                    reading_value, _ = gemini_reader.extract_reading_from_image(
                        reading.image.path, 
                        reading.meter.meter_type
                    )
                    
                    if reading_value is not None:
                        reading.reading_value = reading_value
                        reading.processed = True
                        reading.save()
                        
                        messages.success(request, f'Reading processed successfully by AI: {reading_value}')
                    else:
                        messages.warning(request, 'Could not extract reading from image. Please edit the reading to add value manually.')
                        
                except Exception as e:
                    messages.error(request, f'Error processing image: {str(e)}')
            
            return redirect('utilities:readings_list')
    else:
        form = WaterReadingUploadForm(user=request.user)
    
    return render(request, 'utilities/upload_reading.html', {'form': form})


@login_required
def readings_list(request):
    readings = WaterReading.objects.filter(meter__user=request.user)
    return render(request, 'utilities/readings_list.html', {'readings': readings})


@login_required
def meter_management(request):
    if request.method == 'POST':
        form = WaterMeterForm(request.POST)
        if form.is_valid():
            meter = form.save(commit=False)
            meter.user = request.user
            meter.save()
            messages.success(request, 'Meter added successfully!')
            return redirect('utilities:meter_management')
    else:
        form = WaterMeterForm()
    
    meters = WaterMeter.objects.filter(user=request.user)
    return render(request, 'utilities/meter_management.html', {
        'form': form,
        'meters': meters
    })


@login_required
def edit_meter(request, meter_id):
    meter = get_object_or_404(WaterMeter, id=meter_id, user=request.user)
    
    if request.method == 'POST':
        form = WaterMeterForm(request.POST, instance=meter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Meter updated successfully!')
            return redirect('utilities:meter_management')
    else:
        form = WaterMeterForm(instance=meter)
    
    return render(request, 'utilities/edit_meter.html', {
        'form': form,
        'meter': meter
    })


@login_required
def delete_meter(request, meter_id):
    meter = get_object_or_404(WaterMeter, id=meter_id, user=request.user)
    
    # Check if meter has readings
    readings_count = meter.readings.count()
    
    if request.method == 'POST':
        meter_name = meter.name
        meter.delete()
        messages.success(request, f'Meter "{meter_name}" deleted successfully!')
        return redirect('utilities:meter_management')
    
    return render(request, 'utilities/confirm_delete_meter.html', {
        'meter': meter,
        'readings_count': readings_count
    })


@login_required
def usage_analytics(request):
    meters = WaterMeter.objects.filter(user=request.user)
    analytics_data = {}
    
    for meter in meters:
        # Get recent readings ordered by timestamp
        readings = WaterReading.objects.filter(
            meter=meter, 
            processed=True
        ).order_by('timestamp')
        
        if len(readings) >= 2:
            daily_usages = []
            readings_data = []
            
            for i in range(1, len(readings)):
                prev_reading = readings[i-1]
                curr_reading = readings[i]
                
                # Calculate usage
                raw_usage = float(curr_reading.reading_value) - float(prev_reading.reading_value)
                usage = raw_usage
                
                daily_usages.append(usage)
                readings_data.append({
                    'date': curr_reading.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'usage': usage,
                    'current_reading': float(curr_reading.reading_value),
                    'previous_reading': float(prev_reading.reading_value),
                    'has_issue': usage < 0
                })
                
            # Check for data quality issues
            negative_readings = [r for r in readings_data if r['has_issue']]
            valid_usages = [u for u in daily_usages if u > 0]
            
            # Calculate predictions only if we have positive usage data
            if any(u > 0 for u in valid_usages):
                positive_usages = [u for u in valid_usages if u > 0]
                predicted_usage, predicted_cost = WaterUsageCalculator.predict_monthly_cost(positive_usages, float(meter.cost_per_unit))
                avg_daily = sum(positive_usages) / len(positive_usages)
                
                analytics_data[meter.name] = {
                    'daily_usages': daily_usages,
                    'average_daily': avg_daily,
                    'predicted_monthly_usage': predicted_usage,
                    'predicted_monthly_cost': predicted_cost,
                    'readings_dates': [r['date'] for r in readings_data],
                    'total_readings': len(readings),
                    'has_negative_usage': len(negative_readings) > 0,
                    'negative_count': len(negative_readings),
                    'data_quality_issues': negative_readings,
                }
            else:
                # No valid data for calculations
                analytics_data[meter.name] = {
                    'daily_usages': daily_usages,
                    'average_daily': 0,
                    'predicted_monthly_usage': 0,
                    'predicted_monthly_cost': 0,
                    'readings_dates': [r['date'] for r in readings_data],
                    'total_readings': len(readings),
                    'has_negative_usage': len(negative_readings) > 0,
                    'negative_count': len(negative_readings),
                    'data_quality_issues': negative_readings,
                    'no_valid_data': True,
                }
    
    return render(request, 'utilities/usage_analytics.html', {
        'analytics_data': analytics_data,
        'meters': meters
    })


@login_required
def edit_reading(request, reading_id):
    reading = get_object_or_404(WaterReading, id=reading_id, meter__user=request.user)
    
    if request.method == 'POST':
        form = WaterReadingUploadForm(request.POST, request.FILES, instance=reading, user=request.user)
        if form.is_valid():
            updated_reading = form.save(commit=False)
            
            # Check if manual reading value is provided
            manual_value = form.cleaned_data.get('reading_value_manual')
            if manual_value is not None:
                updated_reading.reading_value = manual_value
                updated_reading.processed = True
            
            # If new image is uploaded, process with AI (unless manual value is provided)
            if 'image' in form.changed_data and not manual_value:
                try:
                    gemini_reader = GeminiWaterMeterReader()
                    reading_value, _ = gemini_reader.extract_reading_from_image(
                        updated_reading.image.path,
                        updated_reading.meter.meter_type
                    )
                    
                    if reading_value is not None:
                        updated_reading.reading_value = reading_value
                        updated_reading.processed = True
                        messages.info(request, f'New image processed by AI: {reading_value}')
                    else:
                        messages.warning(request, 'Could not extract reading from new image.')
                        
                except Exception as e:
                    messages.error(request, f'Error processing new image: {str(e)}')
            
            updated_reading.save()
            
            if manual_value is not None:
                messages.success(request, f'Reading updated successfully with manual value: {manual_value}')
            else:
                messages.success(request, 'Reading updated successfully!')
            
            return redirect('utilities:readings_list')
    else:
        form = WaterReadingUploadForm(instance=reading, user=request.user)
    
    return render(request, 'utilities/edit_reading.html', {
        'form': form,
        'reading': reading
    })


@login_required
def delete_reading(request, reading_id):
    reading = get_object_or_404(WaterReading, id=reading_id, meter__user=request.user)
    
    if request.method == 'POST':
        reading.delete()
        messages.success(request, 'Reading deleted successfully!')
        return redirect('utilities:readings_list')
    
    return render(request, 'utilities/confirm_delete.html', {'reading': reading})


@login_required
def api_usage_data(request):
    meters = WaterMeter.objects.filter(user=request.user)
    data = {}
    
    for meter in meters:
        readings = WaterReading.objects.filter(
            meter=meter,
            processed=True,
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).order_by('timestamp')
        
        usage_data = []
        for i in range(1, len(readings)):
            prev = readings[i-1]
            curr = readings[i]
            usage = float(curr.reading_value - prev.reading_value) if curr.reading_value > prev.reading_value else 0
            usage_data.append({
                'date': curr.timestamp.strftime('%Y-%m-%d'),
                'usage': usage,
                'reading': float(curr.reading_value)
            })
        
        data[meter.name] = usage_data
    
    return JsonResponse(data)
