if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import os
import json
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
        Uses LLM to Autocorrect, Normalize, and extract Context.
        """
        # Default fallback structure
        result = {"intent": "WEATHER", "locations": [], "params": {}}

        if NLPService.HAS_LLM:
            try:
                # --- THE AUTOCORRECT & CONTEXT PROMPT ---
                prompt = f"""
                You are a Geospatial Query Corrector.
                Input: "{text}"
                
                Task:
                1. Identify the user's INTENT: "WEATHER", "ROUTE", or "NEARBY".
                2. Extract locations and perform AUTOCORRECT on them.
                   - Fix typos: "Banglore" -> "Bengaluru"
                   - Resolve Aliases: "Bombay" -> "Mumbai", "Madras" -> "Chennai"
                   - Contextual Disambiguation: If user says "Paris near Dallas", return "Paris". If just "Paris", return "Paris".
                        Examples:
                        - "Paris in Texas" -> ["Paris, Texas"]
                        - "Paris France" -> ["Paris, France"]
                        - "Hyderabad Pakistan vs Hyderabad India" -> ["Hyderabad, Pakistan", "Hyderabad, India"]
                        - "Route from London Ontario to London UK" -> ["London, Ontario", "London, UK"]
                        - "Banglore" -> ["Bengaluru"] (Autocorrect)

                
                3. CRITICAL: Preserve TRAVEL ORDER for Routes.
                   - "Bangalore to Delhi via Mumbai" -> ["Bengaluru", "Mumbai", "Delhi"]
                   - "Trip from London to Paris stopping in Lyon" -> ["London", "Lyon", "Paris"]   
                                      - If a city is followed by a Region/State/Country, MERGE them into one string with a comma.

                   - Apply context ONLY to the specific city it belongs to.
                    Examples:
                    - "Paris in Texas" -> ["Paris, Texas"]
                    - "Bangalore and Madurai and Paris in Texas" -> ["Bengaluru", "Madurai", "Paris, Texas"]
                    - "London UK and London Ontario" -> ["London, UK", "London, Ontario"]
                    - "Rome Italy, Paris France and Barcelona" -> ["Rome, Italy", "Paris, France", "Barcelona"]  
                           
                Output JSON Format:
                {{
                  "intent": "string",
                  "locations": ["CorrectedName1", "CorrectedName2"], or for Route "locations": ["StartLocation", "Waypoint", "EndLocation"],
                  "params": {{ "radius_km": 50 }}
                }}
                
                Return ONLY valid JSON.
                """
                
                response = NLPService.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0, # 0.0 means strictly factual/deterministic
                        response_mime_type="application/json"
                    )
                )
                
                if response.text:
                    result = json.loads(response.text)
                    return result
            except Exception as e:
                print(f"[ERROR] LLM Failed: {e}")

        # Fallback: Spacy (Basic extraction, no autocorrect)
        if not result['locations'] and NLPService.nlp:
            doc = NLPService.nlp(text)
            locs = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
            # Deduplicate preserving order
            result['locations'] = list(dict.fromkeys(locs))
            
        return result

# --- TEST BLOCK ---
if __name__ == "__main__":
    print("\n--- TESTING NLP AUTOCORRECT ---")
    
    queries = [
        "tell me about Banglore",          # Typo Test
        "weather in Bombay",               # Alias Test
        "compare India and Austrailia",    # Typo Test
        "route from Delh to Agra",          # Typo Test
        "paris in texas",
        "route from bangalore to delhi via mumbaai",  # Multiple Typos
        "Paris in Texas",
        "Route from London UK to London Ontario",
        "Hyderabad in Pakistan",
        "Bangalore and Madurai and Paris in Texas"
    ]
    
    for q in queries:
        print(f"\nQuery: '{q}'")
        res = NLPService.analyze_query(q)
        print(f"   Intent:    {res.get('intent')}")
        print(f"   Locations: {res.get('locations')}")