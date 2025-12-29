"""
Django Admin Configuration for GPS Application
"""
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from .models import GpsData


@admin.register(GpsData)
class GpsDataAdmin(OSMGeoAdmin):
    """
    Admin interface for GPS data with map display
    """
    list_display = ['id', 'timestamp', 'player_id', 'mac', 'latitude', 'longitude', 
                    'speed_kmh', 'num_satellites', 'quality']
    list_filter = ['player_iD', 'quality', 'timestamp']
    search_fields = ['mac', 'player_id']
    date_hierarchy = 'timestamp'
    readonly_fields = ['geom']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('timestamp', 'mac', 'player_id')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'altitude', 'geom')
        }),
        ('GPS Quality', {
            'fields': ('quality', 'num_satellites', 'hdop')
        }),
        ('Movement', {
            'fields': ('speed_kmh', 'course')
        }),
    )
    
    # Display map with OpenStreetMap
    default_center_longitude = 18.9659
    default_center_latitude = 50.2585
    default_zoom = 15
