"""
GPS History API
Converted from history.php

Provides endpoints for retrieving GPS tracking history with position hold logic.
"""
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from ...functions import haversine_distance
from ...models import GpsData


@require_GET
def get_gps_history(request):
    """
    Get GPS history with movement analysis using Django ORM.
    """
    try:
        threshold = float(request.GET.get('threshold', 0.8))
        hours = int(request.GET.get('hours', 24))
    except (ValueError, TypeError):
        threshold = 0.8
        hours = 24
    
    try:
        # Get data from last N hours using ORM
        time_limit = timezone.now() - timedelta(hours=hours)
        
        gps_records = GpsData.objects.filter(
            quality__gt=0,
            timestamp__gt=time_limit
        ).order_by('timestamp').values(
            'timestamp', 'mac', 'latitude', 'longitude', 'speed_kmh'
        )
        
        # Convert to list and format response
        results = []
        for record in gps_records:
            speed = float(record['speed_kmh']) if record['speed_kmh'] else 0.0
            results.append({
                'timestamp': record['timestamp'].isoformat(),
                'mac': record['mac'],
                'latitude': round(float(record['latitude']), 6),
                'longitude': round(float(record['longitude']), 6),
                'speed_kmh': round(speed, 2) if speed >= threshold else 0.0,
                'step_dist': 0.0
            })
        
        return JsonResponse(results, safe=False)
        
    except Exception as e:
        import traceback
        print(f"[ERROR] get_gps_history: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'type': type(e).__name__
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
        quality__gt=0,
        timestamp__gt=time_limit
    ).order_by('timestamp').values(
        'timestamp', 'mac', 'latitude', 'longitude', 'speed_kmh'
    )
    
    # Convert to list and format
    results = []
    for item in gps_data:
        speed = float(item['speed_kmh']) if item['speed_kmh'] else 0.0
        results.append({
            'timestamp': item['timestamp'].isoformat(),
            'mac': item['mac'],
            'latitude': round(float(item['latitude']), 6),
            'longitude': round(float(item['longitude']), 6),
            'speed_kmh': round(speed, 2) if speed >= threshold else 0.0,
            'step_dist': 0.0
        })
    
    return JsonResponse(results, safe=False)
