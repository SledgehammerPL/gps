const map = L.map('map', { zoomControl: true, maxZoom: 22 }).setView([50.2585, 18.9659], 21);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 19, maxZoom: 22 }).addTo(map);

// Click on map to show coordinates
map.on('click', (e) => {
    const lat = e.latlng.lat.toFixed(6);
    const lng = e.latlng.lng.toFixed(6);
    if (window.matchId) {
        const msg = `Współrzędne:\n${lat}. ${lng}\n\nUstawić jako bazę?`;
        if (confirm(msg)) {
            setBaseCoords(lat, lng);
        }
    } else {
        alert(`Współrzędne:\n${lat}. ${lng}`);
    }
});

let data = [], ticks = [], players = {}, cur = 0, playing = false, timer = null;
let loading = false;
let selectedPlayerId = null;
let heatEnabled = false;
let heatLayer = L.heatLayer([], { radius: 15, blur: 20, maxZoom: 19 }).addTo(map);

const colors = ['#ff4757', '#2ed573', '#1e90ff', '#ffa500', '#eccc68'];

// Add base station marker if coordinates exist
let baseMarker = null;
if (window.baseLatitude !== null && window.baseLongitude !== null) {
    baseMarker = L.circleMarker([window.baseLatitude, window.baseLongitude], {
        radius: 12,
        color: '#ffeb3b',
        weight: 3,
        fillColor: '#ffeb3b',
        fillOpacity: 0.8
    }).bindPopup(`Stacja Bazowa<br>${window.baseLatitude.toFixed(6)}. ${window.baseLongitude.toFixed(6)}`).addTo(map);
}

