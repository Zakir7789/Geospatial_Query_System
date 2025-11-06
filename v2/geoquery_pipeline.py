# geoquery_pipeline.py
# -------------------------------------------------------------------
# Purpose: Main pipeline integrating text preprocessing, entity extraction,
# fuzzy matching, and adaptive fallback n-gram logic.
# -------------------------------------------------------------------

import spacy
import json
import re
from nltk.corpus import stopwords
from text_preprocessor import TextPreprocessor
from entity_extractor import extract_entities
from fuzzy_matcher import fuzzy_match_entity

# Load spaCy model once
nlp = spacy.load("en_core_web_lg")


# -------------------------------------------------------------------
# Helper: Filter out meaningless n-grams
# -------------------------------------------------------------------
def filter_meaningful_ngrams(ngrams):
    stop_words = set(stopwords.words("english"))
    filtered = []
    for ngram in ngrams:
        words = ngram.split()
        if len(words) == 0:
            continue
        # Skip phrases that are all stopwords
        if all(w in stop_words for w in words):
            continue
        # Skip phrases with no alphabetic character
        if not any(re.search(r"[a-zA-Z]", w) for w in words):
            continue
        # Skip phrases that are too long or meaningless
        if len(words) > 4:
            continue
        filtered.append(ngram)
    return filtered


# -------------------------------------------------------------------
# Helper: Generate context-aware n-grams from unrecognized text only
# -------------------------------------------------------------------
def generate_unrecognized_ngrams(doc, n_range=(1, 3)):
    recognized_spans = [(ent.start, ent.end) for ent in doc.ents]
    recognized_tokens = set()
    for start, end in recognized_spans:
        recognized_tokens.update(range(start, end))

    tokens = [t.text for t in doc]
    unrecognized_segments = []
    current_segment = []

    for i, token in enumerate(tokens):
        if i not in recognized_tokens:
            current_segment.append(token)
        else:
            if current_segment:
                unrecognized_segments.append(current_segment)
                current_segment = []
    if current_segment:
        unrecognized_segments.append(current_segment)

    ngrams = []
    for seg in unrecognized_segments:
        for n in range(n_range[0], n_range[1] + 1):
            for i in range(len(seg) - n + 1):
                ngrams.append(" ".join(seg[i:i + n]))
    return ngrams


# -------------------------------------------------------------------
# Main Pipeline
# -------------------------------------------------------------------
def process_query(query):
    # Step 1: Preprocess text
    processed = TextPreprocessor().preprocess(query)
    doc = nlp(processed)

    # Step 2: Extract named entities using spaCy (GPE, LOC, etc.)
    spacy_entities = extract_entities(doc)

    print(f"\n[INFO] SpaCy detected entities: {[e["text"] for e in spacy_entities]}")

    # Step 3: Adaptive Fallback Logic
    if len(spacy_entities) == 0 or len(spacy_entities) < 2:
        print(f"[INFO] SpaCy detected {len(spacy_entities)} entities — enabling fallback n-grams.")
        ngrams = generate_unrecognized_ngrams(doc, n_range=(1, 3))
        ngrams = filter_meaningful_ngrams(ngrams)
    else:
        print(f"[INFO] SpaCy detected {len(spacy_entities)} entities — skipping fallback n-grams.")
        ngrams = []

    # Combine detected entities and fallback n-grams
    all_phrases = [e["text"] for e in spacy_entities] + ngrams

    results = []
    for phrase in all_phrases:
        candidates = fuzzy_match_entity(phrase, top_k=3, threshold=0.35)
        for cand in candidates:
            cand["token"] = phrase
            results.append(cand)

    # Sort matches by rank and similarity
    results = sorted(
        results,
        key=lambda x: (-x.get("score", 0), -x.get("final_rank", 0))
    )

    return {
        "query": query,
        "matches": results[:5]  # return top 5 results
    }


# -------------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------------
if __name__ == "__main__":
    query = input("Enter query: ").strip()
    output = process_query(query)
    print(json.dumps(output, indent=2))
