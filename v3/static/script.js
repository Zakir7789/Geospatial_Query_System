document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const queryInput = document.getElementById('query-input');
    const resolveButton = document.getElementById('resolve-button');
    const resultsContainer = document.getElementById('results-container');

    // Leaflet map setup
    const map = L.map('map').setView([20, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap'
    }).addTo(map);
    
    // This is the correct Leaflet class to use (fixes .getBounds error)
    const featureGroup = L.featureGroup().addTo(map);

    // --- Event Listeners ---
    resolveButton.addEventListener('click', onResolveClick);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onResolveClick();
        }
    });

    async function onResolveClick() {
        const query = queryInput.value;
        if (!query.trim()) return;

        setLoading(true);
        clearResults();

        try {
            const response = await fetch('/api/resolve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query }),
            });

            if (!response.ok) throw new Error(`Server error: ${response.status}`);

            const data = await response.json();

            displayResultCards(data.resolved_places);
            displayMapFeatures(data.resolved_places);

        } catch (error) {
            console.error("Error fetching results:", error);
            resultsContainer.innerHTML = `<p class="placeholder">Error: ${error.message}</p>`;
        } finally {
            setLoading(false);
        }
    }

    function displayResultCards(places) {
        if (places.length === 0) {
            resultsContainer.innerHTML = '<p class="placeholder">No places detected.</p>';
            return;
        }

        places.forEach(r => {
            const card = document.createElement('div');
            card.className = 'result-card';

            let cardClass = r.status === 'resolved' ? 'success' : (r.status === 'clarification_required' ? 'warning' : 'error');
            card.classList.add(cardClass);

            card.innerHTML = `
                <h3>${r.token}</h3>
                <p><span>Canonical:</span> ${r.canonical_name || '❌ Unmatched'}</p>
                <p><span>Status:</span> ${r.status}</p>
                ${r.table ? `<p><span>Table:</span> ${r.table}</p>` : ''}
                ${r.confidence ? `<p><span>Confidence:</span> ${r.confidence.toFixed(3)}</p>` : ''}
            `;
            resultsContainer.appendChild(card);
        });
    }

    function displayMapFeatures(places) {
        let singlePoint = null; 

        places.forEach(r => {
            // This 'if' block is all we need.
            // app_api.py is sending lat/lon for cities
            if (r.lat && r.lon) {
                // *** This draws the Leaflet point marker ***
                const color = r.confidence < 0.9 ? 'orange' : 'green';
                L.circleMarker([r.lat, r.lon], {
                    radius: 8, color: color,
                    fillColor: color, fillOpacity: 0.8
                }).addTo(featureGroup).bindPopup(`<b>${r.canonical_name}</b> (${r.token})`);
                
                singlePoint = [r.lat, r.lon];
            }
        });

        // Auto-zoom map
        const layerCount = featureGroup.getLayers().length;
        
        if (layerCount === 1 && singlePoint) {
            // If it's just one marker, use setView to zoom in
            map.setView(singlePoint, 10); // 10 is a good zoom level for a city
        } else if (layerCount > 0) {
            // If it's multiple markers, use fitBounds
            map.fitBounds(featureGroup.getBounds(), { padding: [50, 50] });
        }
    }

    function setLoading(isLoading) {
        resolveButton.disabled = isLoading;
        resolveButton.textContent = isLoading ? "Resolving..." : "Resolve";
    }

    function clearResults() {
        resultsContainer.innerHTML = '<p class="placeholder">Results will appear here...</p>';
        featureGroup.clearLayers();
        map.setView([20, 0], 2); // Reset map view on clear
    }
});