async function setBaseCoords(lat, lng) {
    try {
        const formData = new FormData();
        formData.append('match_id', window.matchId);
        formData.append('latitude', lat);
        formData.append('longitude', lng);
        
        const res = await fetch(window.updateBaseCoordsUrl, {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            const data = await res.json();
            alert(`Baza zaktualizowana:\n${data.base_latitude}. ${data.base_longitude}`);
        } else {
            alert('Błąd przy aktualizacji bazy');
        }
    } catch (e) {
        alert(`Błąd: ${e.message}`);
    }
}

async function loadHistory() {
    if (loading) return;
    loading = true;

    // Clear previous layers/UI
    Object.values(players).forEach(p => { map.removeLayer(p.m); map.removeLayer(p.t); });
    players = {};
    document.getElementById('player-list').innerHTML = '';
    heatLayer.setLatLngs([]);

    // Django URL - używamy reverse URL zamiast history.php
    const params = window.matchId ? `?match=${window.matchId}` : '';
    const res = await fetch(window.gpsHistoryUrl + params, { cache: 'no-store' });
    const raw = await res.json();
    
    // Filtr 40km/h
    data = raw.filter(d => parseFloat(d.speed_kmh) < 40);

    const groups = {};
    data.forEach(d => { 
        const ts = d.timestamp.substring(0, 19); // Wyciągnij datę i czas bez timezone
        if(!groups[ts]) groups[ts] = []; 
        groups[ts].push(d); 
    });
    ticks = Object.keys(groups).sort();
    document.getElementById('timeline').max = ticks.length - 1;
    document.getElementById('timeline').value = 0;
    cur = 0;

    const macs = [...new Set(data.map(d => d.mac))];
    macs.forEach((mac, idx) => {
        const c = colors[idx % colors.length];
        players[mac] = {
            m: L.circleMarker([0,0], {radius: 7, color: '#fff', weight: 2, fillColor: c, fillOpacity: 1}).addTo(map),
            t: L.polyline([], {color: c, weight: 3, opacity: 0.3}).addTo(map)
        };
    });
    
    // Set map center to first data point
    if (data.length > 0) {
        map.setView([data[0].latitude, data[0].longitude], 21);
    }
    
    show(0);
    loading = false;
}

function toggleHeat() {
    heatEnabled = !heatEnabled;
    const btn = document.getElementById('heatBtn');
    btn.innerText = heatEnabled ? "HEATMAPA: ON" : "HEATMAPA: OFF";
    btn.classList.toggle('on', heatEnabled);
    if(!heatEnabled) heatLayer.setLatLngs([]);
    show(cur);
}

function selectPlayer(id) {
    selectedPlayerId = id;
    document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
    if(id !== null) document.getElementById(`p-${id}`).classList.add('active');
    show(cur);
}

function show(idx) {
    cur = idx;
    const ts = ticks[idx];
    if(!ts) return;
    document.getElementById('time-val').innerText = ts.substring(11); // HH:MM:SS

    const frame = data.filter(d => d.timestamp.substring(0, 19) === ts);
    let heatPoints = [];

    // Przetwarzanie zawodników po MAC
    Object.keys(players).forEach(mac => {
        const p = players[mac];
        const pData = frame.find(d => d.mac === mac);
        const hist = data.filter(x => x.mac === mac && x.timestamp.substring(0, 19) <= ts);
        
        // Oblicz statystyki
        let dSum = 0, vMax = 0;
        hist.forEach(h => {
            dSum += parseFloat(h.step_dist || 0);
            if(parseFloat(h.speed_kmh) > vMax) vMax = parseFloat(h.speed_kmh);
        });

        if(pData) {
            p.m.setLatLng([pData.latitude, pData.longitude]);
            p.t.setLatLngs(hist.map(h => [h.latitude, h.longitude]));
            updateUI(mac, parseFloat(pData.speed_kmh), vMax, dSum);
            
            // Ukrywanie/Pokazywanie markerów w zależności od wyboru
            if(selectedPlayerId === null || selectedPlayerId === mac) {
                p.m.setStyle({opacity: 1, fillOpacity: 1});
                p.t.setStyle({opacity: 0.3});
            } else {
                p.m.setStyle({opacity: 0, fillOpacity: 0});
                p.t.setStyle({opacity: 0});
            }
        }

        // Dodawanie do heatmapy (tylko wybrany lub wszyscy)
        if(heatEnabled) {
            if(selectedPlayerId === null || selectedPlayerId === mac) {
                hist.forEach(h => heatPoints.push([h.latitude, h.longitude, 0.5]));
            }
        }
    });

    if(heatEnabled) heatLayer.setLatLngs(heatPoints);
}

function updateUI(mac, v, vm, d) {
    let el = document.getElementById(`p-${mac}`);
    if(!el) {
        el = document.createElement('div'); el.id = `p-${mac}`; el.className = 'card';
        el.onclick = () => selectPlayer(mac);
        const idx = Object.keys(players).indexOf(mac);
        el.style.borderLeftColor = colors[idx % colors.length];
        document.getElementById('player-list').appendChild(el);
    }
    el.innerHTML = `
        <div style="display:flex; justify-content:space-between"><strong>${mac}</strong> <span class="v-curr">${v.toFixed(1)} <small>km/h</small></span></div>
        <div class="grid">
            <div><div class="label">Dystans</div><div class="val" style="color:#2ed573">${d.toFixed(2)} m</div></div>
            <div><div class="label">V-Max</div><div class="val" style="color:#ff4757">${vm.toFixed(1)} km/h</div></div>
        </div>`;
}

async function togglePlay() {
    if (playing) {
        playing = false;
        document.getElementById('btnPlay').innerText = 'ODTWÓRZ';
        clearInterval(timer);
        return;
    }

    // Load history only if data is empty (first time)
    if (data.length === 0) {
        await loadHistory();
    }

    playing = true;
    document.getElementById('btnPlay').innerText = 'PAUZA';
    timer = setInterval(() => {
        if(cur < ticks.length - 1) {
            show(cur + 1);
            document.getElementById('timeline').value = cur;
        } else {
            togglePlay();
        }
    }, 100 / document.getElementById('speed').value);
}

document.getElementById('timeline').oninput = (e) => { 
    if(playing) togglePlay(); 
    show(parseInt(e.target.value)); 
};
loadHistory();
