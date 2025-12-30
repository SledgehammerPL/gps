"""
Management command to analyze GPS signal stability by MAC address
Helps identify stationary base station candidates
"""
import statistics
from math import radians, cos, sin, asin, sqrt
from django.core.management.base import BaseCommand
from django.db.models import Avg
from apps.gps.models import GpsData


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS points in meters
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r


class Command(BaseCommand):
    help = 'Analyze GPS signal stability for each MAC address'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mac',
            type=str,
            help='Analyze specific MAC address',
        )
        parser.add_argument(
            '--match',
            type=int,
            help='Filter by match ID',
        )

    def handle(self, *args, **options):
        query = GpsData.objects.all()
        
        if options['match']:
            query = query.filter(match_id=options['match'])
        
        if options['mac']:
            query = query.filter(mac=options['mac'])

        # Get unique MAC addresses
        macs = query.values_list('mac', flat=True).distinct().order_by('mac')
        
        if not macs:
            self.stdout.write(self.style.WARNING('No GPS data found'))
            return

        results = []

        for mac in macs:
            mac_data = query.filter(mac=mac).order_by('timestamp')
            points_count = mac_data.count()
            
            if points_count < 2:
                continue

            # Calculate average position
            avg_pos = mac_data.aggregate(
                avg_lat=Avg('latitude'),
                avg_lon=Avg('longitude')
            )
            
            avg_lat = avg_pos['avg_lat']
            avg_lon = avg_pos['avg_lon']

            # Calculate distances from average
            distances = []
            for point in mac_data:
                dist = haversine_distance(
                    avg_lat, avg_lon,
                    point.latitude, point.longitude
                )
                distances.append(dist)

            # Calculate statistics
            avg_distance = statistics.mean(distances)
            std_dev = statistics.stdev(distances) if len(distances) > 1 else 0
            max_distance = max(distances)
            min_distance = min(distances)

            results.append({
                'mac': mac,
                'points': points_count,
                'avg_dist_m': avg_distance,
                'std_dev_m': std_dev,
                'max_dist_m': max_distance,
                'min_dist_m': min_distance,
                'avg_lat': avg_lat,
                'avg_lon': avg_lon,
            })

        # Sort by average distance (lowest = most stable)
        results.sort(key=lambda x: x['avg_dist_m'])

        # Display results
        self.stdout.write(self.style.SUCCESS('\n=== GPS Signal Stability Analysis ===\n'))
        
        for i, result in enumerate(results, 1):
            stability_score = '🟢' if result['avg_dist_m'] < 5 else '🟡' if result['avg_dist_m'] < 20 else '🔴'
            
            self.stdout.write(
                f"{i}. {stability_score} MAC: {result['mac']}"
            )
            self.stdout.write(f"   Points: {result['points']}")
            self.stdout.write(f"   Avg distance from center: {result['avg_dist_m']:.2f}m")
            self.stdout.write(f"   Std deviation: {result['std_dev_m']:.2f}m")
            self.stdout.write(f"   Range: {result['min_distance_m']:.2f}m - {result['max_dist_m']:.2f}m")
            self.stdout.write(f"   Center position: ({result['avg_lat']:.6f}, {result['avg_lon']:.6f})")
            self.stdout.write("")

        if results:
            best = results[0]
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Most stable (base candidate): {best['mac']} "
                    f"({best['avg_dist_m']:.2f}m avg deviation)\n"
                )
            )
