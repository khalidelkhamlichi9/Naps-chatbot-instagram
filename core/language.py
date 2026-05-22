from langdetect import detect, LangDetectException

DARIJA_SIGNALS = [
    # Salutations / formules courantes (CRITIQUE — manquantes)
    "salam", "salamou", "salamoualikoum", "alikoum", "labas", "lhamdoulillah",
    "inchallah", "wllah", "yallah", "yalah", "marhba", "marhaba", "choukran", 
    "barakallah", "tbarkallah", "bslama", "beslama", "khoya", "khouya",
    # Mots interrogatifs / actions / communs
    "wach", "kifash", "kifach", "bghit", "bghiti", "kayn", "kayna", 
    "makaynsh", "nta", "nti", "fin", "dyal", "dyali", "chhal", "chehal",
    "wash", "ana", "hna", "ndir", "taman", "tamane", "thaman", "thman",
    "khsni", "3ndi", "3andi", "3ndek", "3andek", "khdma", "safi", "mzyan", 
    "mezyan", "ewa", "wakha", "bach", "mn", "men", "3ndkom", "3andkom",
    "bzzaf", "bzaf", "chno", "shnu", "chnou", "mnin", "fach", "lla", "la", "ah", "iyyeh",
    "yeh", "ach", "ash", "ghi", "walakin", "walakine", "ghadi", "ghy", "daba", "mera", "lmera", "lwla",
    "ila", "khdit", "khdito", "rani", "ranni", "smitek", "tcharafna", "kidayr", "kidayra",
    "fhamtek", "fhamt", "nch", "n9der", "n9dr", "m3ak", "3lik", "flous", "carte",
    "t9der", "t9dr", "y9der", "y9dr", "3la", "fe", "li", "liya", "lik", "charaf", "3tini", "t3tini",
]

def detect_language(text: str) -> str:
    """
    Detect language: fr | ar | en | darija
    Darija is detected heuristically before langdetect.
    """
    text_lower = text.lower()
    import re
    clean_text = re.sub(r'[^\w\s]', '', text_lower)
    words = clean_text.split()
    darija_hits = 0
    for signal in DARIJA_SIGNALS:
        if len(signal) <= 2:
            if any(signal == word for word in words):
                darija_hits += 1
        else:
            if any(signal in word for word in words):
                darija_hits += 1
            
    if darija_hits >= 1:
        return "darija"
    # Check for Arabic characters
    if re.search(r'[\u0600-\u06FF]', text):
        # If it has Arabic script, it's either Arabic or Darija (with script)
        # We default to Arabic for script unless Darija words are found (already checked above)
        return "ar"

    try:
        lang = detect(text)
        if lang in ("fr", "ar", "en"):
            return lang
        # Map similar languages to French
        if lang in ("ca", "es", "it", "pt", "ro"):
            return "fr"
        # Map other Arabic-script languages (detected by mistake) to Arabic
        if lang in ("fa", "ur", "ps"):
            return "ar"
        # If very short and common, default to Darija/Arabic instead of French
        if len(words) <= 2 and "salam" in text_lower:
            return "darija"
            
        return "fr"
    except LangDetectException:
        if "salam" in text_lower: return "darija"
        return "fr"
    except Exception:
        return "fr"


def determine_language(message: str, history: list[dict]) -> str:
    """
    Determine conversation language with memory.
    If the current message is short or has no text content (neutral, e.g. names, numbers, "oui", "non"),
    it inherits the language of the ongoing conversation.
    """
    current_lang = detect_language(message)
    
    # If the user explicitly used Darija/Arabic/English f the current message, switch immediately
    if current_lang in ("darija", "ar", "en"):
        return current_lang
        
    # If current_lang is "fr", it could be a fallback.
    # Check if the current message is neutral (short or contains no letters)
    words = message.strip().split()
    letter_words = [w for w in words if any(c.isalpha() for c in w)]
    has_letters = len(letter_words) > 0
    is_neutral = not has_letters or len(letter_words) <= 3
    
    if is_neutral and history:
        # It's neutral, so we inherit the conversation language from history
        for msg in reversed(history):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                past_lang = detect_language(content)
                if past_lang in ("darija", "ar", "en"):
                    return past_lang
                
                # If we find a non-neutral French message f l'user, we know they spoke French
                past_words = content.strip().split()
                past_letter_words = [w for w in past_words if any(c.isalpha() for c in w)]
                if len(past_letter_words) > 3:
                    return "fr"
                    
    return "fr"


# LEGACY / UNUSED (Replaced by Global System Prompt in Dashboard)
# SYSTEM_PROMPTS and get_system_prompt are deprecated.
