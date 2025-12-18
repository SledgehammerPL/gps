<?php
$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

$db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
header('Content-Type: application/json');

// Pobieramy dane wygładzone średnią kroczącą
$sql = "
    WITH Smoothed AS (
        SELECT 
            timestamp, 
            player_id, 
            -- Wygładzanie pozycji (średnia z 5 próbek - 0.5 sekundy)
            AVG(latitude) OVER (PARTITION BY player_id ORDER BY timestamp ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) as lat,
            AVG(longitude) OVER (PARTITION BY player_id ORDER BY timestamp ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING) as lon,
            speed_kmh
        FROM gps_data
        WHERE player_id > 0 
          AND timestamp BETWEEN '2025-12-18 15:00:00' AND NOW()
          AND quality > 0
    )
    SELECT 
        timestamp, 
        player_id, 
        lat as latitude, 
        lon as longitude, 
        speed_kmh,
        ST_Distance(
            ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 2180),
            LAG(ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 2180)) 
            OVER (PARTITION BY player_id ORDER BY timestamp ASC)
        ) as step_dist
    FROM Smoothed
    ORDER BY timestamp ASC
";

$stmt = $db->query($sql);
echo json_encode($stmt->fetchAll(PDO::FETCH_ASSOC));
