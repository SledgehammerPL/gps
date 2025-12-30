"""
GPS Data Models for Django
Converted from PHP PostgreSQL/PostGIS schema
"""
from django.contrib.gis.db import models
from django.utils import timezone


class GpsData(models.Model):
    """
    GPS data model storing location and movement information
    Equivalent to gps_data table in PostgreSQL
    """
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(db_index=True)
    mac = models.CharField(max_length=50, db_index=True, help_text="Device MAC address")
    
    # GPS coordinates
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField(default=0.0)
    
    # GPS quality metrics
    num_satellites = models.IntegerField(default=0, help_text="Number of satellites")
    hdop = models.FloatField(default=0.0, help_text="Horizontal Dilution of Precision")
    quality = models.IntegerField(default=0, help_text="GPS fix quality (0=invalid, 1=GPS fix, 2=DGPS fix)")
    
    # Movement data
    speed_kmh = models.FloatField(default=0.0, help_text="Speed in km/h")
    course = models.FloatField(default=0.0, help_text="Course over ground in degrees")
    
    class Meta:
        db_table = 'gps_data'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['mac']),
            models.Index(fields=['quality']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"GPS[{self.mac}] @ {self.timestamp} ({self.latitude}, {self.longitude})"
