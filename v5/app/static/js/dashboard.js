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
    console.log("initMap() started...");

    // Default View: India
    const defaultLoc = { lat: 20.5937, lng: 78.9629 };

    map = new google.maps.Map(document.getElementById("map"), {
        center: defaultLoc,
        zoom: 4,
        disableDefaultUI: true,
        mapId: 'f85aac46be23c13d1254f53d',
    });

    geocoder = new google.maps.Geocoder();
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({ map: map, suppressMarkers: false });

    // Layers & Styles
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

    // Mode Buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            const mode = e.currentTarget.getAttribute('data-mode');
            if (currentLocations.length >= 2) calculateRoute(currentLocations, mode, false);
        });
    });
}

// --- GLOBAL: Close Info Card ---
window.closeInfoCard = function () {
    const card = document.getElementById('info-card');
    if (card) card.classList.remove('active');
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
        const data = await response.json();

        clearMap();

        // --- 1. ROUTE MODE (Prioritize Routing if requested) ---
        if (data.intent === 'ROUTE' && data.results.length >= 2) {
            currentLocations = data.results.map(r => r.city_name);
            console.log(`Routing via: ${currentLocations.join(' -> ')}`);

            document.getElementById('mode-selector').style.display = 'flex';
            switchModeButton('DRIVING');
            calculateRoute(currentLocations, 'DRIVING', true);

        } else {
            // --- 2. INFO / NORMAL MODE ---
            document.getElementById('mode-selector').style.display = 'none';
            document.getElementById('route-stats').classList.remove('show-stats');

            const bounds = new google.maps.LatLngBounds();
            const promises = [];

            // Loop through results (e.g. Bangalore, Mysore)
            for (const loc of data.results) {
                // Pass the specific answer/summary for THIS location to the helper
                promises.push(geocodeAndHighlight(loc.city_name, bounds, loc.ai_answer, loc.ai_summary));
            }

            const results = await Promise.all(promises);

            if (!results.includes(true)) {
                alert("No location found.");
            } else if (!bounds.isEmpty()) {
                map.fitBounds(bounds);

                // If there is exactly one location, open its card automatically
                if (data.results.length === 1) {
                    const loc = data.results[0];
                    showInfoCard(loc.city_name, loc.ai_answer, loc.ai_summary);
                }
            }
        }

    } catch (e) {
        console.error("Search failed:", e);
        alert("An error occurred.");
    } finally {
        btn.innerText = "Analyze";
        btn.disabled = false;
    }
}

// --- INFO CARD FUNCTION ---
function showInfoCard(title, answer, summary) {
    const card = document.getElementById('info-card');
    if (!card) return;

    document.getElementById('info-title').innerText = title;

    // Logic: Use Answer if available, else Summary, else Default text
    let content = answer;
    if (!content && summary) content = summary;
    if (!content) content = "Location identified.";

    document.getElementById('info-answer').innerText = content;
    // Show summary as subtext only if we have both answer AND summary
    document.getElementById('info-summary').innerText = (answer && summary) ? summary : "";

    card.classList.add('active');
}

// --- ROUTING LOGIC ---
function calculateRoute(locationList, mode, isAutoSwitchAllowed) {
    flightPaths.forEach(p => p.setMap(null));
    flightPaths = [];
    directionsRenderer.setMap(null);

    if (mode === 'AIR') {
        drawMultiHopAirRoute(locationList);
        return;
    }

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
        } else if (status === 'ZERO_RESULTS' && isAutoSwitchAllowed && mode === 'DRIVING') {
            switchModeButton('AIR');
            drawMultiHopAirRoute(locationList);
        } else {
            alert('No route found for this mode.');
        }
    });
}

// --- HELPER: Air Route ---
async function drawMultiHopAirRoute(locations) {
    const bounds = new google.maps.LatLngBounds();
    let totalDistKm = 0;
    const coords = [];

    for (const locName of locations) {
        const c = await geocodeLocation(locName);
        if (c) { coords.push(c); bounds.extend(c); }
    }
    if (coords.length < 2) return;

    for (let i = 0; i < coords.length - 1; i++) {
        const start = coords[i], end = coords[i + 1];
        const line = new google.maps.Polyline({
            path: [start, end], geodesic: true, strokeColor: '#ef4444', strokeOpacity: 0.8, strokeWeight: 4,
            icons: [{ icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 4, strokeColor: '#fff', fillColor: '#ef4444', fillOpacity: 1 }, offset: '50%' }],
            map: map
        });
        flightPaths.push(line);
        totalDistKm += (google.maps.geometry.spherical.computeDistanceBetween(start, end) / 1000);
    }
    map.fitBounds(bounds);

    const flightHours = totalDistKm / 800;
    const totalMinutes = Math.round((flightHours * 60) + ((locations.length - 1) * 60));
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
    document.getElementById('route-dist').innerText = dist;
    document.getElementById('route-time').innerText = time;
    statsBox.classList.remove('hidden');
    statsBox.classList.add('show-stats');
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

// --- UPDATED HELPER: Accepts Info Data ---
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

                // --- CLICK LISTENER ---
                // Clicking the marker opens the card for THIS specific place
                marker.addListener('click', () => {
                    showInfoCard(address, aiAnswer, aiSummary);
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

    // Reset UI
    document.getElementById('route-stats').classList.remove('show-stats');
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