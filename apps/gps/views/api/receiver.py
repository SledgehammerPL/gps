"""
GPS Data Receiver API
Converted from gps.php

This view receives GPS data from devices via POST requests,
parses NMEA sentences (GGA and RMC), and stores them in the database.
"""
import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from ...functions import convert_to_decimal
from ...models import GpsData

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
