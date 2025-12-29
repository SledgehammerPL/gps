<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

try {
    $db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    header('Content-Type: application/json');

    $threshold = 0.8;

    $sql = "
        WITH BaseData AS (
            SELECT 
                timestamp, 
                player_id, 
                latitude, 
                longitude, 
                speed_kmh
            FROM gps_data
            WHERE player_id > 0 
              AND quality > 0
              AND timestamp > NOW() - INTERVAL '24 hours'
        ),
        HoldLogic AS (
            SELECT 
                timestamp,
                player_id,
                -- Składnia zgodna ze standardem SQL:2023 / PG 17
                -- Pobieramy ostatnią znaną pozycję z ruchu (IGNORE NULLS)
                LAST_VALUE(CASE WHEN speed_kmh >= :ts THEN latitude END) 
                    OVER (PARTITION BY player_id ORDER BY timestamp ASC 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as last_lat,
                LAST_VALUE(CASE WHEN speed_kmh >= :ts THEN longitude END) 
                    OVER (PARTITION BY player_id ORDER BY timestamp ASC 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as last_lon,
                speed_kmh,
                latitude as raw_lat,
                longitude as raw_lon
            FROM BaseData
        )
        SELECT 
            timestamp::text, 
            player_id, 
            COALESCE(last_lat, raw_lat) as latitude, 
            COALESCE(last_lon, raw_lon) as longitude, 
            CASE WHEN speed_kmh < :ts THEN 0 ELSE speed_kmh END as speed_kmh,
            -- Dystans liczony na skorygowanych punktach
            CASE 
                WHEN speed_kmh >= :ts THEN 
                    ST_Distance(
                        ST_Transform(ST_SetSRID(ST_MakePoint(COALESCE(last_lon, raw_lon), COALESCE(last_lat, raw_lat)), 4326), 2180),
                        LAG(ST_Transform(ST_SetSRID(ST_MakePoint(COALESCE(last_lon, raw_lon), COALESCE(last_lat, raw_lat)), 4326), 2180)) 
                        OVER (PARTITION BY player_id ORDER BY timestamp ASC)
                    )
                ELSE 0 
            END as step_dist
        FROM HoldLogic
        ORDER BY timestamp ASC
    ";

    $stmt = $db->prepare($sql);
    $stmt->execute([':ts' => $threshold]);
    $result = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode($result);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
