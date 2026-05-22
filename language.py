from langdetect import detect, LangDetectException

DARIJA_SIGNALS = [
    # Salutations / formules courantes (CRITIQUE — manquantes)
    "salam", "salamou", "salamoualikoum", "alikoum", "labas", "lhamdoulillah",
    "inchallah", "wllah", "yallah", "yalah", "marhba", "marhaba", "choukran", 
    "barakallah", "tbarkallah", "bslama", "beslama", "khoya", "khouya",
    # Mots interrogatifs / actions
    "wach", "kifash", "kifach", "bghit", "bghiti", "kayn", "kayna", 
    "makaynsh", "nta", "nti", "fin", "dyal", "dyali", "chhal", "chehal",
    "wash", "ana", "hna", "ndir", "taman", "tamane", "thaman", "thman",
    "khsni", "3ndi", "3andi", "3ndek", "3andek", "khdma", "safi", "mzyan", 
    "mezyan", "ewa", "wakha", "bach", "mn", "men", "3ndkom", "3andkom",
    "bzzaf", "bzaf", "chno", "shnu", "chnou", "mnin", "fach", "lla", 
    "yeh", "ach", "ash", "ghi", "walakin", "walakine", "ghadi", "ghy", 
    "ila", "khdit", "khdito", "rani", "ranni", "smitek", "tcharafna",
    "fhamtek", "fhamt", "nch", "n9der", "n9dr",
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
    # Improved detection: check if signal is a substring of any word (better for Darija prefixes)
    darija_hits = 0
    for signal in DARIJA_SIGNALS:
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

# LEGACY / UNUSED (Replaced by Global System Prompt in Dashboard)
# SYSTEM_PROMPTS and get_system_prompt are deprecated.
