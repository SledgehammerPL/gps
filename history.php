<?php
$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

$db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
header('Content-Type: application/json');

$sql = "
    SELECT 
        timestamp, 
        player_id,
        latitude, 
        longitude, 
        speed_kmh,
        ST_Distance(
            geom, 
            LAG(geom) OVER (PARTITION BY player_id ORDER BY timestamp ASC)
        ) as step_dist
    FROM gps_data
    WHERE player_id > 0 
      AND timestamp BETWEEN '2025-12-18 15:44:00' AND NOW()
      AND quality > 0
    ORDER BY timestamp ASC
";

$stmt = $db->query($sql);
echo json_encode($stmt->fetchAll(PDO::FETCH_ASSOC));
