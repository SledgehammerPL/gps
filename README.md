# GPS Tracking System - Django Version

Aplikacja Django do śledzenia GPS - konwersja z PHP do Django.

## Struktura projektu

```
project_root/
├── apps/
│   └── gps/                    # Aplikacja GPS
│       ├── __init__.py
│       ├── models.py           # Model GpsData
│       ├── views_gps_receiver.py  # Odbieranie GPS (zamiennik gps.php)
│       ├── views_history.py    # API historii (zamiennik history.php)
│       ├── urls.py             # GPS routes
│       ├── admin.py            # Panel admina
│       ├── apps.py             # Konfiguracja
│       ├── db_router.py        # Router bazy danych
│       └── migrations/
│           ├── __init__.py
│           └── 0001_initial.py
├── core/                       # Konfiguracja projektu
│   ├── __init__.py
│   ├── settings.py            # Ustawienia Django
│   ├── urls.py                # Główny routing
│   ├── wsgi.py                # WSGI
│   └── asgi.py                # ASGI
├── manage.py                   # Django CLI
├── requirements.txt            # Zależności Python
├── README.md                   # Ten plik
├── gps.php                     # Oryginał PHP (zachowany)
├── history.php                 # Oryginał PHP (zachowany)
└── gps.html                    # Frontend (działa z obiema wersjami)
```

## Pliki źródłowe (zachowane)
- `gps.php` - odbiera dane GPS z urządzeń (oryginał PHP)
- `history.php` - zwraca historię GPS z analizą ruchu (oryginał PHP)
- `gps.html` - interfejs wizualizacji z mapą (działa z obiema wersjami)

## Funkcjonalność

### 1. Odbieranie danych GPS (`apps.gps.views_gps_receiver`)
**Endpoint:** `POST /gps/`

Zastępuje `gps.php`. Odbiera surowe zdania NMEA (GGA i RMC) z urządzeń GPS.

**Parametry POST:**
- `gps_raw` - surowe zdania NMEA (oddzielone znakami nowej linii)
- `mac` - adres MAC urządzenia

**Funkcje:**
- Parsowanie zdań NMEA (GGA: pozycja i jakość, RMC: prędkość i kurs)
- Konwersja współrzędnych z formatu NMEA (DDMM.MMMM) na stopnie dziesiętne
- Filtrowanie jakości: odrzuca punkty z quality=0 lub <6 satelit
- Automatyczne tworzenie geometrii PostGIS (transformacja EPSG:4326 → 2180)
- Logowanie do pliku `gps.log`

### 2. API historii GPS (`apps.gps.views_history`)
**Endpoint:** `GET /history/`

Zastępuje `history.php`. Zwraca historię GPS z logiką zatrzymania (position hold).

**Parametry GET:**
- `threshold` (opcjonalnie, domyślnie 0.8) - próg prędkości w km/h
- `hours` (opcjonalnie, domyślnie 24) - liczba godzin wstecz

**Funkcje:**
- Złożone zapytanie SQL z funkcjami okienkowymi (LAST_VALUE, LAG)
- Logika "position hold" - jeśli prędkość < próg, używa ostatniej znanej pozycji z ruchu
- Kalkulacja dystansu między punktami (PostGIS ST_Distance)

### 3. Uproszczona wersja (Django ORM)
**Endpoint:** `GET /history/simple/`

Alternatywna wersja używająca czystego Django ORM.

## Instalacja

### 1. Zainstaluj zależności systemowe

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv
sudo apt-get install postgresql postgresql-contrib postgis
sudo apt-get install gdal-bin libgdal-dev
```

**macOS:**
```bash
brew install python postgresql postgis gdal
```

### 2. Utwórz środowisko wirtualne

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# lub
venv\Scripts\activate  # Windows
```

### 3. Zainstaluj pakiety Python

```bash
pip install -r requirements.txt
```

### 4. Konfiguracja bazy danych

```sql
CREATE DATABASE gps;
\c gps
CREATE EXTENSION postgis;

-- Użytkownicy
CREATE USER gps_receiver WITH PASSWORD 'gps_kjlsdgf';
CREATE USER gps_analytics WITH PASSWORD 'gps_kjlsdgf2';

GRANT ALL PRIVILEGES ON DATABASE gps TO gps_receiver;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO gps_analytics;
```

### 5. Uruchom migracje

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Utwórz superużytkownika (opcjonalnie)

```bash
python manage.py createsuperuser
```

### 7. Uruchom serwer

```bash
python manage.py runserver 0.0.0.0:8000
```

## Endpoints

| Endpoint | Metoda | Zastępuje | Opis |
|----------|--------|-----------|------|
| `/gps/` | POST | gps.php | Odbiera dane GPS z urządzeń |
| `/history/` | GET | history.php | Historia GPS z position hold |
| `/history/simple/` | GET | - | Uproszczona wersja (ORM) |
| `/admin/` | GET | - | Panel administracyjny Django |

## Testowanie

### Test odbierania GPS:
```bash
curl -X POST http://localhost:8000/gps/ \
  -d "mac=AA:BB:CC:DD:EE:FF" \
  -d "gps_raw=\$GPGGA,123519,5015.510,N,01857.954,E,1,08,0.9,545.4,M,46.9,M,,*47"
```

### Test historii:
```bash
curl "http://localhost:8000/history/?threshold=0.8&hours=24"
```

## Produkcja

Dla środowiska produkcyjnego:

1. Zmień `SECRET_KEY` w `core/settings.py`
2. Ustaw `DEBUG = False`
3. Skonfiguruj `ALLOWED_HOSTS`
4. Użyj Gunicorn/uWSGI
5. Skonfiguruj nginx jako reverse proxy

**Przykład z Gunicorn:**
```bash
pip install gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## Licencja

Konwersja z PHP do Django - 2025
