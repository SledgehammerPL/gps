"""
Base Station Coordinates API
Handles updating base station location
"""
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from ...models import Match


@csrf_exempt
@require_POST
def update_base_coords(request):
    """
    Update base station coordinates for a match.
    
    POST parameters:
        match_id: Match ID (required)
        latitude: Base station latitude (required)
        longitude: Base station longitude (required)
    """
    try:
        match_id = request.POST.get('match_id')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if not match_id or latitude is None or longitude is None:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        match = Match.objects.get(id=match_id)
        match.base_latitude = float(latitude)
        match.base_longitude = float(longitude)
        match.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Base coordinates updated',
            'base_latitude': match.base_latitude,
            'base_longitude': match.base_longitude
        })
    
    except Match.DoesNotExist:
        return JsonResponse({'error': 'Match not found'}, status=404)
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid coordinates: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
