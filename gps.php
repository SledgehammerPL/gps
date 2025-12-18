<?php
    $logFile = 'gps.log';

// Funkcja do konwersji współrzędnych z formatu DDMM.MMMM na stopnie dziesiętne
function convertToDecimal($coord_str, $hemisphere) {
    global $logFile;
    // Rozdzielenie ciągu względem kropki
//    $decimal = (float)$coord_str /100;

    list($degrees_minutes, $fractional) = explode('.', $coord_str, 2);

    // Oddzielenie stopni od minut
    $degrees = (int)substr($degrees_minutes, 0, -2);
    $minutes = (float)(substr($degrees_minutes, -2).'.'.$fractional) / 60;

    // Konwersja minut na stopnie dziesiętne
    $decimal = $degrees + $minutes; 

    // Uwzględnij hemisferę (N/S lub E/W)
    if ($hemisphere === 'S' || $hemisphere === 'W') {
        $decimal *= -1;
    }

    file_put_contents($logFile, "$coord_str $hemisphere -> $decimal\n", FILE_APPEND);
    return $decimal;
}

// Funkcja do konwersji znacznika czasu z formatu hhmmss.ss na TIMESTAMP
function convertToTimestamp($time_str) {
    // Zakłada, że znacznikiem czasu są godziny, minuty, sekundy (hhmmss.ss)
    $hour = substr($time_str, 0, 2);
    $minute = substr($time_str, 2, 2);
    $second = substr($time_str, 4, 2);
    $fraction = substr($time_str, 7, 2); // Używamy tylko pierwszych 2 cyfr ułamkowych
    global $logFile;
    file_put_contents($logFile, "$time_str\n", FILE_APPEND);

    // Użyj obecnej daty i podstaw znacznik czasu
    $date = date('Y-m-d'); // Możesz dostosować datę według potrzeby
    return "{$date} {$hour}:{$minute}:{$second}.{$fraction}+00";
}


function parseGpsData($nmeaString) {
    $parts = explode(',', $nmeaString);
    $type = substr($parts[0], 3, 3); // np. GGA, RMC
    
    if ($type === 'GGA') {
        if (count($parts) < 14) {
            throw new Exception('Nieprawidłowy format GGA. count '.count($parts));
        }
        return [
            'timestamp' => $parts[1],
            'latitude'  => convertToDecimal($parts[2], $parts[3]),
            'longitude' => convertToDecimal($parts[4], $parts[5]),
            'quality'   => (int)$parts[6],
            'numSatellites' => (int)$parts[7],
            'hdop'      => (float)$parts[8],
            'altitude'  => (float)$parts[9],
            'altitudeUnit' => $parts[10],
            'geoidSeparation' => (float)$parts[11],
            'geoidSeparationUnit' => $parts[12],
            'ageOfDifferential' => $parts[13],
            'checksum'  => $parts[14] ?? null
        ];
    }

    if ($type === 'RMC') {
        if (count($parts) < 11) {
            throw new Exception('Nieprawidłowy format RMC. count '.count($parts));
        }
        return [
            'timestamp' => $parts[1],
            'status'    => $parts[2], // A=active, V=void
            'latitude'  => convertToDecimal($parts[3], $parts[4]),
            'longitude' => convertToDecimal($parts[5], $parts[6]),
            'speedKnots'=> (float)$parts[7],
            'course'    => (float)$parts[8],
            'date'      => $parts[9],
            'mode'      => $parts[12] ?? null,
            'checksum'  => end($parts)
        ];
    }

    throw new Exception('Nieobsługiwany typ ramki: '.$parts[0]);
}

$host = 'localhost';
$dbname = 'gps';
$user = 'gps_receiver';
$pass = 'gps_kjlsdgf';

if (isset($_POST['gps_raw']) && isset($_POST['player_id'])) {
    $player_id = $_POST['player_id'];
    $gps_data = $_POST['gps_raw'];

    $lines = explode("\n", trim($gps_data));

    try {
        $pdo = new PDO("pgsql:host=$host;dbname=$dbname", $user, $pass);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '') continue;
            
            try {
#                file_put_contents($logFile, "\nramka od playera $player_id\n", FILE_APPEND);
                $parsedData = parseGpsData($line);

                $timestamp = convertToTimestamp($parsedData['timestamp']);

                $sql = "INSERT INTO gps_data (
                          timestamp, player_id, latitude, longitude, altitude, altitude_unit,
                          geoid_separation, geoid_separation_unit, age_of_differential, num_satellites,
                          geom
                        ) VALUES (
                          :timestamp, :player_id, :latitude, :longitude, :altitude, :altitude_unit,
                          :geoid_separation, :geoid_separation_unit, :age_of_differential, :num_satellites,
                          ST_Transform(ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), 2180)
                        )";

                $stmt = $pdo->prepare($sql);
                $stmt->bindParam(':timestamp', $timestamp);
                $stmt->bindParam(':player_id', $player_id);
                $stmt->bindParam(':latitude', $parsedData['latitude']);
                $stmt->bindParam(':longitude', $parsedData['longitude']);
                $stmt->bindParam(':altitude', $parsedData['altitude']);
                $stmt->bindParam(':altitude_unit', $parsedData['altitudeUnit']);
                $stmt->bindParam(':geoid_separation', $parsedData['geoidSeparation']);
                $stmt->bindParam(':geoid_separation_unit', $parsedData['geoidSeparationUnit']);
                $stmt->bindParam(':age_of_differential', $parsedData['ageOfDifferential']);
                $stmt->bindParam(':num_satellites', $parsedData['numSatellites']);

                $stmt->execute();

                #$report .= "Wstawiono ramkę: $line\n";
            } catch (Exception $e) {
                $report .= "Błąd parsowania: ".$e->getMessage()." dla linii: $line\n";
            }
        }
    } catch (PDOException $e) {
        $report .= "Błąd połączenia: ".$e->getMessage()."\n";
    }
} else {
    $report .= "Missing data. Please provide lat, lon, and player_id.\n";
    $report .= serialize($_POST);
}
file_put_contents($logFile, $report, FILE_APPEND);

