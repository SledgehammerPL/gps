<?php
$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

try {
    $db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
    header('Content-Type: application/json');

    // 1. Pobieramy uśrednioną pozycję referencyjną stacji bazowej (nasze "0,0" na mapie)
    $refSql = "SELECT AVG(latitude) as ref_lat, AVG(longitude) as ref_lon 
               FROM gps_data WHERE player_id = 0 AND quality > 0";
    $refPos = $db->query($refSql)->fetch(PDO::FETCH_ASSOC);
    $refLat = (float)$refPos['ref_lat'];
    $refLon = (float)$refPos['ref_lon'];

    // 2. SQL z korekcją co 0.1s
    $sql = "
        WITH BaseError AS (
            -- Wyliczamy błąd dla każdej klatki czasu 10Hz
            SELECT 
                timestamp,
                (latitude - :refLat) as lat_offset,
                (longitude - :refLon) as lon_offset
            FROM gps_data
            WHERE player_id = 0
        ),
        CorrectedData AS (
            -- Nakładamy błąd bazy na pozycje zawodników
            SELECT 
                g.timestamp, 
                g.player_id,
                (g.latitude - COALESCE(be.lat_offset, 0)) as c_lat,
                (g.longitude - COALESCE(be.lon_offset, 0)) as c_lon,
                g.speed_kmh,
                -- Tworzymy geometrię w układzie 2180 dla precyzyjnych metrów
                ST_Transform(ST_SetSRID(ST_MakePoint(
                    g.longitude - COALESCE(be.lon_offset, 0), 
                    g.latitude - COALESCE(be.lat_offset, 0)
                ), 4326), 2180) as c_geom
            FROM gps_data g
            LEFT JOIN BaseError be ON g.timestamp = be.timestamp
            WHERE g.player_id > 0 
              AND g.timestamp BETWEEN '2025-12-18 15:44:00' AND NOW()
        )
        SELECT 
            timestamp, 
            player_id,
            c_lat as latitude,
            c_lon as longitude,
            speed_kmh,
            -- Liczymy dystans między skorygowanymi punktami
            ST_Distance(
                c_geom, 
                LAG(c_geom) OVER (PARTITION BY player_id ORDER BY timestamp ASC)
            ) as step_dist
        FROM CorrectedData
        ORDER BY timestamp ASC
    ";

    $stmt = $db->prepare($sql);
    $stmt->execute([':refLat' => $refLat, ':refLon' => $refLon]);
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode($rows);

} catch (Exception $e) {
    echo json_encode(['error' => $e->getMessage()]);
}
