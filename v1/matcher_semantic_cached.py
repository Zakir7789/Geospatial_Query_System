from sentence_transformers import SentenceTransformer, util
import torch

# Load model once
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

class SemanticMatcher:
    def __init__(self, canonical_tables):
        """
        canonical_tables: dict, {table_name: [list of canonical names]}
        """
        self.canonical_tables = canonical_tables
        self.embeddings_cache = {}  # {table_name: tensor embeddings}
        self._cache_embeddings()

    def _cache_embeddings(self):
        """Compute and store embeddings for all canonical names"""
        for table, names in self.canonical_tables.items():
            self.embeddings_cache[table] = model.encode(names, convert_to_tensor=True)
        print("💾 Cached embeddings for semantic matcher.")

    def semantic_match_tokens(self, tokens, threshold=0.7):
        """
        tokens: list of strings (query tokens)
        Returns list of dicts with token, canonical, table, score
        """
        results = []
        for token in tokens:
            token_emb = model.encode(token, convert_to_tensor=True)
            best_score = 0
            best_match = None
            best_table = None

            for table, embeddings in self.embeddings_cache.items():
                scores = util.cos_sim(token_emb, embeddings)[0]  # cosine similarity
                max_score = torch.max(scores).item()
                if max_score > best_score:
                    best_score = max_score
                    best_table = table
                    idx = torch.argmax(scores).item()
                    best_match = self.canonical_tables[table][idx]

            results.append({
                "token": token,
                "canonical": best_match if best_score >= threshold else None,
                "table": best_table if best_score >= threshold else None,
                "score": best_score
            })

        return results
