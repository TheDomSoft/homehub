import google.generativeai as genai
from django.conf import settings
from PIL import Image
from PIL.ExifTags import TAGS
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GeminiWaterMeterReader:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def extract_reading_from_image(self, image_path, meter_type='water'):
        try:
            image = Image.open(image_path)
            
            prompt = f"""
            Analyze this {meter_type} meter reading image and extract the current reading value.
            
            Instructions:
            1. Look for digital or analog display showing numbers
            2. Return only the numerical reading (e.g., 1234.567)
            3. If you see multiple numbers, choose the main meter reading
            4. If the reading is unclear, return "UNCLEAR"
            5. Be precise with decimal places if visible
            
            Response format: Just the number or "UNCLEAR"
            """
            
            response = self.model.generate_content([prompt, image])
            reading_text = response.text.strip()
            
            # Extract numerical value
            number_match = re.search(r'\d+\.?\d*', reading_text)
            if number_match:
                reading_value = float(number_match.group())
                return reading_value, None
            else:
                return None, None
                
        except Exception as e:
            logger.error(f"Error processing image with Gemini: {e}")
            return None, None
    


class ImageMetadataExtractor:
    @staticmethod
    def extract_timestamp_from_image(image_path):
        try:
            image = Image.open(image_path)
            exif_data = image.getexif()
            
            timestamp = None
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "DateTime":
                    timestamp = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    break
            
            return timestamp
        except Exception as e:
            logger.error(f"Error extracting timestamp: {e}")
            return None
    
    @staticmethod
    def get_image_info(image_path):
        try:
            image = Image.open(image_path)
            return {
                'format': image.format,
                'size': image.size,
                'mode': image.mode,
            }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return None


class WaterUsageCalculator:
    @staticmethod
    def calculate_daily_usage(previous_reading, current_reading):
        if previous_reading and current_reading:
            usage = current_reading - previous_reading
            return max(0, usage)  # Ensure non-negative usage
        return 0
    
    @staticmethod
    def predict_monthly_cost(daily_usages, cost_per_unit=0.005):
        if not daily_usages:
            return 0, 0
        
        average_daily = sum(daily_usages) / len(daily_usages)
        days_in_month = 30
        predicted_monthly_usage = average_daily * days_in_month
        predicted_cost = predicted_monthly_usage * cost_per_unit
        
        return predicted_monthly_usage, predicted_cost