"""
Django Admin Configuration for GPS Application
"""
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from .models import Match, Player, MacAssignment, GpsData


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'description']
    list_filter = ['date']
    search_fields = ['description']
    date_hierarchy = 'date'


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['number', 'first_name', 'last_name']
    list_filter = ['number']
    search_fields = ['first_name', 'last_name', 'number']
    ordering = ['number']


@admin.register(MacAssignment)
class MacAssignmentAdmin(admin.ModelAdmin):
    list_display = ['mac', 'player', 'match', 'assigned_at']
    list_filter = ['match__date', 'assigned_at']
    search_fields = ['mac', 'player__first_name', 'player__last_name']
    readonly_fields = ['assigned_at']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('mac', 'player', 'match')
        }),
        ('Metadata', {
            'fields': ('assigned_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(GpsData)
class GpsDataAdmin(OSMGeoAdmin):
    """
    Admin interface for GPS data with map display
    """
    list_display = ['id', 'timestamp', 'player', 'mac', 'latitude', 'longitude', 
                    'speed_kmh', 'num_satellites', 'quality']
    list_filter = ['quality', 'timestamp', 'player', 'match']
    search_fields = ['mac', 'player__first_name', 'player__last_name']
    date_hierarchy = 'timestamp'
    readonly_fields = ['geom']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('timestamp', 'mac', 'player', 'match')
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
