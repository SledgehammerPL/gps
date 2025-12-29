# Generated migration file for GpsData model
# This is an example - run "python manage.py makemigrations" to generate actual migrations

from django.contrib.gis.db import models
from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GpsData',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(db_index=True)),
                ('mac', models.CharField(db_index=True, help_text='Device MAC address', max_length=50)),
                ('player_id', models.IntegerField(db_index=True, default=0, help_text='Player identifier')),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('altitude', models.FloatField(default=0.0)),
                ('num_satellites', models.IntegerField(default=0, help_text='Number of satellites')),
                ('hdop', models.FloatField(default=0.0, help_text='Horizontal Dilution of Precision')),
                ('quality', models.IntegerField(default=0, help_text='GPS fix quality (0=invalid, 1=GPS fix, 2=DGPS fix)')),
                ('speed_kmh', models.FloatField(default=0.0, help_text='Speed in km/h')),
                ('course', models.FloatField(default=0.0, help_text='Course over ground in degrees')),
                ('geom', models.PointField(blank=True, null=True, srid=2180)),
            ],
            options={
                'db_table': 'gps_data',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='gpsdata',
            index=models.Index(fields=['timestamp'], name='gps_data_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='gpsdata',
            index=models.Index(fields=['mac'], name='gps_data_mac_idx'),
        ),
        migrations.AddIndex(
            model_name='gpsdata',
            index=models.Index(fields=['player_id'], name='gps_data_player_idx'),
        ),
        migrations.AddIndex(
            model_name='gpsdata',
            index=models.Index(fields=['quality'], name='gps_data_quality_idx'),
        ),
    ]
