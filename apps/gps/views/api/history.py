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
from ...models import GpsData, Match


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

    match_id = request.GET.get('match')
    match = None
    if match_id:
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return JsonResponse({'error': 'Match not found'}, status=404)
    
    try:
        # Get data from last N hours using ORM
        time_limit = timezone.now() - timedelta(hours=hours)
        
        gps_query = GpsData.objects.filter(quality__gt=0)

        if match:
            gps_query = gps_query.filter(timestamp__date=match.date)
        else:
            gps_query = gps_query.filter(timestamp__gt=time_limit)
        
        gps_records = list(gps_query.order_by('timestamp').values(
            'timestamp', 'mac', 'latitude', 'longitude', 'speed_kmh'
        ))

        def smooth_three_point(records):
            """
            Three-point moving average per device:
            - 1st point: raw
            - 2nd point: avg of first two
            - 3rd+ points: avg of last three raw points (i, i-1, i-2)
            """
            by_mac = {}
            for rec in records:
                by_mac.setdefault(rec['mac'], []).append(rec)

            smoothed = []
            for recs in by_mac.values():
                recs.sort(key=lambda r: r['timestamp'])
                window = []
                for rec in recs:
                    window.append(rec)
                    if len(window) > 3:
                        window.pop(0)

                    lat_avg = sum(float(r['latitude']) for r in window) / len(window)
                    lon_avg = sum(float(r['longitude']) for r in window) / len(window)

                    new_rec = rec.copy()
                    new_rec['latitude'] = lat_avg
                    new_rec['longitude'] = lon_avg
                    smoothed.append(new_rec)

            return sorted(smoothed, key=lambda r: r['timestamp'])

        # Base-station correction: keep base_mac fixed, apply its drift delta to all points at same timestamp
        if match and match.base_mac:
            base_mac = match.base_mac
            base_points = [r for r in gps_records if r['mac'] == base_mac]
            if base_points:
                ref_lat = sum(float(p['latitude']) for p in base_points) / len(base_points)
                ref_lon = sum(float(p['longitude']) for p in base_points) / len(base_points)
                # Build per-timestamp delta for base
                base_deltas = {}
                for p in base_points:
                    ts_key = p['timestamp']  # datetime with microseconds
                    base_deltas[ts_key] = (
                        float(p['latitude']) - ref_lat,
                        float(p['longitude']) - ref_lon,
                    )
                # Apply correction using exact timestamps (microsecond precision)
                for rec in gps_records:
                    ts_key = rec['timestamp']
                    delta = base_deltas.get(ts_key)
                    if delta:
                        dlat, dlon = delta
                        rec['latitude'] = float(rec['latitude']) - dlat
                        rec['longitude'] = float(rec['longitude']) - dlon

        # Smooth positions per device (3-point moving average)
        gps_records = smooth_three_point(gps_records)
        
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
        hours: Number of hours to look back (default: 24) if match not set
        match: Match ID to filter by match date
    """
    threshold = float(request.GET.get('threshold', 0.8))
    hours = int(request.GET.get('hours', 24))
    match_id = request.GET.get('match')
    match = None
    if match_id:
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return JsonResponse({'error': 'Match not found'}, status=404)
    
    # Get data from last N hours or match date
    time_limit = timezone.now() - timedelta(hours=hours)
    gps_query = GpsData.objects.filter(quality__gt=0)
    if match:
        gps_query = gps_query.filter(timestamp__date=match.date)
    else:
        gps_query = gps_query.filter(timestamp__gt=time_limit)
    
    gps_data = list(gps_query.order_by('timestamp').values(
        'timestamp', 'mac', 'latitude', 'longitude', 'speed_kmh'
    ))

    # Base-station correction when match and base_mac present
    if match and match.base_mac:
        base_mac = match.base_mac
        base_points = [r for r in gps_data if r['mac'] == base_mac]
        if base_points:
            ref_lat = sum(float(p['latitude']) for p in base_points) / len(base_points)
            ref_lon = sum(float(p['longitude']) for p in base_points) / len(base_points)
            base_deltas = {}
            for p in base_points:
                ts_key = p['timestamp']  # datetime with microseconds
                base_deltas[ts_key] = (
                    float(p['latitude']) - ref_lat,
                    float(p['longitude']) - ref_lon,
                )
            for rec in gps_data:
                ts_key = rec['timestamp']
                delta = base_deltas.get(ts_key)
                if delta:
                    dlat, dlon = delta
                    rec['latitude'] = float(rec['latitude']) - dlat
                    rec['longitude'] = float(rec['longitude']) - dlon
    
    # Convert to list and format
    results = []
    for item in gps_data:
        speed = float(item['speed_kmh']) if item['speed_kmh'] else 0.0
        results.append({
            'timestamp': item['timestamp'].isoformat(),
            'mac': item['mac'],
            'latitude': float(item['latitude']),
            'longitude': float(item['longitude']),
            'speed_kmh': round(speed, 2) if speed >= threshold else 0.0,
            'step_dist': 0.0
        })
    
    return JsonResponse(results, safe=False)
