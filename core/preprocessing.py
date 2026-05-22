import re

# Minimal stop words for FR and AR (can be expanded)
STOP_WORDS = {
    "fr": {
        "le", "la", "les", "un", "une", "des", "ce", "cette", "ces", "et", "ou", "mais", "pour", 
        "avec", "dans", "sur", "sous", "par", "qui", "que", "quoi", "dont", "où", "est", "sont", 
        "être", "avoir", "faire", "plus", "moins", "très", "tout", "tous", "c", "d", "l", "m", "n", "s", "t"
    },
    "ar": {
        "من", "إلى", "على", "عن", "في", "مع", "هذا", "هذه", "ذلك", "تلك", "هو", "هي", "هم", "هن",
        "و", "أو", "ثم", "إن", "أن", "الذي", "التي", "هؤلاء", "كل", "بعض", "ما", "لم", "لا"
    }
}

def clean_text(text: str, language: str = "fr") -> str:
    """
    Basic preprocessing:
    1. Lowercase
    2. Remove special characters
    3. Remove stop words (optional, usually kept for RAG/Context)
    4. Normalize whitespace
    """
    # 1. Lowercase (for Latin scripts)
    text = text.lower()
    
    # 2. Remove special characters (except punctuation that might matter for sentences)
    # Keeping . , ? ! for sentence splitting if needed later
    text = re.sub(r"[^\w\s\.\,\?\!]", " ", text)
    
    # 3. Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def tokenize_and_clean(text: str, language: str = "fr") -> str:
    """
    Advanced cleaning: Tokenization + Stop words removal.
    Note: For RAG, we usually keep stop words in the actual content for LLM quality,
    but we can clean the text used for search if needed.
    Here, we'll just normalize the text to ensure consistency.
    """
    words = text.split()
    lang_stops = STOP_WORDS.get(language, STOP_WORDS["fr"])
    
    filtered = [w for w in words if w.lower() not in lang_stops]
    
    return " ".join(filtered)
