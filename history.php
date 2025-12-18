<?php


$host = 'localhost';
$dbname = 'gps';
$user = 'gps_analytics';
$pass = 'gps_kjlsdgf2';

$db = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);

header('Content-Type: application/json');

$sql = "
  SELECT id, timestamp, player_id, latitude, longitude
  FROM gps_data
  WHERE timestamp BETWEEN '2025-12-17 17:21:24' AND NOW()
  ORDER BY timestamp ASC
";
$stmt = $db->query($sql);
$rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

echo json_encode($rows, JSON_UNESCAPED_UNICODE);
