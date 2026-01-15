"""
GPS History API
Converted from history.php

Provides endpoints for retrieving GPS tracking history with position hold logic.
"""
import logging
from collections import defaultdict
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from ...models import GpsData, Match

logger = logging.getLogger(__name__)


@require_GET
def get_gps_history(request):
    """
    Get GPS history with movement analysis using Django ORM.
    """
    logger.info(f"[DEBUG] get_gps_history called with params: {request.GET.dict()}")
    
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
            logger.info(f"[DEBUG] Match found: {match.id}, base_mac={match.base_mac}")
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

        # Build correction map if we have base_mac and base coordinates
        corrections_by_tick = {}
        if match and match.base_mac and match.base_latitude is not None and match.base_longitude is not None:
            base_mac = match.base_mac
            base_lat = float(match.base_latitude)
            base_lon = float(match.base_longitude)
            
            logger.info(f"[DEBUG] Building correction map: base_mac={base_mac}")
            
            # Step 1: Get all base_mac points and group by tick (0.1s precision)
            base_points = [r for r in gps_records if r['mac'] == base_mac]
            logger.info(f"[DEBUG] Found {len(base_points)} base_mac points")
            
            base_ticks = defaultdict(list)
            for rec in base_points:
                ts = rec['timestamp']
                tick_key = ts.replace(microsecond=(ts.microsecond // 100000) * 100000)
                base_ticks[tick_key].append(rec)
            
            # Step 2: Calculate correction for each tick with base_mac data
            for tick_key in sorted(base_ticks.keys()):
                tick_recs = base_ticks[tick_key]
                avg_lat = sum(float(r['latitude']) for r in tick_recs) / len(tick_recs)
                avg_lon = sum(float(r['longitude']) for r in tick_recs) / len(tick_recs)
                
                correction_lat = base_lat - avg_lat
                correction_lon = base_lon - avg_lon
                
                corrections_by_tick[tick_key] = {
                    'lat': correction_lat,
                    'lon': correction_lon
                }
            
            logger.info(f"[DEBUG] Calculated corrections for {len(corrections_by_tick)} ticks")
            
            # Step 3: Interpolate missing corrections
            if corrections_by_tick:
                sorted_ticks = sorted(corrections_by_tick.keys())
                
                for i in range(len(sorted_ticks) - 1):
                    curr_tick = sorted_ticks[i]
                    next_tick = sorted_ticks[i + 1]
                    
                    # Calculate how many ticks are between current and next
                    tick_diff = (next_tick - curr_tick).total_seconds()
                    num_gaps = int(tick_diff / 0.1) - 1
                    
                    if num_gaps > 0:
                        curr_corr = corrections_by_tick[curr_tick]
                        next_corr = corrections_by_tick[next_tick]
                        
                        if num_gaps == 1:
                            # Single gap: average
                            mid_tick = curr_tick + (next_tick - curr_tick) / 2
                            corrections_by_tick[mid_tick] = {
                                'lat': (curr_corr['lat'] + next_corr['lat']) / 2,
                                'lon': (curr_corr['lon'] + next_corr['lon']) / 2
                            }
                        else:
                            # Multiple gaps: linear interpolation
                            for gap_idx in range(1, num_gaps + 1):
                                fraction = gap_idx / (num_gaps + 1)
                                gap_tick = curr_tick + (next_tick - curr_tick) * fraction
                                corrections_by_tick[gap_tick] = {
                                    'lat': curr_corr['lat'] + (next_corr['lat'] - curr_corr['lat']) * fraction,
                                    'lon': curr_corr['lon'] + (next_corr['lon'] - curr_corr['lon']) * fraction
                                }
                
                logger.info(f"[DEBUG] After interpolation: {len(corrections_by_tick)} corrections available")
            
            # Step 4: Apply corrections to all records
            corrected_records = []
            for rec in gps_records:
                ts = rec['timestamp']
                tick_key = ts.replace(microsecond=(ts.microsecond // 100000) * 100000)
                
                if tick_key in corrections_by_tick:
                    correction = corrections_by_tick[tick_key]
                    rec['latitude'] = float(rec['latitude']) + correction['lat']
                    rec['longitude'] = float(rec['longitude']) + correction['lon']
                
                corrected_records.append(rec)
            
            gps_records = corrected_records
            logger.info("[DEBUG] Applied corrections to all records")
        
        # Filter by threshold
        gps_records = [
            rec for rec in gps_records
            if (rec['timestamp'].microsecond // 100000) % 1 == 0
        ]
        
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
        
        if results:
            logger.info(f"[DEBUG] First result: {results[0]}")
            logger.info(f"[DEBUG] Total results: {len(results)}")
        
        return JsonResponse(results, safe=False)
        
    except Exception as e:
        import traceback
        logger.error(f"[ERROR] get_gps_history: {e}")
        logger.error(traceback.format_exc())
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

    # Build correction map if we have base_mac and base coordinates
    corrections_by_tick = {}
    if match and match.base_mac and match.base_latitude is not None and match.base_longitude is not None:
        base_mac = match.base_mac
        base_lat = float(match.base_latitude)
        base_lon = float(match.base_longitude)
        
        logger.info(f"[DEBUG simple] Building correction map: base_mac={base_mac}")
        
        # Step 1: Get all base_mac points and group by tick (0.1s precision)
        base_points = [r for r in gps_data if r['mac'] == base_mac]
        logger.info(f"[DEBUG simple] Found {len(base_points)} base_mac points")
        
        base_ticks = defaultdict(list)
        for rec in base_points:
            ts = rec['timestamp']
            tick_key = ts.replace(microsecond=(ts.microsecond // 100000) * 100000)
            base_ticks[tick_key].append(rec)
        
        # Step 2: Calculate correction for each tick with base_mac data
        for tick_key in sorted(base_ticks.keys()):
            tick_recs = base_ticks[tick_key]
            avg_lat = sum(float(r['latitude']) for r in tick_recs) / len(tick_recs)
            avg_lon = sum(float(r['longitude']) for r in tick_recs) / len(tick_recs)
            
            correction_lat = base_lat - avg_lat
            correction_lon = base_lon - avg_lon
            
            corrections_by_tick[tick_key] = {
                'lat': correction_lat,
                'lon': correction_lon
            }
        
        logger.info(f"[DEBUG simple] Calculated corrections for {len(corrections_by_tick)} ticks")
        
        # Step 3: Interpolate missing corrections
        if corrections_by_tick:
            sorted_ticks = sorted(corrections_by_tick.keys())
            
            for i in range(len(sorted_ticks) - 1):
                curr_tick = sorted_ticks[i]
                next_tick = sorted_ticks[i + 1]
                
                # Calculate how many ticks are between current and next
                tick_diff = (next_tick - curr_tick).total_seconds()
                num_gaps = int(tick_diff / 0.1) - 1
                
                if num_gaps > 0:
                    curr_corr = corrections_by_tick[curr_tick]
                    next_corr = corrections_by_tick[next_tick]
                    
                    if num_gaps == 1:
                        # Single gap: average
                        mid_tick = curr_tick + (next_tick - curr_tick) / 2
                        corrections_by_tick[mid_tick] = {
                            'lat': (curr_corr['lat'] + next_corr['lat']) / 2,
                            'lon': (curr_corr['lon'] + next_corr['lon']) / 2
                        }
                    else:
                        # Multiple gaps: linear interpolation
                        for gap_idx in range(1, num_gaps + 1):
                            fraction = gap_idx / (num_gaps + 1)
                            gap_tick = curr_tick + (next_tick - curr_tick) * fraction
                            corrections_by_tick[gap_tick] = {
                                'lat': curr_corr['lat'] + (next_corr['lat'] - curr_corr['lat']) * fraction,
                                'lon': curr_corr['lon'] + (next_corr['lon'] - curr_corr['lon']) * fraction
                            }
            
            logger.info(f"[DEBUG simple] After interpolation: {len(corrections_by_tick)} corrections available")
        
        # Step 4: Apply corrections to all records
        corrected_records = []
        for rec in gps_data:
            ts = rec['timestamp']
            tick_key = ts.replace(microsecond=(ts.microsecond // 100000) * 100000)
            
            if tick_key in corrections_by_tick:
                correction = corrections_by_tick[tick_key]
                rec['latitude'] = float(rec['latitude']) + correction['lat']
                rec['longitude'] = float(rec['longitude']) + correction['lon']
            
            corrected_records.append(rec)
        
        gps_data = corrected_records
        logger.info("[DEBUG simple] Applied corrections to all records")
    
    # Filter by threshold
    gps_data = [
        rec for rec in gps_data
        if (rec['timestamp'].microsecond // 100000) % 1 == 0
    ]
    
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
