from flask import Flask
from datetime import datetime
from dotenv import load_dotenv
import logging
import pytz
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY")

    from . import main
    app.register_blueprint(main.bp)

    from . import standup
    app.register_blueprint(standup.bp)

    @app.template_filter('format_date')
    def format_date(value, format='%Y-%m-%d %I:%M %p'):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        if isinstance(value, datetime):
            return value.strftime(format)
        return value


    @app.template_filter('format_time')
    def format_time(value, format='%I:%M %p'):
        if isinstance(value, str):
            try:
                time_object = datetime.strptime(value, '%H:%M:00').time()
                return time_object.strftime(format)

            except ValueError:
                pass
            
        return value


    @app.template_filter('convert_timezone')
    def convert_timezone(value, source_tz='UTC', target_tz='UTC', format='%Y-%m-%d %I:%M %p'):
        """Convert datetime from one timezone to another and format it"""
        if isinstance(value, str):
            try:
                # Parse the string to datetime, assuming it's in UTC if no timezone info
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        
        if isinstance(value, datetime):
            # If the datetime has no timezone info, assume it's in source_tz
            if value.tzinfo is None:
                source_timezone = pytz.timezone(source_tz)
                value = source_timezone.localize(value)
            
            # Convert to target timezone
            target_timezone = pytz.timezone(target_tz)
            converted = value.astimezone(target_timezone)
            
            # Format the datetime
            return converted.strftime(format)
        
        return value

    return app
