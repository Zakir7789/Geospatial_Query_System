from sentence_transformers import SentenceTransformer, util
import pandas as pd
import torch

# Load pre-trained embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')  # lightweight, fast, accurate


def encode_canonical_names(canonical_tables: dict):
    """
    Encode all canonical names from Country, State, City tables.
    Returns a dict: {table_name: {"names": [...], "embeddings": tensor}}
    """
    encoded = {}
    for table_name, df in canonical_tables.items():
        names = df['name'].tolist()
        embeddings = model.encode(names, convert_to_tensor=True)
        encoded[table_name] = {"names": names, "embeddings": embeddings}
    return encoded


def match_token_to_table_semantic(token, canonical_tables, threshold=0.7):
    """
    Match token against canonical tables using semantic similarity.
    """
    best_match = None
    best_score = 0.0
    best_table = None

    token_emb = model.encode(token, convert_to_tensor=True)

    for table, names in canonical_tables.items():  # names is already a list
        if not names:
            continue

        name_embs = model.encode(names, convert_to_tensor=True)

        # cosine similarity
        scores = util.cos_sim(token_emb, name_embs)[0]

        max_idx = scores.argmax().item()
        score = scores[max_idx].item()

        if score > best_score and score >= threshold:
            best_match = names[max_idx]
            best_score = score
            best_table = table

    return {
        "token": token,
        "canonical": best_match,
        "table": best_table,
        "score": round(best_score, 3)
    }

def semantic_match_tokens(tokens, canonical_tables, threshold=0.7):
    results = []
    for token in tokens:
        result = match_token_to_table_semantic(token, canonical_tables, threshold)
        results.append(result)
    return results


# ---------------- Example Usage -----------------
if __name__ == "__main__":
    df_country = pd.DataFrame({"id": [1, 2, 3], "name": ["India", "United States", "New Zealand"]})
    df_state = pd.DataFrame({"id": [1, 2], "name": ["Maharashtra", "Gujarat"]})
    df_city = pd.DataFrame({"id": [1, 2], "name": ["Mumbai", "Chennai"]})

    canonical_tables = {"Country": df_country, "State": df_state, "City": df_city}

    # Encode canonical tables
    encoded_tables = encode_canonical_names(canonical_tables)

    # Test tokens including nicknames/abbreviations
    tokens = ["Bombay", "Maharastra", "Chennnai", "U.S.A", "NZ", "Ahmdabad"]

    results = semantic_match_tokens(tokens, encoded_tables)
    for r in results:
        print(r)
