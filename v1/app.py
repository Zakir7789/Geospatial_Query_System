import streamlit as st
from nlp import extract_place_entities
from matcher_phonetic import phonetic_match_tokens
from matcher_semantic_cached import SemanticMatcher
from db import Database
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium
import base64

# --- Function to set the background image ---
def set_background(image_file):
    """
    Sets the background image of the Streamlit app using base64 encoding.
    """
    try:
        # 1. Read the image file and encode it to Base64
        with open(image_file, "rb") as f:
            img_bytes = f.read()
        encoded_string = base64.b64encode(img_bytes).decode()

        # 2. Inject CSS with the Base64 image
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpeg;base64,{encoded_string}");
                background-size: cover; /* Cover the entire page */
                background-repeat: no-repeat; /* No tiling */
                background-attachment: fixed; /* Fixed background */
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.error(f"Background image file not found: {image_file}")
    except Exception as e:
        st.error(f"Error setting background image: {e}")

# 3. Call the function before any other Streamlit component
set_background('bg-img.jpg')

CONFIDENCE_THRESHOLD = 0.8


# --- Cache database connection ---
@st.cache_resource
def get_db():
    db = Database()
    db.connect_db()
    return db


# --- Cache canonical tables ---
@st.cache_data
def load_canonical_tables(_db):   # note the _db instead of db
    canonical_tables = {}
    with _db.conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE';
        """)
        tables = [row[0] for row in cur.fetchall()]
    for t in tables:
        df = _db.fetch_table(t)
        if not df.empty:
            canonical_tables[t] = df['name'].tolist()
    return canonical_tables



# --- Cache semantic matcher ---
@st.cache_resource
def get_semantic_matcher(canonical_tables):
    return SemanticMatcher(canonical_tables)


# --- Resolve places ---
def resolve_places(places, canonical_tables, matcher):
    results = []
    fuzzy_results = phonetic_match_tokens(places, canonical_tables)

    for fr in fuzzy_results:
        if fr["canonical"] is None:
            sem_results = matcher.semantic_match_tokens([fr["token"]])
            if sem_results and sem_results[0]["canonical"] is not None:
                r = sem_results[0]
                r["source"] = "semantic"
            else:
                r = fr
                r["source"] = "unmatched"
                r["score"] = 0
        else:
            r = fr
            r["source"] = "phonetic"

        r["warning"] = r["score"] < CONFIDENCE_THRESHOLD
        results.append(r)
    return results


# --- Initialize once ---
db = get_db()

canonical_tables = load_canonical_tables(db)  # db gets passed as _db internally
matcher = get_semantic_matcher(canonical_tables)



# --- Streamlit UI ---
st.title("🌍 Geospatial Query Resolver & Map Visualization")
query = st.text_area("Enter query here:", "")

if st.button("Resolve Places"):
    if not query.strip():
        st.warning("Please enter a query.")
    else:
        places = extract_place_entities(query)
        resolved = resolve_places(places, canonical_tables, matcher)
        st.session_state["resolved_results"] = resolved  # ✅ save to session_state


# --- Display results if available ---
if "resolved_results" in st.session_state:
    resolved = st.session_state["resolved_results"]

    if not resolved:
        st.info("No places detected.")
    else:
        st.subheader("Resolved Places")
        for r in resolved:
            token = r["token"]
            canonical = r["canonical"] or "❌ Unmatched"
            table = r["table"] or "-"
            score = round(r["score"], 3)
            source = r["source"]
            warning = r["warning"]

            if warning:
                bg_color = "#FFF3CD"
            elif source in ["phonetic", "semantic"]:
                bg_color = "#D4EDDA"
            else:
                bg_color = "#F8D7DA"

        # --- Map visualization ---
        st.subheader("📍 Map of Resolved Places")
        m = folium.Map(location=[20, 0], zoom_start=2)
        geolocator = Nominatim(user_agent="geo_resolver")

        for r in resolved:
            if r["canonical"]:
                try:
                    location = geolocator.geocode(r["canonical"], timeout=100)
                    if location:
                        color = "green" if not r["warning"] else "orange"
                        folium.CircleMarker(
                            location=[location.latitude, location.longitude],
                            radius=8,
                            popup=f"{r['canonical']} ({r['token']})",
                            color=color,
                            fill=True,
                            fill_color=color,
                        ).add_to(m)
                except Exception as e:
                    st.warning(f"Could not geocode {r['canonical']}: {e}")

        st_folium(m, width=700, height=500)
