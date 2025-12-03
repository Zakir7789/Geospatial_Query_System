if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import os
import json
import re
import spacy
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class NLPService:
    client = None
    HAS_LLM = False
    
    # Load Spacy (Backup only)
    try:
        nlp = spacy.load("en_core_web_trf")
    except:
        try:
            nlp = spacy.load("en_core_web_sm")
        except:
            print("[WARNING] Spacy not found.")
            nlp = None

    # Connect to Gemini
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            HAS_LLM = True
    except Exception as e:
        print(f"[ERROR] Gemini Init Failed: {e}")

    @staticmethod
    def analyze_query(text):
        """
        Uses LLM to:
        1. Identify Intent (WEATHER, ROUTE, INFO)
        2. Extract & Autocorrect Locations
        3. Handle Context & Mixed Lists
        4. Generate Answer & Summary PER LOCATION
        """
        result = {
            "intent": "INFO", 
            "locations": [], 
            "location_details": {}, # Stores info for each place: { "PlaceName": { "summary": "...", "answer": "..." } }
            "params": {}
        }

        if NLPService.HAS_LLM:
            try:
                # --- MASTER PROMPT ---
                prompt = f"""
                You are a Geospatial Assistant.
                User Input: "{text}"
                
                Tasks:
                1. Identify INTENT: "WEATHER", "ROUTE", "NEARBY", or "INFO" (General query).
                
                2. Extract Locations & Perform Autocorrect:
                   - Fix typos: "Banglore" -> "Bengaluru"
                   - Resolve Aliases: "Bombay" -> "Mumbai"
                
                3. CONTEXT FUSION (Critical):
                   - If a city is followed by a Region/State/Country, MERGE them into one string with a comma.
                   - Apply context ONLY to the specific city it belongs to.
                   - Example: "Paris in Texas" -> ["Paris, Texas"]
                   - Example: "Bangalore and Madurai and Paris in Texas" -> ["Bengaluru", "Madurai", "Paris, Texas"]
                
                4. ROUTE ORDERING:
                   - Preserve sequence: "From A to B via C" -> ["A", "C", "B"]
                
                5. GENERATE CONTENT (Per Location):
                   - For EACH location found, provide a "summary" (3-4 sentences covering key facts like capital, population, and significance).
                   - If the user asked a specific question (e.g. "Who founded X?"), put the answer in the "answer" field for that location.
                
                Output JSON:
                {{
                  "intent": "string",
                  "locations": ["Loc1", "Loc2"],
                  "location_details": {{
                      "Loc1": {{ "summary": "Fact about Loc1", "answer": "Specific answer if relevant" }},
                      "Loc2": {{ "summary": "Fact about Loc2", "answer": "" }}
                  }},
                  "params": {{ "radius_km": 50 }}
                }}
                
                Return ONLY valid JSON.
                """
                
                response = NLPService.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3, 
                        response_mime_type="application/json"
                    )
                )
                
                if response.text:
                    result = json.loads(response.text)
                    return result
            except Exception as e:
                # Check if it's a rate limit error (429 or ResourceExhausted)
                error_str = str(e).lower()
                if "429" in error_str or "resource" in error_str or "quota" in error_str or "rate" in error_str:
                    print(f"[WARNING] LLM Quota Exceeded, switching to fallback mode")
                else:
                    print(f"[ERROR] LLM Failed: {e}")
                
                # Trigger fallback
                return NLPService._local_fallback(text)

        # If LLM is not available, use fallback
        if not NLPService.HAS_LLM:
            return NLPService._local_fallback(text)
            
        return result

    @staticmethod
    def _local_fallback(text):
        """
        Local rule-based extraction when LLM is unavailable.
        Uses keyword matching for intent and regex/spacy for locations.
        """
        result = {
            "intent": "INFO",
            "locations": [],
            "location_details": {},
            "params": {}
        }
        
        text_lower = text.lower()
        
        # --- INTENT DETECTION ---
        if any(keyword in text_lower for keyword in ["weather", "temperature", "climate", "forecast"]):
            result["intent"] = "WEATHER"
        elif any(keyword in text_lower for keyword in ["route", "drive", "fly", "from", "to", "travel", "journey"]):
            result["intent"] = "ROUTE"
        elif any(keyword in text_lower for keyword in ["nearby", "near", "around", "close to"]):
            result["intent"] = "NEARBY"
            result["params"]["radius_km"] = 50
        
        # --- LOCATION EXTRACTION ---
        locations = []
        
        # Method 1: Use Spacy if available
        if NLPService.nlp:
            try:
                doc = NLPService.nlp(text)
                locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
            except Exception as e:
                print(f"[WARNING] Spacy extraction failed: {e}")
        
        # Method 2: Regex fallback (extract capitalized words)
        if not locations:
            # Pattern: Capitalized words (possibly multi-word like "New York")
            pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
            matches = re.findall(pattern, text)
            
            # Filter out common keywords that aren't locations
            stopwords = {"From", "To", "Via", "In", "The", "And", "Or", "Weather", "Route", "Tell", "About",
                        "Temperature", "Climate", "Distance", "Forecast", "Compare", "Between"}
            locations = [m for m in matches if m not in stopwords]
        
        # Handle "and" separators ONLY if we still have no locations
        # This prevents overwriting good Spacy extractions
        if not locations and " and " in text_lower:
            # Split by "and" and re-extract from each part
            parts = text.split(" and ")
            locations = []
            for part in parts:
                if NLPService.nlp:
                    try:
                        doc = NLPService.nlp(part)
                        locs = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
                        locations.extend(locs)
                    except:
                        pass
                else:
                    matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', part)
                    stopwords = {"From", "To", "Via", "In", "The", "And", "Or", "Weather", "Route", "Tell", "About",
                                "Temperature", "Climate", "Distance", "Forecast", "Compare", "Between"}
                    locations.extend([m for m in matches if m not in stopwords])
        
        # Deduplicate while preserving order
        seen = set()
        unique_locations = []
        for loc in locations:
            if loc not in seen:
                unique_locations.append(loc)
                seen.add(loc)
        
        result["locations"] = unique_locations
        
        # Add minimal location details (no AI summary in fallback)
        for loc in unique_locations:
            result["location_details"][loc] = {
                "summary": "",
                "answer": ""
            }
        
        print(f"[FALLBACK MODE] Extracted: {result}")
        return result

# --- TEST BLOCK ---
if __name__ == "__main__":
    print("\n--- TESTING MASTER NLP SERVICE ---")
    
    queries = [
        "tell me about Banglore and hosur", 
        "route from bangalore to delhi via mumbaai",
        "Bangalore and Madurai and Paris in Texas",
        "Who founded Hyderabad in India?",
        "india and England",
        "Weather in Chennai and Kolkata"
    ]
    
    for q in queries:
        print(f"\nQuery: '{q}'")
        res = NLPService.analyze_query(q)
        print(f"   Intent:    {res.get('intent')}")
        print(f"   Locations: {res.get('locations')}")
        print(f"   Details:   {json.dumps(res.get('location_details'), indent=2)}")