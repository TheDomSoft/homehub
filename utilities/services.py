import google.generativeai as genai
from django.conf import settings
from PIL import Image
from PIL.ExifTags import TAGS
import os
from django.utils import timezone
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
    def extract_timestamp_from_image(image_path_or_file):
        try:
            # Ensure file-like objects are at the start
            try:
                if hasattr(image_path_or_file, 'seek'):
                    image_path_or_file.seek(0)
            except Exception:
                pass

            image = Image.open(image_path_or_file)
            exif_data = image.getexif()

            def parse_exif_datetime(raw_dt: str, offset: str | None = None):
                try:
                    dt = datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S")
                    # Make timezone-aware using local timezone
                    aware_dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    if offset and len(offset) >= 6 and offset[0] in ['+', '-']:
                        # Offset like +01:00; convert to timedelta and adjust
                        try:
                            sign = 1 if offset[0] == '+' else -1
                            hours = int(offset[1:3])
                            minutes = int(offset[4:6])
                            aware_dt = aware_dt.replace() + sign * timezone.timedelta(hours=hours, minutes=minutes)
                        except Exception:
                            pass
                    return aware_dt
                except Exception:
                    return None

            timestamp = None
            offset_time = None
            if exif_data:
                # Build tag name -> value map
                exif_by_name = {}
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    exif_by_name[tag_name] = value

                # Try common EXIF datetime tags by priority
                raw_dt = None
                for key in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                    if key in exif_by_name and exif_by_name[key]:
                        raw_dt = exif_by_name[key]
                        break

                # Timezone offset tags if present
                for key in ["OffsetTimeOriginal", "OffsetTimeDigitized", "OffsetTime"]:
                    if key in exif_by_name and exif_by_name[key]:
                        offset_time = str(exif_by_name[key])
                        break

                if raw_dt:
                    timestamp = parse_exif_datetime(str(raw_dt), offset_time)

            if not timestamp:
                # Fallback to file creation time if we have a path
                file_path = None
                if isinstance(image_path_or_file, str):
                    file_path = image_path_or_file
                else:
                    # Some uploaded files expose a temporary file name
                    file_path = getattr(image_path_or_file, 'temporary_file_path', lambda: None)()
                    if not file_path:
                        file_path = getattr(image_path_or_file, 'name', None)

                if file_path and os.path.exists(file_path):
                    try:
                        ctime = os.path.getctime(file_path)
                        timestamp = timezone.make_aware(datetime.fromtimestamp(ctime), timezone.get_current_timezone())
                    except Exception:
                        pass

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