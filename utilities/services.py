import google.generativeai as genai
from django.conf import settings
from PIL import Image
from PIL.ExifTags import TAGS
import os
from django.utils import timezone
import pytz
import re
from datetime import datetime, timezone as dt_timezone, timedelta
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
            if hasattr(image_path_or_file, 'seek'):
                try:
                    image_path_or_file.seek(0)
                except Exception:
                    pass

            # Always read EXIF from the original file if possible to avoid metadata loss from edits/crops
            exif_source = image_path_or_file
            if hasattr(image_path_or_file, 'original_file'):  # custom attribute if we pass it
                exif_source = image_path_or_file.original_file or image_path_or_file

            image = Image.open(exif_source)
            exif_data = image.getexif()

            def parse_exif_datetime(raw_dt: str, offset: str = None):
                """Parse EXIF datetime with improved error handling and timezone support"""
                try:
                    # Handle different datetime formats
                    dt_formats = [
                        "%Y:%m:%d %H:%M:%S",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y:%m:%d %H:%M:%S.%f",
                        "%Y-%m-%d %H:%M:%S.%f"
                    ]
                    
                    dt = None
                    for fmt in dt_formats:
                        try:
                            dt = datetime.strptime(raw_dt, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not dt:
                        return None
                    
                    # Handle timezone offset
                    if offset and len(offset) >= 6 and offset[0] in ['+', '-']:
                        try:
                            sign = 1 if offset[0] == '+' else -1
                            hours = int(offset[1:3])
                            minutes = int(offset[4:6])
                            tz = dt_timezone(timedelta(hours=sign * hours, minutes=sign * minutes))
                            return dt.replace(tzinfo=tz)
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to parse timezone offset '{offset}': {e}")
                    
                    # Use Django's timezone setting if available
                    try:
                        if hasattr(settings, 'TIME_ZONE') and settings.TIME_ZONE:
                            local_tz = pytz.timezone(settings.TIME_ZONE)
                            return local_tz.localize(dt)
                    except Exception as e:
                        logger.warning(f"Failed to use Django timezone: {e}")
                    
                    # Fallback to system timezone
                    try:
                        # More reliable way to get local timezone
                        import time
                        if time.daylight:
                            local_tz = dt_timezone(timedelta(seconds=-time.altzone))
                        else:
                            local_tz = dt_timezone(timedelta(seconds=-time.timezone))
                        return dt.replace(tzinfo=local_tz)
                    except Exception:
                        # Last resort: use UTC
                        return dt.replace(tzinfo=dt_timezone.utc)
                        
                except Exception as e:
                    logger.error(f"Error parsing EXIF datetime '{raw_dt}': {e}")
                    return None

            timestamp = None
            
            if exif_data:
                # Build tag name -> value map
                exif_by_name = {}
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    exif_by_name[tag_name] = value

                # Try common EXIF datetime tags by priority
                raw_dt = None
                datetime_tags = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]
                
                for tag in datetime_tags:
                    if tag in exif_by_name and exif_by_name[tag]:
                        raw_dt = str(exif_by_name[tag]).strip()
                        if raw_dt and raw_dt != "0000:00:00 00:00:00":
                            break
                        raw_dt = None

                # Get timezone offset
                offset_time = None
                offset_tags = ["OffsetTimeOriginal", "OffsetTimeDigitized", "OffsetTime"]
                for tag in offset_tags:
                    if tag in exif_by_name and exif_by_name[tag]:
                        offset_time = str(exif_by_name[tag]).strip()
                        break

                if raw_dt:
                    timestamp = parse_exif_datetime(raw_dt, offset_time)

            # Fallback strategies if no EXIF timestamp
            if not timestamp:
                timestamp = ImageMetadataExtractor._get_file_timestamp(image_path_or_file)

            # If still no timestamp, use current time with warning
            if not timestamp:
                logger.warning("No timestamp found in image, using current time")
                timestamp = timezone.now()

            return timestamp
            
        except Exception as e:
            logger.error(f"Error extracting timestamp: {e}")
            # Return current time as last resort
            return timezone.now()
    
    @staticmethod
    def _get_file_timestamp(image_path_or_file):
        """Extract timestamp from file system metadata"""
        try:
            file_path = None
            
            if isinstance(image_path_or_file, str):
                file_path = image_path_or_file
            else:
                # Try to get file path from uploaded file object
                if hasattr(image_path_or_file, 'temporary_file_path'):
                    try:
                        file_path = image_path_or_file.temporary_file_path()
                    except Exception:
                        pass
                
                if not file_path and hasattr(image_path_or_file, 'name'):
                    file_path = image_path_or_file.name

            if file_path and os.path.exists(file_path):
                # Use modification time (usually more reliable than creation time)
                mtime = os.path.getmtime(file_path)
                
                # Convert to timezone-aware datetime
                if hasattr(settings, 'TIME_ZONE') and settings.TIME_ZONE:
                    try:
                        local_tz = pytz.timezone(settings.TIME_ZONE)
                        return datetime.fromtimestamp(mtime, tz=local_tz)
                    except Exception:
                        pass
                
                # Fallback to UTC
                return datetime.fromtimestamp(mtime, tz=dt_timezone.utc)
                
        except Exception as e:
            logger.error(f"Error getting file timestamp: {e}")
            
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