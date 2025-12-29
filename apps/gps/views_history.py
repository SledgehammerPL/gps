"""
GPS History API View
Converted from history.php

This view provides historical GPS data with movement analysis,
including position hold logic for stationary periods.
Uses Django ORM for all queries.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import timedelta
from .models import GpsData
import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points on Earth in meters using Haversine formula.
    """
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


@require_GET
def get_gps_history(request):
    """
    Get GPS history with movement analysis using Django ORM.
    
    Returns JSON array with:
    - timestamp
    - player_id
    - latitude (with hold logic)
    - longitude (with hold logic)
    - speed_kmh (zeroed when below threshold)
    - step_dist (distance from previous point in meters)
    
    Query parameters:
        threshold: Speed threshold in km/h (default: 0.8)
        hours: Number of hours to look back (default: 24)
    """
    threshold = float(request.GET.get('threshold', 0.8))
    hours = int(request.GET.get('hours', 24))
    
    try:
        # Get data from last N hours using ORM
        time_limit = timezone.now() - timedelta(hours=hours)
        
        gps_records = GpsData.objects.filter(
            player_id__gt=0,
            quality__gt=0,
            timestamp__gt=time_limit
        ).order_by('player_id', 'timestamp').values(
            'timestamp', 'player_id', 'latitude', 'longitude', 'speed_kmh'
        )
        
        # Apply position hold logic in Python
        results = []
        last_moving_pos = {}  # Track last position when moving by player_id
        prev_record = {}  # Track previous record for distance calculation
        
        for record in gps_records:
            player_id = record['player_id']
            speed = float(record['speed_kmh']) if record['speed_kmh'] else 0.0
            lat = float(record['latitude'])
            lon = float(record['longitude'])
            timestamp = record['timestamp']
            
            # Position hold logic: use last moving position if currently stationary
            if speed >= threshold:
                # Moving - update last known position
                last_moving_pos[player_id] = (lat, lon)
                display_lat, display_lon = lat, lon
            else:
                # Stationary - use last known moving position if available
                if player_id in last_moving_pos:
                    display_lat, display_lon = last_moving_pos[player_id]
                else:
                    display_lat, display_lon = lat, lon
            
            # Calculate distance from previous point
            step_dist = 0.0
            prev_key = (player_id, timestamp)
            if prev_key in prev_record and speed >= threshold:
                prev_lat, prev_lon = prev_record[prev_key]
                step_dist = haversine_distance(prev_lat, prev_lon, display_lat, display_lon)
            
            # Store previous position for next iteration
            prev_record[(player_id, timestamp)] = (display_lat, display_lon)
            
            results.append({
                'timestamp': timestamp.isoformat(),
                'player_id': player_id,
                'latitude': round(display_lat, 6),
                'longitude': round(display_lon, 6),
                'speed_kmh': round(speed, 2) if speed >= threshold else 0.0,
                'step_dist': round(step_dist, 2)
            })
        
        return JsonResponse(results, safe=False)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_GET
def get_simple_history(request):
    """
    Simplified history endpoint without position hold logic.
    Returns raw GPS data filtered by parameters.
    
    Query parameters:
        threshold: Speed threshold in km/h (default: 0.8)
        hours: Number of hours to look back (default: 24)
    """
    threshold = float(request.GET.get('threshold', 0.8))
    hours = int(request.GET.get('hours', 24))
    
    # Get data from last N hours
    time_limit = timezone.now() - timedelta(hours=hours)
    
    gps_data = GpsData.objects.filter(
        player_id__gt=0,
        quality__gt=0,
        timestamp__gt=time_limit
    ).order_by('timestamp').values(
        'timestamp', 'player_id', 'latitude', 'longitude', 'speed_kmh'
    )
    
    # Convert to list and format
    results = []
    for item in gps_data:
        speed = float(item['speed_kmh']) if item['speed_kmh'] else 0.0
        results.append({
            'timestamp': item['timestamp'].isoformat(),
            'player_id': item['player_id'],
            'latitude': round(float(item['latitude']), 6),
            'longitude': round(float(item['longitude']), 6),
            'speed_kmh': round(speed, 2) if speed >= threshold else 0.0,
            'step_dist': 0.0
        })
    
    return JsonResponse(results, safe=False)
