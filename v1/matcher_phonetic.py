from rapidfuzz import process, fuzz
import pandas as pd
import phonetics


def get_phonetic_code(name: str):
    """Return the Metaphone code for a name."""
    return phonetics.metaphone(name)


def match_token_to_table(token, canonical_tables, threshold=80):
    best_match = None
    best_score = 0
    best_table = None

    for table, names in canonical_tables.items():  # names is already a list of strings
        if not names:
            continue

        # RapidFuzz best match
        match, score, _ = process.extractOne(
            token, names, scorer=fuzz.ratio
        )

        if score > best_score and score >= threshold:
            best_match = match
            best_score = score
            best_table = table

    return {
        "token": token,
        "canonical": best_match,
        "table": best_table,
        "score": round(best_score / 100, 3)  # normalize to 0–1
    }



def phonetic_match_tokens(tokens, canonical_tables, threshold=80):
    results = []
    for token in tokens:
        result = match_token_to_table(token, canonical_tables, threshold)
        results.append(result)
    return results



# ---------------- Example Usage -----------------
if __name__ == "__main__":
    df_country = pd.DataFrame({"id": [1, 2], "name": ["India", "New Zealand"]})
    df_state = pd.DataFrame({"id": [1, 2], "name": ["Maharashtra", "Gujarat"]})
    df_city = pd.DataFrame({"id": [1, 2], "name": ["Ahmedabad", "Chennai"]})

    canonical_tables = {"Country": df_country, "State": df_state, "City": df_city}

    tokens = ["Maharastra", "Ahmedabad", "Chennnai", "New-Zealand"]
    tokens = [t.replace("-", " ") for t in tokens]

    results = phonetic_match_tokens(tokens, canonical_tables)
    for r in results:
        print(r)
