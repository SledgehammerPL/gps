"""
GPS Helper Functions
Utility functions for GPS data processing
"""
import math


def convert_to_decimal(coord_str, hemisphere):
    """
    Convert GPS coordinates from NMEA format (DDMM.MMMM) to decimal degrees
    
    Args:
        coord_str: Coordinate string in NMEA format
        hemisphere: N/S for latitude, E/W for longitude
    
    Returns:
        Decimal degrees or False if invalid
    """
    if not coord_str or float(coord_str) == 0:
        return False
    
    try:
        dot_pos = coord_str.find('.')
        if dot_pos == -1:
            return False
        
        # Extract minutes (last 2 digits before decimal + decimal part)
        minutes_part = coord_str[dot_pos - 2:]
        # Extract degrees (everything before minutes)
        degrees_part = coord_str[:dot_pos - 2]
        
        decimal = float(degrees_part) + (float(minutes_part) / 60)
        
        # Apply hemisphere (S and W are negative)
        if hemisphere in ['S', 'W']:
            decimal *= -1
        
        return decimal
    except (ValueError, IndexError):
        return False


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

