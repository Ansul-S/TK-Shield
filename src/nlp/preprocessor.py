# src/nlp/preprocessor.py

import spacy
import nltk
from nltk.corpus import stopwords
import re

# Load spaCy's English model
nlp = spacy.load("en_core_web_sm")

# Load English stopwords from NLTK
STOPWORDS = set(stopwords.words("english"))

# Extra stopwords specific to legal/patent language
LEGAL_STOPWORDS = {
    "wherein", "hereby", "thereof", "herein", "whereas",
    "comprising", "consisting", "said", "claim", "claims"
}

# Combine both sets
ALL_STOPWORDS = STOPWORDS.union(LEGAL_STOPWORDS)


def clean_text(text: str) -> str:
    """
    Step 1: Basic cleaning
    - Convert to lowercase
    - Remove special characters and extra spaces
    """
    # Lowercase everything
    text = text.lower()

    # Remove special characters (keep letters, numbers, spaces)
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str) -> list:
    """
    Step 2: Split text into individual word tokens
    """
    doc = nlp(text)
    tokens = [token.text for token in doc]
    return tokens


def remove_stopwords(tokens: list) -> list:
    """
    Step 3: Remove meaningless words
    'neem leaves used malaria' is better than
    'neem leaves are used in for the malaria fever'
    """
    filtered = [word for word in tokens if word not in ALL_STOPWORDS]
    return filtered


def lemmatize(tokens: list) -> list:
    """
    Step 4: Reduce words to their base form
    'leaves' → 'leaf'
    'boiling' → 'boil'
    'infections' → 'infection'

    Why? So 'healing' and 'heals' match the same concept
    """
    doc = nlp(" ".join(tokens))
    lemmas = [token.lemma_ for token in doc]
    return lemmas


def preprocess(text: str) -> str:
    """
    Full pipeline: runs all steps in order
    Returns a clean, normalized string ready for embedding
    """
    # Step 1: Clean
    cleaned = clean_text(text)

    # Step 2: Tokenize
    tokens = tokenize(cleaned)

    # Step 3: Remove stopwords
    tokens = remove_stopwords(tokens)

    # Step 4: Lemmatize
    tokens = lemmatize(tokens)

    # Join back into a single string
    result = " ".join(tokens)

    return result


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":

    test_sentences = [
        "Neem leaves boiled in water are used for malaria fever!!",
        "Turmeric paste was applied to wounds by Ayurvedic practitioners in Kerala",
        "The invention comprising use of Azadirachta indica wherein said plant extract"
    ]

    print("=" * 60)
    print("TK-SHIELD — NLP PREPROCESSOR TEST")
    print("=" * 60)

    for sentence in test_sentences:
        result = preprocess(sentence)
        print(f"\nINPUT : {sentence}")
        print(f"OUTPUT: {result}")
        print("-" * 60)