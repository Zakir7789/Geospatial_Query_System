import spacy

# Load spaCy English model (make sure to run: python -m spacy download en_core_web_sm)
nlp = spacy.load("en_core_web_trf")


def extract_place_entities(text: str):
    """
    Extract potential place names (GPE entities) from text using spaCy NER.
    Returns a list of tokens (strings).
    """

    text = text.replace("-", " ")
    doc = nlp(text)
    places = []

    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:  # GPE = countries, cities, states | LOC = locations
            places.append(ent.text)

    return list(set(places))  # remove duplicates


if __name__ == "__main__":
    # Test sentences
    queries = [
        "Which of the following saw the highest average temperature in January, Maharashtra, Ahmedabad or entire New-Zealand?",
        "Show me a graph of rainfall for Chennai for the month of October",
        "What is the population of Mumbai and Gujarat compared to New Zealand?",
    ]

    for q in queries:
        print(f"\n🔎 Query: {q}")
        print("📍 Extracted Places:", extract_place_entities(q))
