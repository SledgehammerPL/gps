<?php
$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

try {
    $db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
    header('Content-Type: application/json');
    
    $sql = "
        SELECT 
            timestamp, 
            player_id, 
            latitude, 
            longitude, 
            speed_kmh,
            -- Obliczamy dystans od poprzedniego punktu w metrach (układ 2180)
            ST_Distance(
                geom, 
                LAG(geom) OVER (PARTITION BY player_id ORDER BY timestamp)
            ) as step_dist
        FROM gps_data
        WHERE timestamp BETWEEN '2025-12-18 15:00:00' AND '2025-12-18 16:00:00'
          AND player_id > 0
        ORDER BY timestamp ASC
    ";
    
    $stmt = $db->query($sql);
    $results = [];
    
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        $row['geometry'] = json_decode($row['geometry']); // Dekodujemy string GeoJSON do obiektu
        $results[] = $row;
    }

    echo json_encode($results);

} catch (Exception $e) {
    echo json_encode(['error' => $e->getMessage()]);
}
