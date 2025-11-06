# entity_extractor.py

import spacy
from text_preprocessor import TextPreprocessor as tp

# Load spaCy English model
nlp = spacy.load("en_core_web_lg")

def extract_entities(doc):
    """
    Extract geographic entity candidates from text using spaCy NER.
    """

    entities = []
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "FAC"):  # GPE = Geo-political entity, LOC = location, FAC = facilities
            entities.append({
                "text": ent.text,
                "label": ent.label_,
            })

    # Fallback: capture capitalized or common geographic words if spaCy misses
    tokens = [token.text for token in doc if token.is_alpha]
    if not entities:
        for token in tokens:
            if token.lower() not in ["in", "at", "on", "of", "the", "and"]:
                entities.append({"text": token, "label": "UNKNOWN"})

    return entities


if __name__ == "__main__":
    examples = [
        "Flooding in São Paulo, Côte d’Ivoire and New York City.",
        "Earthquake reported near Delhi and Kathmandu.",
        "Severe cyclone expected in Bay of Bengal.",
        "Fire at Los Angeles International Airport."
    ]

    for text in examples:
        print(f"\nInput: {text}")
        processed = tp().preprocess(text)
        doc = nlp(processed)
        entities = extract_entities(doc)
        for e in entities:
            print(f" → {e['text']} ({e['label']})")
