"""
URL Configuration for GPS Application
GPS-specific routes
"""
from django.urls import path
from .views.web import gps_map_view
from .views.api import receive_gps_data, get_gps_history, get_simple_history, stability

app_name = 'gps'

urlpatterns = [
    # GPS Map visualization (main page)
    # Usage: GET / - renders GPS tracking map
    path('', gps_map_view, name='gps_map'),
    
    # GPS data receiver endpoint (POST)
    # Replaces: gps.php
    # Usage: POST to /gps/ with params: gps_raw, mac
    path('gps/', receive_gps_data, name='receive_gps_data'),
    
    # GPS history API endpoint (GET)
    # Replaces: history.php
    # Usage: GET /history/ or /history/?threshold=0.8&hours=24
    path('history/', get_gps_history, name='gps_history'),
    
    # Alternative simple history endpoint (Django ORM only)
    # Usage: GET /history/simple/
    path('history/simple/', get_simple_history, name='simple_history'),
    
    # GPS Signal Stability Analysis
    # Usage: GET /stability/ or /stability/?match=1&mac=D8F15B0A3E69
    path('stability/', stability, name='stability'),
]
