<?php
$host = 'localhost';
$dbname = 'gps';
$user = 'gps_receiver';
$pass = 'gps_kjlsdgf';
$logFile = __DIR__ . '/gps.log';

function logToFile($message) {
    global $logFile;
    $date = date('Y-m-d H:i:s');
    file_put_contents($logFile, "[$date] $message\n", FILE_APPEND);
}

function convertToDecimal($coord_str, $hemisphere) {
    if (empty($coord_str) || (float)$coord_str == 0) return false;
    $dotPos = strpos($coord_str, '.');
    if ($dotPos === false) return false;
    $minutes_part = substr($coord_str, $dotPos - 2);
    $degrees_part = substr($coord_str, 0, $dotPos - 2);
    $decimal = (float)$degrees_part + ((float)$minutes_part / 60);
    return ($hemisphere === 'S' || $hemisphere === 'W') ? $decimal * -1 : $decimal;
}

if (isset($_POST['gps_raw']) && isset($_POST['player_id'])) {
    $player_id = (int)$_POST['player_id'];
    $lines = explode("\n", trim($_POST['gps_raw']));
    
    try {
        $pdo = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $buffer = [];

        foreach ($lines as $line) {
            $parts = explode(',', trim($line));
            if (count($parts) < 2) continue;
            
            $type = substr($parts[0], 3, 3);
            $time = $parts[1];

            if (!isset($buffer[$time])) $buffer[$time] = ['player_id' => $player_id];

            if ($type === 'GGA' && count($parts) >= 10) {
                $buffer[$time]['lat']   = convertToDecimal($parts[2], $parts[3]);
                $buffer[$time]['lon']   = convertToDecimal($parts[4], $parts[5]);
                $buffer[$time]['qual']  = (int)$parts[6];
                $buffer[$time]['sats']  = (int)$parts[7];
                $buffer[$time]['hdop']  = (float)$parts[8];
                $buffer[$time]['alt']   = (float)$parts[9];
            } 
            elseif ($type === 'RMC' && count($parts) >= 10) {
                $buffer[$time]['speed']  = (float)$parts[7] * 1.852;
                $buffer[$time]['course'] = (float)$parts[8];
                $buffer[$time]['date']   = $parts[9];
                if (!isset($buffer[$time]['lat']) || $buffer[$time]['lat'] === false) {
                    $buffer[$time]['lat'] = convertToDecimal($parts[3], $parts[4]);
                    $buffer[$time]['lon'] = convertToDecimal($parts[5], $parts[6]);
                }
            }
        }

        $sql = "INSERT INTO gps_data (
                    timestamp, player_id, latitude, longitude, altitude, 
                    num_satellites, hdop, speed_kmh, course, quality, geom
                ) VALUES (
                    :ts, :pid, :lat, :lon, :alt, :sats, :hdop, :speed, :course, :qual,
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 2180)
                )";
        
        $stmt = $pdo->prepare($sql);
        $insertedCount = 0;

        foreach ($buffer as $time => $row) {
            // --- FILTR JAKOŚCI ---
            $quality = (int)($row['qual'] ?? 0);
            $sats    = (int)($row['sats'] ?? 0);
            $lat     = $row['lat'] ?? false;

            // Odrzucamy jeśli: brak współrzędnych LUB jakość 0 LUB mniej niż 6 satelitów
            if ($lat === false || $quality === 0 || $sats < 6 || empty($row['date'])) {
                continue; 
            }

            $d = $row['date'];
            $fullTs = "20".substr($d,4,2)."-".substr($d,2,2)."-".substr($d,0,2)." ".
                      substr($time,0,2).":".substr($time,2,2).":".substr($time,4);

            $stmt->execute([
                ':ts'     => $fullTs,
                ':pid'    => (int)$row['player_id'],
                ':lat'    => (float)$row['lat'],
                ':lon'    => (float)$row['lon'],
                ':alt'    => (float)($row['alt'] ?? 0),
                ':sats'   => $sats,
                ':hdop'   => (float)($row['hdop'] ?? 0),
                ':speed'  => (float)($row['speed'] ?? 0),
                ':course' => (float)($row['course'] ?? 0),
                ':qual'   => $quality
            ]);
            $insertedCount++;
        }
        
        // Logujemy tylko jeśli faktycznie coś wpadło, żeby nie śmiecić w logu przy braku fixa
        if ($insertedCount > 0) {
            logToFile("PLAYER $player_id: Wstawiono $insertedCount czystych rekordów (Sats >= 6).");
        }

    } catch (Exception $e) {
        logToFile("BŁĄD: " . $e->getMessage());
    }
}
?>
