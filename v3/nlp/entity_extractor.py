# nlp/entity_extractor_v1.py
import spacy

nlp = spacy.load("en_core_web_trf")

def extract_location_tokens(sentence: str):
    """Extract potential place-name tokens using SpaCy NER and fallback heuristics."""
    doc = nlp(sentence)
    tokens = set()

    # Named Entity Recognition (NER)
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:  # Geopolitical entity or location
            tokens.add(ent.text)

    # Fallback: capitalized tokens not in common stopwords
    if not tokens:
        for token in doc:
            if token.is_title and not token.is_stop and token.is_alpha:
                tokens.add(token.text)

    return list(tokens)

print(extract_location_tokens("Which of the following has the highest population — Maharashtra, Ahmedabad or India"))
