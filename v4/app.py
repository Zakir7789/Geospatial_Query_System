from flask import Flask, render_template, request, jsonify
import os

# Try importing spacy for better NLP if available
import spacy

# Load the small English model
# Run `python -m spacy download en_core_web_sm` if this fails
nlp = spacy.load("en_core_web_trf")

app = Flask(__name__, static_folder='static', template_folder='templates')


@app.route('/')
def home():
    """Serves the main frontend dashboard."""
    return render_template('index.html')


@app.route('/api/resolve', methods=['POST'])
def resolve_query():
    """
    API Endpoint: Receives a natural language query,
    extracts location entities, and returns them.
    """
    data = request.json
    user_query = data.get('query', '')

    if not user_query:
        return jsonify({"status": "error", "message": "No query provided"}), 400

    extracted_places = []

    # --- NLP LOGIC ---
    if nlp:
        # Use spaCy for robust Named Entity Recognition (NER)
        doc = nlp(user_query)
        for ent in doc.ents:
            # GPE = Geopolitical Entity (Countries, Cities, States)
            # LOC = Non-GPE locations, mountain ranges, bodies of water
            if ent.label_ in ['GPE', 'LOC']:
                extracted_places.append(ent.text)
    else:
        # Fallback: Simple heuristic extraction if spaCy is missing
        # This is a simulation and should be replaced by your actual model
        ignore_words = [
            'weather', 'compare', 'in', 'and', 'vs', 'show', 'me',
            'temperature', 'between', 'rainfall', 'humidity', 'of',
            'forecast', 'climate', 'prediction', 'analysis', 'the', 'a', 'an'
        ]

        # Clean punctuation
        clean_query = user_query.replace(',', ' ').replace('?', '').replace('.', '')
        words = clean_query.split()

        for word in words:
            # Basic heuristic: assume capitalized words that aren't stop words are places
            # or simply words not in the ignore list for this demo
            if word.lower() not in ignore_words and len(word) > 2:
                # In a real scenario, you might check if the word starts with uppercase
                # if word[0].isupper():
                extracted_places.append(word)

    # Remove duplicates while preserving order
    unique_places = list(dict.fromkeys(extracted_places))

    print(f"Query: {user_query} -> Resolved Places: {unique_places}")

    return jsonify({
        "status": "success",
        "places": unique_places
    })


if __name__ == '__main__':
    # Ensure templates and static directories exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')

    app.run(debug=True, port=5000)