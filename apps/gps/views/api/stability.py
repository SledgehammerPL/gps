"""
GPS Stability Analysis API
Analyzes which MAC addresses are most stationary
"""
import statistics
from math import radians, cos, sin, asin, sqrt
from django.http import JsonResponse
from django.db.models import Avg
from apps.gps.models import GpsData


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS points in meters
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r


def stability(request):
    """
    Analyze GPS signal stability for each MAC address
    Returns: sorted list of MAC addresses by stability (least movement first)
    
    Query params:
    - match: Filter by match ID
    - mac: Analyze specific MAC only
    """
    query = GpsData.objects.all()
    
    match_id = request.GET.get('match')
    mac = request.GET.get('mac')
    
    if match_id:
        query = query.filter(match_id=match_id)
    
    if mac:
        query = query.filter(mac=mac)

    macs = query.values_list('mac', flat=True).distinct().order_by('mac')
    
    if not macs:
        return JsonResponse({'error': 'No GPS data found'}, status=404)

    results = []

    for mac_addr in macs:
        mac_data = query.filter(mac=mac_addr).order_by('timestamp')
        points_count = mac_data.count()
        
        if points_count < 2:
            continue

        # Calculate average position
        avg_pos = mac_data.aggregate(
            avg_lat=Avg('latitude'),
            avg_lon=Avg('longitude')
        )
        
        avg_lat = avg_pos['avg_lat']
        avg_lon = avg_pos['avg_lon']

        # Calculate distances from average
        distances = []
        for point in mac_data:
            dist = haversine_distance(
                avg_lat, avg_lon,
                point.latitude, point.longitude
            )
            distances.append(dist)

        # Calculate statistics
        avg_distance = statistics.mean(distances)
        std_dev = statistics.stdev(distances) if len(distances) > 1 else 0
        max_distance = max(distances)
        min_distance = min(distances)

        results.append({
            'mac': mac_addr,
            'points': points_count,
            'avg_distance_m': round(avg_distance, 2),
            'std_dev_m': round(std_dev, 2),
            'max_distance_m': round(max_distance, 2),
            'min_distance_m': round(min_distance, 2),
            'avg_lat': round(avg_lat, 6),
            'avg_lon': round(avg_lon, 6),
            'stability_score': 'excellent' if avg_distance < 5 else 'good' if avg_distance < 20 else 'poor'
        })

    # Sort by average distance (lowest = most stable)
    results.sort(key=lambda x: x['avg_distance_m'])

    return JsonResponse({
        'total_macs': len(results),
        'stability': results,
        'best_candidate': results[0]['mac'] if results else None
    })
