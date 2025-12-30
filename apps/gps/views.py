"""
GPS Data Receiver View
Converted from gps.php

This view receives GPS data from devices via POST requests,
parses NMEA sentences (GGA and RMC), and stores them in the database.
"""
import logging
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .functions import convert_to_decimal, haversine_distance
from .models import GpsData

# Configure logging
logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def receive_gps_data(request):
    """
    Receive and process GPS data from devices
    
    POST parameters:
        gps_raw: Raw NMEA sentences (newline separated)
        mac: Device MAC address
    
    Returns:
        JSON response with status
    """
    gps_raw = request.POST.get('gps_raw', '')
    mac = request.POST.get('mac', '')
    
    if not gps_raw or not mac:
        return JsonResponse({
            'status': 'error',
            'message': 'Missing gps_raw or mac parameter'
        }, status=400)
    
    logger.info(f"PLAYER {mac} - zgłosił się")
    
    lines = gps_raw.strip().split('\n')
    buffer = {}
    
    # Parse NMEA sentences
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) < 2:
            continue
        
        # Extract sentence type (GGA or RMC)
        sentence_type = parts[0][3:6] if len(parts[0]) >= 6 else ''
        time = parts[1]
        
        if not time:
            continue
        
        # Initialize buffer entry
        if time not in buffer:
            buffer[time] = {'mac': mac}
        
        # Parse GGA sentence (position and quality)
        if sentence_type == 'GGA' and len(parts) >= 10:
            buffer[time]['lat'] = convert_to_decimal(parts[2], parts[3])
            buffer[time]['lon'] = convert_to_decimal(parts[4], parts[5])
            buffer[time]['qual'] = int(parts[6]) if parts[6] else 0
            buffer[time]['sats'] = int(parts[7]) if parts[7] else 0
            buffer[time]['hdop'] = float(parts[8]) if parts[8] else 0.0
            buffer[time]['alt'] = float(parts[9]) if parts[9] else 0.0
        
        # Parse RMC sentence (speed, course, date)
        elif sentence_type == 'RMC' and len(parts) >= 10:
            # Convert speed from knots to km/h (1 knot = 1.852 km/h)
            buffer[time]['speed'] = float(parts[7]) * 1.852 if parts[7] else 0.0
            buffer[time]['course'] = float(parts[8]) if parts[8] else 0.0
            buffer[time]['date'] = parts[9]
            
            # Use RMC position if GGA not available
            if 'lat' not in buffer[time] or buffer[time]['lat'] is False:
                buffer[time]['lat'] = convert_to_decimal(parts[3], parts[4])
                buffer[time]['lon'] = convert_to_decimal(parts[5], parts[6])
    
    # Insert valid records into database
    inserted_count = 0
    
    for time, row in buffer.items():
        # Quality filter: skip if no coordinates, quality 0, or less than 6 satellites
        quality = row.get('qual', 0)
        sats = row.get('sats', 0)
        lat = row.get('lat', False)
        date_str = row.get('date', '')
        
        if lat is False or quality == 0 or sats < 6 or not date_str:
            continue
        
        try:
            # Parse date and time
            # Date format: DDMMYY, Time format: HHMMSS
            day = date_str[0:2]
            month = date_str[2:4]
            year = f"20{date_str[4:6]}"
            hour = time[0:2]
            minute = time[2:4]
            second = time[4:6] if len(time) >= 6 else '00'
            
            timestamp_str = f"{year}-{month}-{day} {hour}:{minute}:{second}"
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            # Create GPS data record
            gps_data = GpsData(
                timestamp=timestamp,
                mac=mac,
                latitude=float(row['lat']),
                longitude=float(row['lon']),
                altitude=row.get('alt', 0.0),
                num_satellites=sats,
                hdop=row.get('hdop', 0.0),
                speed_kmh=row.get('speed', 0.0),
                course=row.get('course', 0.0),
                quality=quality
            )
            gps_data.save()
            inserted_count += 1
            
        except Exception as e:
            logger.error(f"Error inserting GPS record: {e}")
            continue
    
    if inserted_count > 0:
        logger.info(f"PLAYER {mac}: Wstawiono {inserted_count} czystych rekordów (Sats >= 6).")
    
    return JsonResponse({
        'status': 'success',
        'inserted': inserted_count
    })


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
