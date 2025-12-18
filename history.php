<?php
$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

$db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
header('Content-Type: application/json');

// Definiujemy próg Static Hold: 1.0 km/h (możesz zmienić na 0.7 lub 1.2 w zależności od testów)
$staticHoldThreshold = 1.0;

$sql = "
    WITH RawData AS (
        SELECT 
            timestamp, 
            player_id, 
            latitude, 
            longitude, 
            speed_kmh,
            -- Pobieramy poprzednią pozycję do porównania
            LAG(latitude) OVER (PARTITION BY player_id ORDER BY timestamp) as prev_lat,
            LAG(longitude) OVER (PARTITION BY player_id ORDER BY timestamp) as prev_lon
        FROM gps_data
        WHERE player_id > 0 AND quality > 0
          AND timestamp BETWEEN '2025-12-18 15:44:00' AND NOW()
    ),
    StaticHold AS (
        SELECT 
            timestamp,
            player_id,
            -- LOGIKA STATIC HOLD:
            -- Jeśli prędkość jest poniżej progu, użyj poprzedniej szerokości, w przeciwnym razie nowej
            CASE 
                WHEN speed_kmh < :threshold AND prev_lat IS NOT NULL THEN prev_lat 
                ELSE latitude 
            END as c_lat,
            CASE 
                WHEN speed_kmh < :threshold AND prev_lon IS NOT NULL THEN prev_lon 
                ELSE longitude 
            END as c_lon,
            CASE WHEN speed_kmh < :threshold THEN 0 ELSE speed_kmh END as c_speed
        FROM RawData
    )
    SELECT 
        timestamp, 
        player_id, 
        c_lat as latitude, 
        c_lon as longitude, 
        c_speed as speed_kmh,
        -- Dystans liczymy tylko gdy nie trzymamy pozycji
        CASE 
            WHEN c_speed > 0 THEN 
                ST_Distance(
                    ST_Transform(ST_SetSRID(ST_MakePoint(c_lon, c_lat), 4326), 2180),
                    LAG(ST_Transform(ST_SetSRID(ST_MakePoint(c_lon, c_lat), 4326), 2180)) 
                    OVER (PARTITION BY player_id ORDER BY timestamp ASC)
                )
            ELSE 0 
        END as step_dist
    FROM StaticHold
    ORDER BY timestamp ASC
";

$stmt = $db->prepare($sql);
$stmt->execute([':threshold' => $staticHoldThreshold]);
echo json_encode($stmt->fetchAll(PDO::FETCH_ASSOC));
