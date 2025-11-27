let map;
let geocoder;
let hourlyChart = null;

// --- STATE MANAGEMENT ---
// Changed to a Set to store MULTIPLE place IDs
let highlightedPlaceIds = new Set(); 
let hoveredPlaceId = null;

// --- LAYERS ---
let countryLayer, stateLayer, cityLayer;

// --- STYLES ---
// 1. Active Style (Highlighted Border for multiple places)
const activeStyle = {
    fillColor: '#2563eb',   
    fillOpacity: 0.1,       
    strokeColor: '#2563eb', 
    strokeOpacity: 1.0,
    strokeWeight: 2,
};

// 2. Hover Style (When mouse is over ANY highlighted area)
const hoverStyle = {
    fillColor: '#2563eb',   
    fillOpacity: 0.4,       
    strokeColor: '#1d4ed8', 
    strokeOpacity: 1.0,
    strokeWeight: 3,
};

function initMap() {
    const defaultLoc = { lat: 20.5937, lng: 78.9629 };

    map = new google.maps.Map(document.getElementById("map"), {
        center: defaultLoc,
        zoom: 4,
        disableDefaultUI: true,
        // Make sure this Map ID allows Vector Maps in Cloud Console
        mapId: 'f85aac46be23c13d1254f53d' 
    });

    geocoder = new google.maps.Geocoder();

    // Init Feature Layers
    countryLayer = map.getFeatureLayer('COUNTRY');
    stateLayer = map.getFeatureLayer('ADMINISTRATIVE_AREA_LEVEL_1');
    cityLayer = map.getFeatureLayer('LOCALITY');

    // Add Event Listeners to Layers
    [countryLayer, stateLayer, cityLayer].forEach(layer => {
        setupLayerEvents(layer);
    });

    // UI Listeners
    document.getElementById('search-button').addEventListener('click', handleSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if(e.key === 'Enter') handleSearch();
    });

    initEmptyChart();
}

// --- LAYER EVENT LOGIC ---
function setupLayerEvents(layer) {
    // 1. Mouse Move: Detect Hover
    layer.addListener('mousemove', (event) => {
        const featureId = event.features[0].placeId;
        
        // Only trigger hover if this place is currently highlighted
        if (highlightedPlaceIds.has(featureId)) {
            hoveredPlaceId = featureId;
            applyLayerStyles();
            document.getElementById('map').style.cursor = 'pointer';
            document.getElementById('map-tooltip').classList.add('visible');
        }
    });

    // 2. Mouse Out: Reset Hover
    layer.addListener('mouseout', (event) => {
        hoveredPlaceId = null;
        applyLayerStyles();
        document.getElementById('map').style.cursor = '';
        document.getElementById('map-tooltip').classList.remove('visible');
    });

    // 3. Click: Trigger Visualization
    layer.addListener('click', (event) => {
        const featureId = event.features[0].placeId;
        if (highlightedPlaceIds.has(featureId)) {
            fetchDataForLocation(event.latLng.lat(), event.latLng.lng(), event.features[0].displayName);
        }
    });
}

// --- STYLE APPLICATION ---
function applyLayerStyles() {
    const styleFactory = (params) => {
        const placeId = params.feature.placeId;
        
        // 1. Hover has highest priority
        if (placeId === hoveredPlaceId) {
            return hoverStyle;
        }
        
        // 2. Then check if it is in the set of Highlighted IDs
        if (highlightedPlaceIds.has(placeId)) {
            return activeStyle;
        }
        
        return null; 
    };

    countryLayer.style = styleFactory;
    stateLayer.style = styleFactory;
    cityLayer.style = styleFactory;
}

// --- SEARCH HANDLER (Multiple Locations) ---
async function handleSearch() {
    const query = document.getElementById('search-input').value;
    if (!query) return;

    // 1. Simple Keyword Parsing (Split by 'vs', 'and', ',')
    const rawTokens = query.split(/,| and | vs | VS | AND /);
    const stopWords = ['weather', 'in', 'show', 'temperature', 'compare', 'rainfall', 'average', 'the'];
    const locations = rawTokens
        .map(t => t.trim())
        .filter(t => t.length > 0)
        .filter(t => !stopWords.includes(t.toLowerCase()));

    // 2. Reset State
    highlightedPlaceIds.clear();
    hoveredPlaceId = null;
    
    // 3. Geocode Loop
    const bounds = new google.maps.LatLngBounds();
    let foundCount = 0;

    for (const locName of locations) {
        try {
            const result = await geocodeOne(locName);
            if (result) {
                // Add to Set
                highlightedPlaceIds.add(result.place_id);
                
                // Extend Bounds
                if (result.geometry.viewport) {
                    bounds.union(result.geometry.viewport);
                } else {
                    bounds.extend(result.geometry.location);
                }
                foundCount++;
            }
        } catch (e) {
            console.warn(`Skipping ${locName}`, e);
        }
    }

    // 4. Update Map & Styles
    if (foundCount > 0) {
        applyLayerStyles(); // Redraw styles with new Set
        map.fitBounds(bounds); // Zoom to fit all
        
        // Optional: padding to not cut off edges
        // map.fitBounds(bounds, 50); 
    } else {
        alert("No locations found.");
    }
}

