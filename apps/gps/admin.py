"""
Django Admin Configuration for GPS Application
"""
from django.contrib import admin
from .models import GpsData


@admin.register(GpsData)
class GpsDataAdmin(admin.ModelAdmin):
    """
    Admin interface for GPS data
    """
    list_display = ['id', 'timestamp', 'mac', 'latitude', 'longitude', 
                    'speed_kmh', 'num_satellites', 'quality']
    list_filter = ['quality', 'timestamp']
    search_fields = ['mac']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('timestamp', 'mac')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'altitude')
        }),
        ('GPS Quality', {
            'fields': ('quality', 'num_satellites', 'hdop')
        }),
        ('Movement', {
            'fields': ('speed_kmh', 'course')
        }),
    )
