"""
URL Configuration for GPS Application
GPS-specific routes
"""
from django.urls import path
from . import views

app_name = 'gps'

urlpatterns = [
    # GPS data receiver endpoint (POST)
    # Replaces: gps.php
    # Usage: POST to /gps/ with params: gps_raw, mac
    path('gps/', views.receive_gps_data, name='receive_gps_data'),
    
    # GPS history API endpoint (GET)
    # Replaces: history.php
    # Usage: GET /history/ or /history/?threshold=0.8&hours=24
    path('history/', views.get_gps_history, name='gps_history'),
    
    # Alternative simple history endpoint (Django ORM only)
    # Usage: GET /history/simple/
    path('history/simple/', views.get_simple_history, name='simple_history'),
]
