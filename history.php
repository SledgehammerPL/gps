<?php
$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

try {
    $db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
    header('Content-Type: application/json');

    // 1. Obliczamy stały punkt odniesienia dla BAZY (średnia z jej logów)
    $refSql = "SELECT AVG(latitude) as ref_lat, AVG(longitude) as ref_lon 
               FROM gps_data WHERE player_id = 0 AND quality > 0";
    $refPos = $db->query($refSql)->fetch(PDO::FETCH_ASSOC);
    $refLat = $refPos['ref_lat'];
    $refLon = $refPos['ref_lon'];

    // 2. Pobieramy dane, korygując pozycję zawodników o błąd bazy w danym czasie
    // Używamy złączenia (JOIN), aby dopasować błąd bazy z tej samej sekundy do zawodnika
    $sql = "
        WITH BaseError AS (
            SELECT 
                timestamp,
                (latitude - :refLat) as lat_err,
                (longitude - :refLon) as lon_err
            FROM gps_data
            WHERE player_id = 0
        )
        SELECT 
            g.timestamp, 
            g.player_id,
            -- Odejmujemy błąd bazy od pozycji zawodnika
            (g.latitude - COALESCE(be.lat_err, 0)) as latitude,
            (g.longitude - COALESCE(be.lon_err, 0)) as longitude,
            g.speed_kmh,
            ST_Distance(
                ST_SetSRID(ST_MakePoint(g.longitude - COALESCE(be.lon_err, 0), g.latitude - COALESCE(be.lat_err, 0)), 4326)::geography,
                LAG(ST_SetSRID(ST_MakePoint(g.longitude - COALESCE(be.lon_err, 0), g.latitude - COALESCE(be.lat_err, 0)), 4326)::geography) 
                OVER (PARTITION BY g.player_id ORDER BY g.timestamp ASC)
            ) as step_dist
        FROM gps_data g
        LEFT JOIN BaseError be ON g.timestamp = be.timestamp
        WHERE g.player_id > 0 
          AND g.timestamp BETWEEN '2025-12-18 15:44:00' AND NOW()
          AND g.quality > 0
        ORDER BY g.timestamp ASC
    ";

    $stmt = $db->prepare($sql);
    $stmt->execute([':refLat' => $refLat, ':refLon' => $refLon]);
    echo json_encode($stmt->fetchAll(PDO::FETCH_ASSOC));

} catch (Exception $e) {
    echo json_encode(['error' => $e->getMessage()]);
}
