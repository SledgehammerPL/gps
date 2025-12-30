"""
GPS Map Web Views
Renders web interface for GPS visualization
"""
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def gps_map_view(request):
    """
    Render GPS tracking map interface
    """
    return render(request, 'gps/map.html')
