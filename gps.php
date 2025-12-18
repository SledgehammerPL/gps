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

// POPRAWIONA FUNKCJA KONWERSJI
function convertToDecimal($coord_str, $hemisphere) {
    if (empty($coord_str) || (float)$coord_str == 0) return false;
    
    // NMEA format: DDMM.MMMM (dla Latitude) lub DDDMM.MMMM (dla Longitude)
    // Musimy odciąć ostatnie 2 cyfry minut przed kropką
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
                $buffer[$time]['lat'] = convertToDecimal($parts[2], $parts[3]);
                $buffer[$time]['lon'] = convertToDecimal($parts[4], $parts[5]);
                $buffer[$time]['qual'] = (int)$parts[6];
                $buffer[$time]['sats'] = (int)$parts[7];
                $buffer[$time]['hdop'] = (float)$parts[8];
                $buffer[$time]['alt'] = (float)$parts[9];
            } 
            elseif ($type === 'RMC' && count($parts) >= 10) {
                $buffer[$time]['speed'] = (float)$parts[7] * 1.852;
                $buffer[$time]['course'] = (float)$parts[8]; // Dodane!
                $buffer[$time]['date'] = $parts[9];
                if (!isset($buffer[$time]['lat']) || $buffer[$time]['lat'] === false) {
                    $buffer[$time]['lat'] = convertToDecimal($parts[3], $parts[4]);
                    $buffer[$time]['lon'] = convertToDecimal($parts[5], $parts[6]);
                }
            }
        }

        // SQL MA 10 PARAMETRÓW (łącznie z :course)
        $sql = "INSERT INTO gps_data (
                    timestamp, player_id, latitude, longitude, altitude, 
                    num_satellites, hdop, speed_kmh, course, quality, geom
                ) VALUES (
                    :ts, :pid, :lat, :lon, :alt, :sats, :hdop, :speed, :course, :qual,
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 2180)
                )";
        
        $stmt = $pdo->prepare($sql);

        foreach ($buffer as $time => $row) {
            if (!isset($row['lat']) || $row['lat'] === false || empty($row['date'])) continue;

            $d = $row['date'];
            $fullTs = "20".substr($d,4,2)."-".substr($d,2,2)."-".substr($d,0,2)." ".
                      substr($time,0,2).":".substr($time,2,2).":".substr($time,4);

            // PEŁNA LISTA 10 PARAMETRÓW
            $params = [
                ':ts'     => $fullTs,
                ':pid'    => $row['player_id'],
                ':lat'    => $row['lat'],
                ':lon'    => $row['lon'],
                ':alt'    => $row['alt'] ?? 0,
                ':sats'   => $row['sats'] ?? 0,
                ':hdop'   => $row['hdop'] ?? 0,
                ':speed'  => $row['speed'] ?? 0,
                ':course' => $row['course'] ?? 0, // Teraz jest w komplecie!
                ':qual'   => $row['qual'] ?? 0
            ];

            try {
                $stmt->execute($params);
            } catch (PDOException $e) {
                logToFile("BŁĄD SQL: " . $e->getMessage());
                logToFile("WYSŁANO: " . json_encode($params));
            }
        }
    } catch (Exception $e) {
        logToFile("BŁĄD KRYTYCZNY: " . $e->getMessage());
    }
}
?>
