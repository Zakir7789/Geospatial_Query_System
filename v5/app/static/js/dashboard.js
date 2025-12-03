console.log("App Started");
let map;
let geocoder;
let markers = [];
let highlightedPlaceIds = new Set();
let countryLayer, stateLayer, cityLayer;

// --- ROUTING SERVICES ---
let directionsService;
let directionsRenderer;
let flightPaths = [];
let currentLocations = [];

const activeStyle = {
    fillColor: '#2563eb', fillOpacity: 0.1, strokeColor: '#2563eb', strokeOpacity: 1.0, strokeWeight: 2
};

function initMap() {
    try {
        const defaultLoc = { lat: 20.5937, lng: 78.9629 };
        map = new google.maps.Map(document.getElementById("map"), {
            center: defaultLoc, zoom: 4, disableDefaultUI: true, mapId: 'f85aac46be23c13d1254f53d',
        });

        geocoder = new google.maps.Geocoder();
        directionsService = new google.maps.DirectionsService();
        directionsRenderer = new google.maps.DirectionsRenderer({ map: map, suppressMarkers: false });

        countryLayer = map.getFeatureLayer('COUNTRY');
        stateLayer = map.getFeatureLayer('ADMINISTRATIVE_AREA_LEVEL_1');
        cityLayer = map.getFeatureLayer('LOCALITY');
        [countryLayer, stateLayer, cityLayer].forEach(layer => setupLayerEvents(layer));
        applyStyles();

        // Listeners
        document.getElementById('search-button').addEventListener('click', performSearch);
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });

        // Mode Buttons (Manual Toggle)
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                const mode = e.currentTarget.getAttribute('data-mode');
                if (currentLocations.length >= 2) calculateRoute(currentLocations, mode, false);
            });
        });

        setupVoiceSearch();

    } catch (e) {
        console.error("Map Initialization Error:", e);
        showToast("Failed to initialize map.", "error");
    }
}
window.initMap = initMap;

