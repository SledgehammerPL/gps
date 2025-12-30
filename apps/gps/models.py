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
    
    # PostGIS geometry field - POINT in EPSG:2180 (Polish coordinate system)
    geom = models.PointField(srid=2180, null=True, blank=True)
    
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
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically create geometry point from lat/lon
        Transforms from WGS84 (EPSG:4326) to PUWG 1992 (EPSG:2180)
        """
        from django.contrib.gis.geos import Point
        
        if self.latitude and self.longitude:
            # Create point in WGS84 (4326)
            point = Point(self.longitude, self.latitude, srid=4326)
            # Transform to EPSG:2180
            point.transform(2180)
            self.geom = point
        
        super().save(*args, **kwargs)
