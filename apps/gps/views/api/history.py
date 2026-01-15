"""
GPS History API
Converted from history.php

Provides endpoints for retrieving GPS tracking history with position hold logic.
"""
from collections import defaultdict
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
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

        # Group records by timestamp (tick) with 0.1s precision
        ticks = defaultdict(list)
        for rec in gps_records:
            # Round to 0.1s precision
            ts = rec['timestamp']
            tick_key = ts.replace(microsecond=(ts.microsecond // 100000) * 100000)
            ticks[tick_key].append(rec)
        
        # Process ticks in chronological order with base correction
        corrected_records = []
        if match and match.base_mac and match.base_latitude is not None and match.base_longitude is not None:
            base_mac = match.base_mac
            base_lat = float(match.base_latitude)
            base_lon = float(match.base_longitude)
            
            print(f"[DEBUG] Base correction enabled: MAC={base_mac}, Lat={base_lat}, Lon={base_lon}")
            
            for tick_key in sorted(ticks.keys()):
                tick_records = ticks[tick_key]
                
                # Find base_mac in this tick
                base_record = None
                for rec in tick_records:
                    if rec['mac'] == base_mac:
                        base_record = rec
                        break
                
                # If no base_mac in this tick, skip it
                if not base_record:
                    continue
                
                # Calculate correction: difference between base_mac position and known base coordinates
                base_rec_lat = float(base_record['latitude'])
                base_rec_lon = float(base_record['longitude'])
                correction_lat = base_lat - base_rec_lat
                correction_lon = base_lon - base_rec_lon
                
                # Apply correction to all records in this tick
                for rec in tick_records:
                    original_lat = float(rec['latitude'])
                    original_lon = float(rec['longitude'])
                    rec['latitude'] = original_lat + correction_lat
                    rec['longitude'] = original_lon + correction_lon
                    corrected_records.append(rec)
        else:
            # No base correction, flatten all ticks
            print(f"[DEBUG] No base correction - match: {match}, base_mac: {match.base_mac if match else None}")
            for tick_key in sorted(ticks.keys()):
                corrected_records.extend(ticks[tick_key])
        
        gps_records = corrected_records
        
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

    # Group records by timestamp (tick) with 0.1s precision
    ticks = defaultdict(list)
    for rec in gps_data:
        # Round to 0.1s precision
        ts = rec['timestamp']
        tick_key = ts.replace(microsecond=(ts.microsecond // 100000) * 100000)
        ticks[tick_key].append(rec)
    
    # Process ticks in chronological order with base correction
    corrected_records = []
    if match and match.base_mac and match.base_latitude is not None and match.base_longitude is not None:
        base_mac = match.base_mac
        base_lat = float(match.base_latitude)
        base_lon = float(match.base_longitude)
        
        print(f"[DEBUG simple] Base correction enabled: MAC={base_mac}, Lat={base_lat}, Lon={base_lon}")
        
        for tick_key in sorted(ticks.keys()):
            tick_records = ticks[tick_key]
            
            # Find base_mac in this tick
            base_record = None
            for rec in tick_records:
                if rec['mac'] == base_mac:
                    base_record = rec
                    break
            
            # If no base_mac in this tick, skip it
            if not base_record:
                continue
            
            # Calculate correction: difference between base_mac position and known base coordinates
            base_rec_lat = float(base_record['latitude'])
            base_rec_lon = float(base_record['longitude'])
            correction_lat = base_lat - base_rec_lat
            correction_lon = base_lon - base_rec_lon
            
            # Apply correction to all records in this tick
            for rec in tick_records:
                original_lat = float(rec['latitude'])
                original_lon = float(rec['longitude'])
                rec['latitude'] = original_lat + correction_lat
                rec['longitude'] = original_lon + correction_lon
                corrected_records.append(rec)
    else:
        # No base correction, flatten all ticks
        print(f"[DEBUG simple] No base correction - match: {match}, base_mac: {match.base_mac if match else None}")
        for tick_key in sorted(ticks.keys()):
            corrected_records.extend(ticks[tick_key])
    
    gps_data = corrected_records
    
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