// Helper for single geocode
function geocodeOne(address) {
    return new Promise((resolve) => {
        geocoder.geocode({ address: address }, (results, status) => {
            if (status === 'OK' && results[0]) {
                resolve(results[0]);
            } else {
                resolve(null);
            }
        });
    });
}

// --- DATA FETCHING ---
async function fetchDataForLocation(lat, lng, displayName) {
    // Show Dashboard
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('data-content').classList.remove('hidden');
    document.getElementById('loading-indicator').style.display = 'flex';
    
    // Update Name (Try to use what we have, or generic)
    document.getElementById('city-name').innerText = displayName || "Selected Location";

    try {
        const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&hourly=temperature_2m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto`;
        const aqiUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lng}&current=us_aqi`;

        const [wRes, aRes] = await Promise.all([fetch(weatherUrl), fetch(aqiUrl)]);
        const wData = await wRes.json();
        const aData = await aRes.json();

        updateDashboard(wData, aData);

    } catch (e) {
        console.error(e);
    }
}

function updateDashboard(wData, aData) {
    const current = wData.current;
    const daily = wData.daily;
    const aqi = aData.current ? aData.current.us_aqi : '--';

    document.getElementById('current-date').innerText = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    document.getElementById('current-temp').innerText = Math.round(current.temperature_2m) + "°";
    document.getElementById('weather-desc').innerText = getWeatherDesc(current.weather_code);
    document.getElementById('main-icon').innerText = getWeatherIcon(current.weather_code);

    document.getElementById('wind-speed-text').innerText = current.wind_speed_10m + " km/h";
    document.getElementById('humidity-val').innerText = current.relative_humidity_2m + "%";
    document.getElementById('aqi-text').innerText = aqi;

    const fContainer = document.getElementById('forecast-container');
    fContainer.innerHTML = '';
    for(let i=0; i<5; i++) {
        const day = new Date(daily.time[i]).toLocaleDateString('en-US', {weekday:'short'});
        const icon = getWeatherIcon(daily.weather_code[i]);
        const temp = Math.round(daily.temperature_2m_max[i]);
        
        const div = document.createElement('div');
        div.className = 'forecast-item';
        div.innerHTML = `<div>${day}</div><div>${icon}</div><div>${temp}°</div>`;
        fContainer.appendChild(div);
    }

    updateChart(wData.hourly);
}

function updateChart(hourly) {
    const labels = [];
    const data = [];
    // Take every 2nd hour for next 12 hours
    const nowIndex = new Date().getHours();
    
    for(let i=0; i<12; i+=2) {
        if (nowIndex + i < hourly.time.length) {
            const t = new Date(hourly.time[nowIndex + i]);
            labels.push(t.getHours() + ":00");
            data.push(hourly.temperature_2m[nowIndex + i]);
        }
    }

    hourlyChart.data.labels = labels;
    hourlyChart.data.datasets[0].data = data;
    hourlyChart.update();
}

function initEmptyChart() {
    const ctx = document.getElementById('hourlyChart').getContext('2d');
    hourlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temp (°C)',
                data: [],
                borderColor: '#2563eb',
                backgroundColor: (context) => {
                    const ctx = context.chart.ctx;
                    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
                    gradient.addColorStop(0, 'rgba(37, 99, 235, 0.2)');
                    gradient.addColorStop(1, 'rgba(37, 99, 235, 0)');
                    return gradient;
                },
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: '#2563eb',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { font: {size: 11} } },
                y: { display: false }
            }
        }
    });
}

// Helpers
function getWeatherIcon(code) {
    if (code === 0) return "☀️";
    if (code < 3) return "⛅";
    if (code < 50) return "🌫️";
    if (code < 80) return "🌧️";
    return "⛈️";
}

function getWeatherDesc(code) {
    if (code === 0) return "Clear Sky";
    if (code < 3) return "Partly Cloudy";
    if (code < 50) return "Foggy";
    if (code < 80) return "Rainy";
    return "Stormy";
}