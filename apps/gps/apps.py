"""
GPS Application Configuration
"""
from django.apps import AppConfig


class GpsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.gps'
    verbose_name = 'GPS Tracking System'
