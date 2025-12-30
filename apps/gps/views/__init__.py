"""
GPS Views Package
Provides web and API views for GPS tracking system
"""
# Import API views
from .api.receiver import receive_gps_data
from .api.history import get_gps_history, get_simple_history

# Import web views
from .web.map import gps_map_view

# Export all views for backward compatibility
__all__ = [
    # API endpoints
    'receive_gps_data',
    'get_gps_history',
    'get_simple_history',
    
    # Web views
    'gps_map_view',
]
