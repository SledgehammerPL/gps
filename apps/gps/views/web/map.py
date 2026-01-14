"""
GPS Map Web Views
Renders web interface for GPS visualization
"""
from django.shortcuts import render
from django.http import Http404
from django.views.decorators.http import require_GET
from apps.gps.models import Match


@require_GET
def gps_map_view(request):
    """
    Render GPS tracking map interface
    Accepts optional ?match=<id> to filter map data to a specific match date
    """
    match_id = request.GET.get('match')
    context = {}

    if match_id:
        try:
            match = Match.objects.get(id=match_id)
            context['match_id'] = match.id
            context['match_date'] = match.date.isoformat()
            context['base_mac'] = match.base_mac or ''
            context['base_latitude'] = match.base_latitude
            context['base_longitude'] = match.base_longitude
        except Match.DoesNotExist:
            raise Http404("Match not found")

    return render(request, 'gps/map.html', context)