// --- TOAST NOTIFICATION ---
function showToast(message, type = 'error') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'success' ? 'success' : ''}`;
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// --- VOICE SEARCH ---
function setupVoiceSearch() {
    if (!('webkitSpeechRecognition' in window)) return;
    const recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    const voiceBtn = document.getElementById('voice-trigger');
    const searchInput = document.getElementById('search-input');

    if (voiceBtn) {
        voiceBtn.addEventListener('click', () => recognition.start());
        recognition.onstart = () => voiceBtn.classList.add('listening');
        recognition.onend = () => voiceBtn.classList.remove('listening');
        recognition.onresult = (event) => {
            searchInput.value = event.results[0][0].transcript;
            performSearch();
        };
    }
}

// --- GLOBAL: Close Info Card ---
window.closeInfoCard = function () {
    const container = document.getElementById('cards-container');
    if (container) container.innerHTML = '';
}

// --- MAIN SEARCH ---
async function performSearch() {
    const input = document.getElementById('search-input');
    const btn = document.getElementById('search-button');
    const query = input.value.trim();

    if (!query) return;

    btn.innerText = "Processing...";
    btn.disabled = true;
    closeInfoCard();

    try {
        const response = await fetch('/api/resolve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        clearMap();

        // --- ROUTE MODE ---
        if (data.intent === 'ROUTE' && data.results.length >= 2) {
            currentLocations = data.results.map(r => r.city_name);

            // Show Standard Mode Selector (Car / Air)
            const modeSelector = document.getElementById('mode-selector');
            if (modeSelector) {
                modeSelector.style.display = 'flex';
                modeSelector.classList.remove('hidden');
            }

            // Default to Driving
            switchModeButton('DRIVING');
            calculateRoute(currentLocations, 'DRIVING', true);

            // Show Stats
            const stats = document.getElementById('route-stats');
            if (stats) stats.classList.remove('hidden');

        } else {
            // --- INFO MODE ---
            const modeSelector = document.getElementById('mode-selector');
            if (modeSelector) modeSelector.style.display = 'none';

            const bounds = new google.maps.LatLngBounds();
            const promises = [];

            for (const loc of data.results) {
                promises.push(geocodeAndHighlight(loc.city_name, bounds, loc.ai_answer, loc.ai_summary));
            }

            const results = await Promise.all(promises);

            if (!results.includes(true)) {
                showToast("No location found.", "error");
            } else {
                renderCards(data.results);
                if (!bounds.isEmpty()) map.fitBounds(bounds);
            }
        }

    } catch (e) {
        console.error("Search failed:", e);
        showToast("Analysis failed. Please try again.", "error");
    } finally {
        btn.innerText = "Analyze";
        btn.disabled = false;
    }
}

// --- CARDS LOGIC ---
function renderCards(results) {
    const container = document.getElementById('cards-container');
    container.innerHTML = '';

    // 1. COMPARISON CHART (Optional)
    const validDataCities = results.filter(city => city.population !== undefined && city.population > 0);
    if (validDataCities.length >= 2) {
        const chartCard = document.createElement('div');
        chartCard.className = 'info-card';

        const chartHeader = document.createElement('div');
        chartHeader.className = 'info-header';
        const chartTitle = document.createElement('h2');
        chartTitle.innerText = "Comparison Analysis";
        chartHeader.appendChild(chartTitle);
        chartCard.appendChild(chartHeader);

        const chartContent = document.createElement('div');
        chartContent.className = 'card-content';
        const canvas = document.createElement('canvas');
        canvas.style.width = '100%';
        canvas.style.maxHeight = '150px';
        chartContent.appendChild(canvas);
        chartCard.appendChild(chartContent);
        container.appendChild(chartCard);

        const labels = validDataCities.map(r => r.city_name);
        const dataPoints = validDataCities.map(r => r.population);

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Population',
                    data: dataPoints,
                    backgroundColor: 'rgba(37, 99, 235, 0.5)',
                    borderColor: 'rgba(37, 99, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { display: false } },
                    x: { ticks: { font: { size: 10 } } }
                }
            }
        });
    }

    results.forEach(loc => {
        // INFO CARD
        const infoCard = document.createElement('div');
        infoCard.className = 'info-card';
        infoCard.innerHTML = `<div class="info-header"><h2>${loc.city_name}</h2></div>`;

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'card-content';
        contentWrapper.innerHTML = `
            <p class="highlight-text">${loc.ai_answer || loc.ai_summary || "Location identified."}</p>
            ${loc.ai_answer && loc.ai_summary ? `<p class="sub-text">${loc.ai_summary}</p>` : ''}
        `;
        infoCard.appendChild(contentWrapper);
        container.appendChild(infoCard);

        // WEATHER CARD
        if (loc.weather) {
            const w = loc.weather;
            const weatherCard = document.createElement('div');
            weatherCard.className = 'info-card';
            weatherCard.innerHTML = `
                <div class="info-header"><h2>Weather in ${loc.city_name}</h2></div>
                <div class="weather-section">
                    <div class="weather-temp">${w.temperature}°C</div>
                    <div class="weather-details">
                        <span>${w.condition_text}</span>
                        <span>Wind: ${w.windspeed} km/h</span>
                    </div>
                </div>
            `;
            container.appendChild(weatherCard);
        }

        // RAINFALL CHART (NEW FEATURE)
        if (loc.rainfall_history) {
            const rainCard = document.createElement('div');
            rainCard.className = 'info-card';
            rainCard.innerHTML = `<div class="info-header"><h2>Rainfall (Last 5 Days)</h2></div>`;

            const chartDiv = document.createElement('div');
            chartDiv.className = 'card-content';
            const canvas = document.createElement('canvas');
            canvas.style.maxHeight = '140px';
            chartDiv.appendChild(canvas);
            rainCard.appendChild(chartDiv);
            container.appendChild(rainCard);

            new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: loc.rainfall_history.dates.map(d => d.slice(5)), // MM-DD
                    datasets: [{
                        label: 'Precipitation (mm)',
                        data: loc.rainfall_history.values,
                        backgroundColor: '#60a5fa'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true } }
                }
            });
        }
    });
}

// --- ROUTING LOGIC ---
function calculateRoute(locationList, mode, isAutoSwitchAllowed) {
    // Clear previous
    flightPaths.forEach(p => p.setMap(null));
    flightPaths = [];
    directionsRenderer.setMap(null);

    // MANUAL AIR MODE (Red Geodesic Lines)
    if (mode === 'AIR') {
        drawMultiHopAirRoute(locationList);
        return;
    }

    // DRIVING MODE
    directionsRenderer.setMap(map);
    const origin = locationList[0];
    const destination = locationList[locationList.length - 1];
    const waypoints = [];

    if (locationList.length > 2) {
        for (let i = 1; i < locationList.length - 1; i++) {
            waypoints.push({ location: locationList[i], stopover: true });
        }
    }

    directionsService.route({
        origin: origin,
        destination: destination,
        waypoints: waypoints,
        optimizeWaypoints: false,
        travelMode: google.maps.TravelMode[mode]
    }, (response, status) => {
        if (status === 'OK') {
            directionsRenderer.setDirections(response);
            let totalDist = 0, totalSec = 0;
            response.routes[0].legs.forEach(leg => {
                totalDist += leg.distance.value;
                totalSec += leg.duration.value;
            });
            updateStatsFormatted(totalDist, totalSec);
        } else {
            showToast('No driving route found.', 'error');
        }
    });
}

// --- MANUAL AIR ROUTE (The "Via" Feature) ---
async function drawMultiHopAirRoute(locations) {
    const bounds = new google.maps.LatLngBounds();
    let totalDistKm = 0;
    const coords = [];

    // Geocode all points
    for (const locName of locations) {
        const c = await geocodeLocation(locName);
        if (c) { coords.push(c); bounds.extend(c); }
    }
    if (coords.length < 2) return;

    // Draw Lines A -> B -> C
    for (let i = 0; i < coords.length - 1; i++) {
        const start = coords[i], end = coords[i + 1];
        const line = new google.maps.Polyline({
            path: [start, end], geodesic: true,
            strokeColor: '#ef4444', strokeOpacity: 0.8, strokeWeight: 4,
            icons: [{ icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 4, strokeColor: '#fff', fillColor: '#ef4444', fillOpacity: 1 }, offset: '50%' }],
            map: map
        });
        flightPaths.push(line);
        totalDistKm += (google.maps.geometry.spherical.computeDistanceBetween(start, end) / 1000);
    }
    map.fitBounds(bounds);

    // Approximate Flight Time (800km/h + 1hr layover per stop)
    const flightHours = totalDistKm / 800;
    const totalMinutes = Math.round((flightHours * 60) + ((locations.length - 2) * 60)); // Extra time for stops
    const h = Math.floor(totalMinutes / 60), m = totalMinutes % 60;
    updateStatsText(`${Math.round(totalDistKm).toLocaleString()} km`, h > 0 ? `~${h} hr ${m} min` : `~${m} min`);
}

function updateStatsFormatted(meters, seconds) {
    const km = (meters / 1000).toFixed(1);
    const h = Math.floor(seconds / 3600), m = Math.floor((seconds % 3600) / 60);
    updateStatsText(`${km} km`, h > 0 ? `${h} hr ${m} min` : `${m} min`);
}

function updateStatsText(dist, time) {
    const statsBox = document.getElementById('route-stats');
    if (statsBox) {
        document.getElementById('route-dist').innerText = dist;
        document.getElementById('route-time').innerText = time;
        statsBox.classList.remove('hidden');
    }
}

function switchModeButton(mode) {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`[data-mode="${mode}"]`);
    if (btn) btn.classList.add('active');
}

function geocodeLocation(address) {
    return new Promise((resolve) => {
        geocoder.geocode({ address: address }, (results, status) => {
            if (status === 'OK') resolve(results[0].geometry.location); else resolve(null);
        });
    });
}

// --- HELPER: Geocode & Highlight (Info Mode) ---
function geocodeAndHighlight(address, bounds, aiAnswer, aiSummary) {
    return new Promise((resolve) => {
        geocoder.geocode({ address: address }, (results, status) => {
            if (status === 'OK' && results[0]) {
                const res = results[0];
                if (res.geometry.viewport) bounds.union(res.geometry.viewport);
                else bounds.extend(res.geometry.location);

                const marker = new google.maps.Marker({
                    map: map,
                    position: res.geometry.location,
                    title: address,
                    animation: google.maps.Animation.DROP
                });
                markers.push(marker);
                if (res.place_id) highlightedPlaceIds.add(res.place_id);
                applyStyles();
                resolve(true);
            } else {
                resolve(false);
            }
        });
    });
}

function clearMap() {
    markers.forEach(m => m.setMap(null));
    markers = [];
    highlightedPlaceIds.clear();
    applyStyles();
    directionsRenderer.setDirections({ routes: [] });
    flightPaths.forEach(p => p.setMap(null));
    flightPaths = [];
    const stats = document.getElementById('route-stats');
    if (stats) stats.classList.add('hidden');
    closeInfoCard();
}

function applyStyles() {
    const styleFactory = (params) => {
        if (highlightedPlaceIds.has(params.feature.placeId)) return activeStyle;
        return null;
    };
    countryLayer.style = styleFactory;
    stateLayer.style = styleFactory;
    cityLayer.style = styleFactory;
}

function setupLayerEvents(layer) {
    layer.addListener('mousemove', (event) => {
        if (highlightedPlaceIds.has(event.features[0].placeId)) document.getElementById('map').style.cursor = 'pointer';
    });
    layer.addListener('mouseout', () => document.getElementById('map').style.cursor = '');
}
