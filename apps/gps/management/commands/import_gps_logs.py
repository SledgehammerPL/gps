"""
Management command to import GPS data from log files.
Parses log format: INFO 2026-01-09 17:23:54,551 receiver 3866476 ... [INCOMING] RAW GPS: $GNRMC,...
"""
import re
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.gps.models import GpsData, Match
from apps.gps.functions import convert_to_decimal


class Command(BaseCommand):
    help = 'Import GPS data from log files'

    def add_arguments(self, parser):
        parser.add_argument('logfile', type=str, help='Path to the log file')
        parser.add_argument(
            '--match-date',
            type=str,
            help='Match date (YYYY-MM-DD). If not provided, uses date from log.'
        )

    def handle(self, *args, **options):
        logfile = options['logfile']
        match_date = options.get('match_date')
        
        try:
            with open(logfile, 'r') as f:
                self.process_logfile(f, match_date)
        except FileNotFoundError:
            raise CommandError(f'Log file not found: {logfile}')

    def process_logfile(self, logfile, match_date):
        """Process log file and import GPS data"""
        
        # Patterns for MAC and RAW GPS lines
        mac_pattern = re.compile(
            r'INFO (\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2}),(\d{3}) '
            r'receiver \d+ .* \[INCOMING\] MAC: ([A-F0-9:]+)'
        )
        gps_pattern = re.compile(
            r'INFO (\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2}),(\d{3}) '
            r'receiver \d+ .* \[INCOMING\] RAW GPS: (\$[A-Z]+.*)'
        )
        
        imported = 0
        skipped = 0
        errors = 0
        current_mac = None
        
        for line_num, line in enumerate(logfile, 1):
            # Check for MAC line
            mac_match = mac_pattern.search(line)
            if mac_match:
                current_mac = mac_match.group(6)
                continue
            
            # Check for GPS line
            gps_match = gps_pattern.search(line)
            if gps_match:
                log_date = gps_match.group(1)
                hour = int(gps_match.group(2))
                minute = int(gps_match.group(3))
                second = int(gps_match.group(4))
                millisecond = int(gps_match.group(5))
                sentence = gps_match.group(6).strip()
                
                # Use current_mac if available, otherwise skip
                if not current_mac:
                    skipped += 1
                    continue
                
                use_date = match_date if match_date else log_date
                
                try:
                    gps_record = self.parse_gnss_sentence(
                        sentence, use_date, hour, minute, second,
                        millisecond, current_mac
                    )
                    
                    if gps_record:
                        self.save_gps_record(gps_record, use_date)
                        imported += 1
                    else:
                        skipped += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Line {line_num} (MAC {current_mac}): {str(e)}'
                        )
                    )
                    errors += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Import complete: {imported} imported, {skipped} skipped, '
                f'{errors} errors'
            )
        )

    def parse_gnss_sentence(
        self, sentence, date_str, hour, minute, second, millisecond, mac
    ):
        """Parse GNRMC or GNGGA sentence"""
        
        parts = sentence.split(',')
        if not parts:
            return None
        
        sentence_type = parts[0]
        
        if sentence_type in ['$GNRMC', '$GPRMC']:
            return self.parse_rmc(
                parts, date_str, hour, minute, second, millisecond, mac
            )
        elif sentence_type in ['$GNGGA', '$GPGGA']:
            return self.parse_gga(
                parts, date_str, hour, minute, second, millisecond, mac
            )
        
        return None

    def parse_rmc(self, parts, date_str, hour, minute, second, millisecond, mac):
        """
        Parse GNRMC sentence format:
        $GNRMC,162352.800,A,5016.611174,N,01903.767172,E,2.44,163.88,090126,,,D,V*03
        """
        if len(parts) < 10:
            return None
        
        try:
            status = parts[2]  # A = active
            if status != 'A':
                return None
            
            lat_str = parts[3]
            lat_hem = parts[4]
            lon_str = parts[5]
            lon_hem = parts[6]
            speed_knots = float(parts[7]) if parts[7] else 0.0
            
            latitude = convert_to_decimal(lat_str, lat_hem)
            longitude = convert_to_decimal(lon_str, lon_hem)
            
            if latitude is False or longitude is False:
                return None
            
            # Convert knots to km/h
            speed_kmh = speed_knots * 1.852
            
            # Parse date from DDMMYY format
            date_from_sentence = parts[9]
            if date_from_sentence and len(date_from_sentence) == 6:
                day = int(date_from_sentence[0:2])
                month = int(date_from_sentence[2:4])
                year = int(date_from_sentence[4:6])
                use_date = f'20{year:02d}-{month:02d}-{day:02d}'
            else:
                use_date = date_str
            
            return {
                'mac': mac,
                'date': use_date,
                'hour': hour,
                'minute': minute,
                'second': second,
                'millisecond': millisecond,
                'latitude': latitude,
                'longitude': longitude,
                'speed_kmh': speed_kmh,
                'quality': 1  # GPS fix
            }
        except (ValueError, IndexError):
            return None

    def parse_gga(self, parts, date_str, hour, minute, second, millisecond, mac):
        """
        Parse GNGGA sentence format:
        $GNGGA,162358.800,5016.598964,N,01903.764094,E,2,31,0.49,267.240,M,42.101,M,,*70
        """
        if len(parts) < 10:
            return None
        
        try:
            lat_str = parts[2]
            lat_hem = parts[3]
            lon_str = parts[4]
            lon_hem = parts[5]
            fix_quality = int(parts[6]) if parts[6] else 0
            
            if fix_quality == 0:
                return None
            
            latitude = convert_to_decimal(lat_str, lat_hem)
            longitude = convert_to_decimal(lon_str, lon_hem)
            
            if latitude is False or longitude is False:
                return None
            
            return {
                'mac': mac,
                'date': date_str,
                'hour': hour,
                'minute': minute,
                'second': second,
                'millisecond': millisecond,
                'latitude': latitude,
                'longitude': longitude,
                'speed_kmh': 0.0,  # GGA doesn't have speed
                'quality': fix_quality
            }
        except (ValueError, IndexError):
            return None

    def save_gps_record(self, record, match_date_str):
        """Save GPS record to database"""
        try:
            # Find or create match for this date
            match_date = datetime.strptime(match_date_str, '%Y-%m-%d').date()
            match, created = Match.objects.get_or_create(date=match_date)
            
            # Construct timestamp
            timestamp = datetime(
                year=int(match_date_str.split('-')[0]),
                month=int(match_date_str.split('-')[1]),
                day=int(match_date_str.split('-')[2]),
                hour=record['hour'],
                minute=record['minute'],
                second=record['second'],
                microsecond=record['millisecond'] * 1000
            )
            
            # Make timezone-aware
            timestamp = timezone.make_aware(timestamp)
            
            # Check if already exists
            existing = GpsData.objects.filter(
                mac=record['mac'],
                timestamp=timestamp
            ).exists()
            
            if not existing:
                GpsData.objects.create(
                    match=match,
                    mac=record['mac'],
                    timestamp=timestamp,
                    latitude=record['latitude'],
                    longitude=record['longitude'],
                    speed_kmh=record['speed_kmh'],
                    quality=record['quality']
                )
        except Exception as e:
            raise Exception(f'Error saving record: {str(e)}')
