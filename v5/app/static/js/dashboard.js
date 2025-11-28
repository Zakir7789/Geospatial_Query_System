let map;
let geocoder;
let markers = [];
let highlightedPlaceIds = new Set();
let countryLayer, stateLayer, cityLayer;

// --- ROUTING SERVICES ---
let directionsService;
let directionsRenderer;
let flightPaths = []; // Changed to Array to hold multiple segments

// Store current route list (Ordered)
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
    directionsRenderer = new google.maps.DirectionsRenderer({
        map: map,
        suppressMarkers: false // Google puts markers A/B, we might add intermediate ones
    });

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

    // Mode Button Logic
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            const target = e.currentTarget;
            target.classList.add('active');

            const mode = target.getAttribute('data-mode');

            if (currentLocations.length >= 2) {
                // Pass 'false' to indicate this is a MANUAL click (don't auto-switch)
                calculateRoute(currentLocations, mode, false);
            }
        });
    });
}

// --- MAIN SEARCH ---
async function performSearch() {
    const input = document.getElementById('search-input');
    const btn = document.getElementById('search-button');
    const query = input.value.trim();

    if (!query) return;

    btn.innerText = "Processing...";
    btn.disabled = true;

    try {
        const response = await fetch('/api/resolve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();

        clearMap();

        // 1. ROUTE MODE (2 or more locations)
        if (data.intent === 'ROUTE' && data.results.length >= 2) {

            // Extract just the names in order
            currentLocations = data.results.map(r => r.city_name);
            console.log(`Routing via: ${currentLocations.join(' -> ')}`);

            // Show Selector
            document.getElementById('mode-selector').style.display = 'flex';

            // Default to Driving, allowing auto-switch (isAutoSwitchAllowed = true)
            switchModeButton('DRIVING');
            calculateRoute(currentLocations, 'DRIVING', true);

        } else {
            // 2. NORMAL SEARCH
            document.getElementById('mode-selector').style.display = 'none';
            const statsBox = document.getElementById('route-stats');
            statsBox.style.display = 'none';
            statsBox.classList.add('hidden');
            const bounds = new google.maps.LatLngBounds();
            const promises = [];
            const list = (data.results && data.results.length > 0) ? data.results.map(l => l.city_name) : [query];

            for (const loc of list) {
                promises.push(geocodeAndHighlight(loc, bounds));
            }

            const results = await Promise.all(promises);
            if (!results.includes(true)) alert("No location found.");
            else if (!bounds.isEmpty()) map.fitBounds(bounds);
        }

    } catch (e) {
        console.error("Search failed:", e);
        alert("An error occurred.");
    } finally {
        btn.innerText = "Analyze";
        btn.disabled = false;
    }
}

// --- ROUTING LOGIC (Handles Waypoints) ---
function calculateRoute(locationList, mode, isAutoSwitchAllowed) {

    // Clear old visual artifacts
    flightPaths.forEach(p => p.setMap(null));
    flightPaths = [];
    directionsRenderer.setMap(null);

    // 1. AIR MODE (Geodesic Flight Path)
    if (mode === 'AIR') {
        drawMultiHopAirRoute(locationList);
        return;
    }

    // 2. ROAD/WALK MODE
    directionsRenderer.setMap(map);

    // Setup Origin, Destination, and Waypoints
    const origin = locationList[0];
    const destination = locationList[locationList.length - 1];

    const waypoints = [];
    // If there are middle cities, add them as waypoints
    if (locationList.length > 2) {
        for (let i = 1; i < locationList.length - 1; i++) {
            waypoints.push({
                location: locationList[i],
                stopover: true
            });
        }
    }

    directionsService.route({
        origin: origin,
        destination: destination,
        waypoints: waypoints,
        optimizeWaypoints: false, // Keep the user's order (Bangalore -> Mumbai -> Delhi)
        travelMode: google.maps.TravelMode[mode]
    }, (response, status) => {
        if (status === 'OK') {
            // Success
            directionsRenderer.setDirections(response);

            // Calculate Total Distance/Time across all legs
            let totalDistMeters = 0;
            let totalSeconds = 0;

            response.routes[0].legs.forEach(leg => {
                totalDistMeters += leg.distance.value;
                totalSeconds += leg.duration.value;
            });

            updateStatsFormatted(totalDistMeters, totalSeconds);

        } else if (status === 'ZERO_RESULTS') {
            // FAILURE CASE
            if (isAutoSwitchAllowed && mode === 'DRIVING') {
                // Only switch automatically on the FIRST load
                console.warn("Road not possible. Auto-switching to AIR.");
                switchModeButton('AIR');
                drawMultiHopAirRoute(locationList);
            } else {
                // Manual click failure -> Show Error
                alert("No route found for this mode. Try Air travel.");
            }
        } else {
            window.alert('Directions request failed: ' + status);
        }
    });
}

// Helper: Multi-Hop Air Route (A->B, B->C)
async function drawMultiHopAirRoute(locations) {
    const bounds = new google.maps.LatLngBounds();
    let totalDistKm = 0;

    // We need to resolve coordinates for ALL locations first
    const coords = [];
    for (const locName of locations) {
        const c = await geocodeLocation(locName);
        if (c) {
            coords.push(c);
            bounds.extend(c);
        }
    }

    if (coords.length < 2) return;

    // Draw lines between sequential points
    for (let i = 0; i < coords.length - 1; i++) {
        const start = coords[i];
        const end = coords[i + 1];

        // Draw Line
        const line = new google.maps.Polyline({
            path: [start, end],
            geodesic: true, // Curve
            strokeColor: '#ef4444',
            strokeOpacity: 0.8,
            strokeWeight: 4,
            icons: [{
                icon: {
                    path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                    scale: 4,
                    strokeColor: '#fff',
                    fillColor: '#ef4444',
                    fillOpacity: 1
                },
                offset: '50%'
            }],
            map: map
        });
        flightPaths.push(line);

        // Calculate Distance
        const distMeters = google.maps.geometry.spherical.computeDistanceBetween(start, end);
        totalDistKm += (distMeters / 1000);
    }

    map.fitBounds(bounds);

    // Calculate Estimated Duration (Total Distance / 800kmh + 1hr per stop)
    // 1 Stop = 60 mins, 2 Stops = 120 mins logistics time
    const flightHours = totalDistKm / 800;
    const logisticsMinutes = (locations.length - 1) * 60;

    const totalMinutes = Math.round((flightHours * 60) + logisticsMinutes);

    // Format Display
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    const timeStr = h > 0 ? `~${h} hr ${m} min` : `~${m} min`;

    updateStatsText(`${Math.round(totalDistKm).toLocaleString()} km`, timeStr);
}

function updateStatsFormatted(meters, seconds) {
    const km = (meters / 1000).toFixed(1);

    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);

    const timeStr = h > 0 ? `${h} hr ${m} min` : `${m} min`;
    updateStatsText(`${km} km`, timeStr);
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
            if (status === 'OK') resolve(results[0].geometry.location);
            else resolve(null);
        });
    });
}

// --- STANDARD MAP FUNCTIONS ---
function geocodeAndHighlight(address, bounds) {
    return new Promise((resolve) => {
        geocoder.geocode({ address: address }, (results, status) => {
            if (status === 'OK' && results[0]) {
                const res = results[0];
                if (res.geometry.viewport) bounds.union(res.geometry.viewport);
                else bounds.extend(res.geometry.location);

                const marker = new google.maps.Marker({
                    map: map, position: res.geometry.location, title: address, animation: google.maps.Animation.DROP
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
    directionsRenderer.setDirections({routes: []});
    flightPaths.forEach(p => p.setMap(null));
    flightPaths = [];
    
    const statsBox = document.getElementById('route-stats');
    statsBox.classList.remove('show-stats');
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