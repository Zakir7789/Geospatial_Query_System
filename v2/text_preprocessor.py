# text_preprocessor.py
import re
import unicodedata
from typing import List


class TextPreprocessor:
    """
    Cleans and normalizes text before entity extraction,
    prioritizing preservation of NER features like case and essential separators.
    """

    def __init__(self):
        # FIX: Keep the comma (,) in the allowed characters (along with hyphen, apostrophe, period)
        # to ensure spaCy correctly tokenizes separate entities.
        self.non_essential_punc_pattern = re.compile(r'[^\w\s\-\'.,&]', re.UNICODE)
        self.multispace_pattern = re.compile(r'\s+')
        self.diacritics_pattern = re.compile(r'[\u0300-\u036f]', re.UNICODE)

    def _normalize_and_strip_accents(self, text: str) -> str:
        """Combines unicode normalization (NFD) and diacritic stripping."""
        text_nfd = unicodedata.normalize("NFD", text)
        text_no_accents = self.diacritics_pattern.sub('', text_nfd)
        return unicodedata.normalize("NFKC", text_no_accents)

    def _clean_punctuation_and_whitespace(self, text: str) -> str:
        """Remove unnecessary punctuation and normalize spaces."""
        # Replace non-essential symbols with a space
        text = self.non_essential_punc_pattern.sub(' ', text)
        # Normalize whitespace
        text = self.multispace_pattern.sub(' ', text).strip()
        return text

    def preprocess(self, text: str, lower: bool = False) -> str:
        """Perform preprocessing steps in an NER-friendly order."""
        text = text.strip()
        text = self._normalize_and_strip_accents(text)
        text = self._clean_punctuation_and_whitespace(text)

        if lower:
            text = text.lower()

        return text

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words using the non-lowercased processed text."""
        processed_text = self.preprocess(text, lower=False)
        return processed_text.split()