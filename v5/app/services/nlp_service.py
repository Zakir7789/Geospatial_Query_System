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
                   - For EACH location found, provide a "summary" (1 sentence fact).
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
                print(f"[ERROR] LLM Failed: {e}")

        # Fallback: Spacy (Basic extraction, no autocorrect)
        if not result['locations'] and NLPService.nlp:
            doc = NLPService.nlp(text)
            locs = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
            result['locations'] = list(dict.fromkeys(locs))
            # No details in fallback
            
        return result

# --- TEST BLOCK ---
if __name__ == "__main__":
    print("\n--- TESTING MASTER NLP SERVICE ---")
    
    queries = [
        "tell me about Banglore", 
        "route from bangalore to delhi via mumbaai",
        "Bangalore and Madurai and Paris in Texas",
        "Who founded Hyderabad in India?",
        "india and England"
    ]
    
    for q in queries:
        print(f"\nQuery: '{q}'")
        res = NLPService.analyze_query(q)
        print(f"   Intent:    {res.get('intent')}")
        print(f"   Locations: {res.get('locations')}")
        print(f"   Details:   {json.dumps(res.get('location_details'), indent=2)}")