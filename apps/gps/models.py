"""
GPS Data Models for Django
Converted from PHP PostgreSQL/PostGIS schema
"""
from django.contrib.gis.db import models
from django.utils import timezone


class Match(models.Model):
    """
    Match/Tournament model
    """
    id = models.AutoField(primary_key=True)
    date = models.DateField(db_index=True, help_text="Match date")
    description = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'match'
        ordering = ['-date']
    
    def __str__(self):
        return f"Match {self.date}"


class Player(models.Model):
    """
    Player model with personal data
    """
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    number = models.IntegerField(help_text="Player number")
    
    class Meta:
        db_table = 'player'
        ordering = ['number']
        unique_together = ('first_name', 'last_name', 'number')
    
    def __str__(self):
        return f"{self.number}. {self.first_name} {self.last_name}"


class MacAssignment(models.Model):
    """
    Mapping between MAC address, Player, and Match
    Allows same MAC to be assigned to different players on different matches
    """
    id = models.AutoField(primary_key=True)
    mac = models.CharField(max_length=50, db_index=True)
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name='mac_assignments')
    match = models.ForeignKey(Match, on_delete=models.PROTECT, related_name='mac_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mac_assignment'
        unique_together = ('mac', 'match')  # One MAC per match
        ordering = ['-match__date']
    
    def __str__(self):
        return f"{self.mac} -> {self.player} @ {self.match}"


class GpsData(models.Model):
    """
    GPS data model storing location and movement information
    Equivalent to gps_data table in PostgreSQL
    """
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(db_index=True)
    mac = models.CharField(max_length=50, db_index=True, help_text="Device MAC address")
    
    # Foreign keys - optional (can be null if MAC not yet assigned to player/match)
    match = models.ForeignKey(Match, on_delete=models.SET_NULL, null=True, blank=True, related_name='gps_data')
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='gps_data')
    
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
            models.Index(fields=['player']),
            models.Index(fields=['match']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        player_str = f"[{self.player.number}] {self.player}" if self.player else self.mac
        return f"GPS {player_str} @ {self.timestamp} ({self.latitude}, {self.longitude})"
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically create geometry point from lat/lon
        Transforms from WGS84 (EPSG:4326) to PUWG 1992 (EPSG:2180)
        Also auto-assign player/match based on MAC assignment
        """
        from django.contrib.gis.geos import Point
        
        # Auto-assign player and match based on MAC and timestamp
        if self.mac and not self.player and not self.match:
            try:
                # Find match based on GPS timestamp date
                match_date = self.timestamp.date()
                # Try to find assignment for this MAC on this match date
                assignment = MacAssignment.objects.filter(
                    mac=self.mac,
                    match__date=match_date
                ).first()
                
                if assignment:
                    self.player = assignment.player
                    self.match = assignment.match
            except:
                pass  # Silent fail - player/match might be assigned later
        
        # Create geometry point
        if self.latitude and self.longitude:
            # Create point in WGS84 (4326)
            point = Point(self.longitude, self.latitude, srid=4326)
            # Transform to EPSG:2180
            point.transform(2180)
            self.geom = point
        
        super().save(*args, **kwargs)
