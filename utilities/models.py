from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import os

User = get_user_model()


def upload_water_image(instance, filename):
    return f'water_readings/{timezone.now().strftime("%Y/%m")}/{filename}'


class WaterMeter(models.Model):
    METER_TYPES = [
        ('hot', 'Hot Water'),
        ('cold', 'Cold Water'),
    ]
    
    name = models.CharField(max_length=100)
    meter_type = models.CharField(max_length=10, choices=METER_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cost_per_unit = models.DecimalField(max_digits=8, decimal_places=4, default=0.0050, help_text="Cost per liter")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_meter_type_display()}"


class WaterReading(models.Model):
    meter = models.ForeignKey(WaterMeter, on_delete=models.CASCADE, related_name='readings')
    image = models.ImageField(upload_to=upload_water_image)
    reading_value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    timestamp = models.DateTimeField()
    processed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['meter', 'timestamp']
    
    def __str__(self):
        return f"{self.meter.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class WaterUsage(models.Model):
    meter = models.ForeignKey(WaterMeter, on_delete=models.CASCADE, related_name='usage_records')
    date = models.DateField()
    start_reading = models.DecimalField(max_digits=10, decimal_places=3)
    end_reading = models.DecimalField(max_digits=10, decimal_places=3)
    usage_amount = models.DecimalField(max_digits=10, decimal_places=3)
    cost_per_unit = models.DecimalField(max_digits=8, decimal_places=4, default=0.0050)
    calculated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['meter', 'date']
    
    def save(self, *args, **kwargs):
        self.usage_amount = self.end_reading - self.start_reading
        self.calculated_cost = self.usage_amount * self.cost_per_unit
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.meter.name} - {self.date} ({self.usage_amount}L)"


class CostPrediction(models.Model):
    meter = models.ForeignKey(WaterMeter, on_delete=models.CASCADE, related_name='predictions')
    prediction_date = models.DateField()
    predicted_usage = models.DecimalField(max_digits=10, decimal_places=3)
    predicted_cost = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-prediction_date']
    
    def __str__(self):
        return f"{self.meter.name} - {self.prediction_date} Prediction"
